#!/usr/bin/env python3
"""C30D 单次低速前进测试（独立脚本，不引用归档驱动）。

默认：只做检查与打印，不打开串口、不发送。
实际发送必须同时满足：
  --execute-forward --confirm-wheels-off --confirm-power-cut-ready
  且环境变量 C30D_ALLOW_EXECUTE=1

定时结束 = 停止发送，不等于电机已停。
不得把零速或反向当作急停；本脚本退出时不发送零帧、不反向。
持续运动时由现场切断电机驱动电源。
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from c30d_frame import BAUD, CANDIDATE_NOTE, DEVICE, build_velocity_frame  # noqa: E402

VX = 60  # 与历史短测整数同量级；单位未证实
VY = 0
WZ = 0
SEND_DURATION_S = 0.20
SEND_PERIOD_S = 0.05
MAX_FRAMES = 4
MAX_DURATION_S = 5.0
LOG_DIR = Path("/opt/personal_robot/hardware_test/c30d/logs")


def expected_forward_hex() -> str:
    return build_velocity_frame(VX, VY, WZ).hex()


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
    hex_got = expected_forward_hex()
    if hex_got != "7b0000003c00000000477d":
        errors.append(f"frame hex mismatch: {hex_got}")
    return errors


def log_line(msg: str) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    path = LOG_DIR / "forward_once.log"
    ts = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    with path.open("a", encoding="utf-8") as f:
        f.write(f"{ts} {msg}\n")


def run_check() -> int:
    frame = build_velocity_frame(VX, VY, WZ)
    print("mode=check (no serial open)")
    print(CANDIDATE_NOTE)
    print(f"device={DEVICE} baud_hypothesis={BAUD}")
    print(f"planned vx,vy,wz={VX},{VY},{WZ}")
    print(f"planned_frame_hex={frame.hex()}")
    print(f"send_duration_s={SEND_DURATION_S} period_s={SEND_PERIOD_S} max_frames={MAX_FRAMES}")
    print("on_timer_end=stop_sending_only; motors_may_keep_moving; cut_motor_power_if_needed")
    print("no_zero_frame_on_exit; no_reverse")
    errs = safety_check()
    for e in errs:
        print(f"CHECK_FAIL {e}")
    if errs:
        return 1
    print("CHECK_OK")
    return 0


def run_execute(duration_s: float, vx: int) -> int:
    if os.environ.get("C30D_ALLOW_EXECUTE") != "1":
        print("REFUSE: set C30D_ALLOW_EXECUTE=1 for execute (not enabled this session unless you set it).")
        return 2
    errs = safety_check()
    if errs:
        for e in errs:
            print(f"CHECK_FAIL {e}")
        return 1
    frame = build_velocity_frame(vx, VY, WZ)
    log_line(f"EXECUTE start hex={frame.hex()} duration={duration_s} vx={vx}")
    fd = None
    sent = 0
    try:
        import termios

        fd = os.open(DEVICE, os.O_RDWR | os.O_NOCTTY)
        attrs = termios.tcgetattr(fd)
        speed = termios.B115200
        attrs[4] = speed
        attrs[5] = speed
        termios.tcsetattr(fd, termios.TCSANOW, attrs)
        deadline = time.monotonic() + duration_s
        max_frames = max(MAX_FRAMES, int(duration_s / SEND_PERIOD_S) + 1)
        while sent < max_frames and time.monotonic() < deadline:
            n = os.write(fd, frame)
            if n != len(frame):
                raise OSError(f"short write {n}")
            sent += 1
            time.sleep(SEND_PERIOD_S)
        log_line(f"EXECUTE stop_sending frames={sent} (not claiming motors stopped)")
        print(f"sent_frames={sent} hex={frame.hex()} duration_s={duration_s}")
        print("STOPPED_SENDING; if wheels still move, CUT MOTOR DRIVE POWER NOW")
        return 0
    except Exception as e:
        log_line(f"EXECUTE error {e!r}")
        print(f"ERROR {e!r}; closed without zero/reverse")
        return 1
    finally:
        if fd is not None:
            try:
                os.close(fd)
            except OSError:
                pass


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="C30D single forward test. Default: check only.")
    p.add_argument("--print-frame", action="store_true")
    p.add_argument("--execute-forward", action="store_true",
                   help="Send candidate forward frames. Requires confirms + env.")
    p.add_argument("--confirm-wheels-off", action="store_true")
    p.add_argument("--confirm-power-cut-ready", action="store_true")
    p.add_argument("--duration-s", type=float, default=SEND_DURATION_S)
    p.add_argument("--vx", type=int, default=VX)
    args = p.parse_args(argv)

    if args.print_frame and not args.execute_forward:
        print(expected_forward_hex())
        return 0

    if args.execute_forward:
        if not (args.confirm_wheels_off and args.confirm_power_cut_ready):
            print("REFUSE execute: need --confirm-wheels-off and --confirm-power-cut-ready")
            return 2
        print("WARNING: timer end != motors stopped. No software e-stop. Cut drive power if needed.")
        duration = args.duration_s
        if duration <= 0 or duration > MAX_DURATION_S:
            print(f"REFUSE: --duration-s must be in (0, {MAX_DURATION_S}]")
            return 2
        return run_execute(duration, args.vx)

    return run_check()


if __name__ == "__main__":
    sys.exit(main())
