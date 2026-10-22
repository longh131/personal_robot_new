#!/usr/bin/env python3
"""C30D 键盘遥控（独立，候选协议未完全验证）。

默认只做静态检查，不开串口。
运动：C30D_ALLOW_EXECUTE=1 且
  --execute-teleop --confirm-wheels-off --confirm-power-cut-ready

W/S 进退  A/D 横移  Q/E 旋转  空格请求停  ESC 退出。
按键后持续按 20Hz 发送，直到松手间隙或满 MAX_HOLD_S。
停止发送 ≠ 电机已停。零速仅为停车请求。不操作板载 RESET。
"""

from __future__ import annotations

import argparse
import os
import select
import sys
import time
import termios
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from c30d_frame import (  # noqa: E402
    BAUD,
    CANDIDATE_NOTE,
    DEVICE,
    build_velocity_frame,
)

TELEOP_SPEED = 150  # mm/s 量级；与已转过的 --vx 150 相同
SEND_PERIOD_S = 0.05
KEY_RELEASE_GAP_S = 0.80
MAX_HOLD_S = 8.0
ZERO_REQUEST_FRAMES = 4
LOG_DIR = Path("/opt/personal_robot/hardware_test/c30d/logs")

KEYS = "W/S 进退  A/D 横移  Q/E 旋转（不是 R）  空格请求停  ESC 退出；按住持续发，松手约 0.8s 后停发"


def proc_occupants(paths: tuple[str, ...]) -> list[str]:
    hits: list[str] = []
    proc = Path("/proc")
    for pdir in proc.iterdir():
        if not pdir.name.isdigit():
            continue
        fd_dir = pdir / "fd"
        try:
            for fd in fd_dir.iterdir():
                try:
                    target = os.readlink(fd)
                except OSError:
                    continue
                if target in paths:
                    hits.append(f"pid={pdir.name} {target}")
        except OSError:
            continue
    return hits


def safety_check() -> list[str]:
    errors: list[str] = []
    if not os.path.exists(DEVICE):
        errors.append(f"missing {DEVICE}")
    occ = proc_occupants((DEVICE, "/dev/ttyACM0"))
    if occ:
        errors.append("occupied: " + "; ".join(occ))
    fwd = build_velocity_frame(TELEOP_SPEED, 0, 0)
    if len(fwd) != 11:
        errors.append(f"bad forward frame {fwd.hex()}")
    return errors


def log_line(msg: str) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    with (LOG_DIR / "keyboard_teleop.log").open("a", encoding="utf-8") as f:
        f.write(f"{ts} {msg}\n")


def run_check() -> int:
    print("mode=check (no serial open)")
    print(CANDIDATE_NOTE)
    print(f"device={DEVICE} baud_hypothesis={BAUD} teleop_speed={TELEOP_SPEED}")
    print(f"keys={KEYS}")
    print(f"period={SEND_PERIOD_S}s hold_gap={KEY_RELEASE_GAP_S}s max_hold={MAX_HOLD_S}s")
    print("stop_sending != motors_stopped; space=zero_request_only; no software e-stop")
    print("board RESET is manual recovery only; this program never toggles reset")
    errs = safety_check()
    for e in errs:
        print(f"CHECK_FAIL {e}")
    if errs:
        return 1
    print("CHECK_OK")
    return 0


def _set_baud_115200(fd: int) -> None:
    attrs = termios.tcgetattr(fd)
    speed = termios.B115200
    attrs[4] = speed
    attrs[5] = speed
    termios.tcsetattr(fd, termios.TCSANOW, attrs)


def _write_frame(fd: int, frame: bytes) -> None:
    n = os.write(fd, frame)
    if n != len(frame):
        raise OSError(f"short write {n}")


def key_to_twist(key: str) -> tuple[int, int, int] | None:
    s = TELEOP_SPEED
    mapping = {
        "w": (s, 0, 0),
        "s": (-s, 0, 0),
        "a": (0, s, 0),
        "d": (0, -s, 0),
        "q": (0, 0, s),
        "e": (0, 0, -s),
    }
    return mapping.get(key.lower())


def run_execute() -> int:
    if os.environ.get("C30D_ALLOW_EXECUTE") != "1":
        print("REFUSE: set C30D_ALLOW_EXECUTE=1")
        return 2
    if not sys.stdin.isatty():
        print("REFUSE: stdin is not a TTY")
        return 2
    errs = safety_check()
    if errs:
        for e in errs:
            print(f"CHECK_FAIL {e}")
        return 1

    print("RISK: candidate protocol unverified; no hardware e-stop; zero frame != stop.")
    print("If wheels keep moving, CUT MOTOR DRIVE POWER. Do not use board RESET as e-stop.")
    print(KEYS)
    log_line("EXECUTE teleop start")

    ser_fd: int | None = None
    old_stdin = None
    hold_frame = b""
    hold_start = 0.0
    last_key_time = 0.0
    holding = False
    sent = 0
    space_latched = False

    try:
        ser_fd = os.open(DEVICE, os.O_RDWR | os.O_NOCTTY)
        _set_baud_115200(ser_fd)
        old_stdin = termios.tcgetattr(sys.stdin.fileno())
        new = termios.tcgetattr(sys.stdin.fileno())
        new[3] = new[3] & ~(termios.ECHO | termios.ICANON)
        new[6][termios.VMIN] = 0
        new[6][termios.VTIME] = 0
        termios.tcsetattr(sys.stdin.fileno(), termios.TCSANOW, new)

        while True:
            now = time.monotonic()
            r, _, _ = select.select([sys.stdin], [], [], SEND_PERIOD_S)
            ch = ""
            if r:
                data = os.read(sys.stdin.fileno(), 8)
                if data:
                    if data[0] == 0x1B:
                        print("\nESC: stop sending, exit (motors may still move)")
                        log_line("ESC exit")
                        break
                    ch = chr(data[0])

            if ch == " ":
                holding = False
                hold_frame = b""
                if not space_latched:
                    space_latched = True
                    z = build_velocity_frame(0, 0, 0)
                    nzero = 0
                    try:
                        for _ in range(ZERO_REQUEST_FRAMES):
                            _write_frame(ser_fd, z)
                            nzero += 1
                            time.sleep(SEND_PERIOD_S)
                    except OSError as e:
                        print(f"\nserial error during stop request: {e!r}")
                        log_line(f"serial error {e!r}")
                        print("CUT MOTOR DRIVE POWER if moving")
                        break
                    print(
                        f"\nstop REQUEST sent {nzero} zero frames; "
                        "NOT claiming motors stopped. Cut power if still moving.",
                        flush=True,
                    )
                    log_line(f"space zero_request frames={nzero}")
                continue

            twist = key_to_twist(ch) if ch else None
            if twist is not None:
                space_latched = False
                vx, vy, wz = twist
                hold_frame = build_velocity_frame(vx, vy, wz)
                last_key_time = now
                if not holding:
                    holding = True
                    hold_start = now
                    sent = 0
                    log_line(f"hold start key={ch!r} hex={hold_frame.hex()}")
                    print(f"\nhold {ch!r} vx,vy,wz={vx},{vy},{wz}", flush=True)

            if holding and (now - last_key_time) >= KEY_RELEASE_GAP_S:
                log_line(f"key gap -> stop sending frames={sent}")
                print(f"\nstop sending after release (frames={sent})", flush=True)
                holding = False
                hold_frame = b""

            if holding and (now - hold_start) >= MAX_HOLD_S:
                log_line(f"max hold -> stop sending frames={sent}")
                print(f"\nmax {MAX_HOLD_S}s, stop sending", flush=True)
                holding = False
                hold_frame = b""

            if holding:
                try:
                    _write_frame(ser_fd, hold_frame)
                except OSError as e:
                    print(f"\nserial disconnect/write error: {e!r}")
                    log_line(f"serial error {e!r}")
                    print("CUT MOTOR DRIVE POWER if moving")
                    break
                sent += 1

        return 0
    except Exception as e:
        log_line(f"EXECUTE error {e!r}")
        print(f"ERROR {e!r}; closed; no reverse. Cut power if moving.")
        return 1
    finally:
        if old_stdin is not None:
            try:
                termios.tcsetattr(sys.stdin.fileno(), termios.TCSANOW, old_stdin)
            except termios.error:
                pass
        if ser_fd is not None:
            try:
                os.close(ser_fd)
            except OSError:
                pass
        log_line("EXECUTE teleop serial closed")
        print("serial closed; if wheels move, CUT MOTOR DRIVE POWER")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="C30D keyboard teleop. Default: check only.")
    p.add_argument("--print-frame", action="store_true")
    p.add_argument("--execute-teleop", action="store_true")
    p.add_argument("--confirm-wheels-off", action="store_true")
    p.add_argument("--confirm-power-cut-ready", action="store_true")
    args = p.parse_args(argv)

    if args.print_frame and not args.execute_teleop:
        print(build_velocity_frame(TELEOP_SPEED, 0, 0).hex())
        return 0

    if args.execute_teleop:
        if not (args.confirm_wheels_off and args.confirm_power_cut_ready):
            print("REFUSE execute: need --confirm-wheels-off and --confirm-power-cut-ready")
            return 2
        return run_execute()

    return run_check()


if __name__ == "__main__":
    sys.exit(main())
