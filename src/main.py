#!/usr/bin/env python3
"""Personal AI entry: start in IDLE. Optional REMOTE http and AWAKE socket."""

from __future__ import annotations

import argparse
import logging
import queue
import signal
import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from awake.session import AwakeSession
from settings import load_idle_timeout_s
from indicators.cues import Cues
from remote.auth import load_auth
from remote.camera import CameraHub
from remote.http_server import RemoteGate, start as start_remote
from runtime.events import Event
from runtime.idle import run
from runtime.machine import Machine
from sentry.watch import Sentry

log = logging.getLogger("main")


def main() -> int:
    p = argparse.ArgumentParser(description="Personal AI")
    p.add_argument("--once", action="store_true", help="enter IDLE then exit")
    p.add_argument("--no-led", action="store_true", help="do not drive GPIO16")
    p.add_argument("--no-buzzer", action="store_true", help="do not drive GPIO12")
    p.add_argument("--no-remote", action="store_true", help="do not start REMOTE http")
    p.add_argument("--no-awake", action="store_true", help="do not start AWAKE local socket")
    p.add_argument("--no-mic", action="store_true", help="do not start microphone wake")
    args = p.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )

    machine = Machine()
    events: queue.Queue[Event] = queue.Queue()
    cues = Cues(led=not args.no_led, buzzer=not args.no_buzzer)
    from awake.battery_watch import BatteryWatch

    battery = BatteryWatch(machine, cues)
    stopping = False
    httpd = None
    gate = None
    awake = None
    mic = None
    sentry = None

    if not args.once and not args.no_remote:
        try:
            auth = load_auth()
        except (OSError, ValueError) as exc:
            log.error("remote auth: %s", exc)
            return 1
        gate = RemoteGate(machine, events, auth)
        httpd = start_remote(gate)

    if not args.once:
        cam = gate.media.camera if gate is not None else CameraHub()
        sentry = Sentry(machine, cam, cues=cues)

    if not args.once and not args.no_awake:
        awake = AwakeSession(machine, events, cues=cues, timeout_s=load_idle_timeout_s())
        awake.start()
        if not args.no_mic:
            try:
                from awake.mic import MicWake

                mic = MicWake(awake)
                mic.start()
            except Exception as exc:
                log.warning("mic wake disabled: %s", exc)
                mic = None
            if sentry is not None:
                sentry.mic = mic
            if gate is not None:
                gate.mic = mic

    def _stop(*_a: object) -> None:
        nonlocal stopping
        stopping = True
        events.put(Event.EXIT_TO_IDLE)

    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)

    def on_tick() -> None:
        if gate is not None:
            gate.check_timeout()
        if awake is not None:
            awake.check_timeout()
        battery.tick()
        cues.tick(machine.mode)
        if sentry is not None:
            sentry.tick()

    def on_mode(prev: str, now: str) -> None:
        if now == "AWAKE" and prev == "IDLE":
            from awake.halt import mode_cmd
            from awake.talk import run_awake

            # Sync Safety/Bus before any drive/follow; do not block greeting on ros2 CLI
            threading.Thread(
                target=mode_cmd,
                args=("AWAKE",),
                name="awake-mode",
                daemon=True,
            ).start()
            threading.Thread(
                target=run_awake,
                kwargs={"machine": machine, "session": awake, "cues": cues, "mic": mic},
                name="awake-talk",
                daemon=True,
            ).start()
            return
        if now == "REMOTE" and mic is not None:
            mic.set_paused(True)
            return
        if prev == "REMOTE" and now != "REMOTE" and mic is not None:
            mic.set_paused(False)
        if prev == "AWAKE" and now != "AWAKE":
            try:
                from awake.halt import drive_stop, mode_cmd

                drive_stop()
                if now == "IDLE":
                    mode_cmd("IDLE")
            except Exception as exc:
                log.warning("awake leave cleanup: %s", exc)
            if mic is not None:
                mic.set_paused(False)

    log.info("personal_ai started mode=%s (no motion)", machine.mode)
    try:
        run(
            machine,
            events,
            on_tick=on_tick,
            on_mode=on_mode,
            once=args.once,
            should_stop=lambda: stopping,
        )
    finally:
        from remote import gimbal

        gimbal.shutdown(home=False)
        if httpd is not None:
            httpd.shutdown()
        if mic is not None:
            mic.close()
        if awake is not None:
            awake.close()
        if sentry is not None:
            sentry.close()
        battery.close()
        cues.close()
        log.info("exit mode=%s estop=%s", machine.mode, machine.estop)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
