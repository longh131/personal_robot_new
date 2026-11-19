#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""单轴舵机扫程（gpiozero+lgpio）。默认 BCM24。不碰底盘。

用法：
  .venv/bin/python hardware_test/gimbal/servo_lgpio_sweep.py
  .venv/bin/python hardware_test/gimbal/servo_lgpio_sweep.py --bcm 19
"""

from __future__ import annotations

import argparse
from time import sleep

from gpiozero import Device, Servo
from gpiozero.pins.lgpio import LGPIOFactory

Device.pin_factory = LGPIOFactory()


def main() -> int:
    p = argparse.ArgumentParser(description="MG90S sweep via lgpio")
    p.add_argument("--bcm", type=int, default=24, help="BCM pin (pan=24 tilt=19)")
    args = p.parse_args()
    servo = Servo(args.bcm, min_pulse_width=0.001, max_pulse_width=0.002, frame_width=0.02)
    try:
        print(f"BCM{args.bcm} mid")
        servo.mid()
        sleep(1)
        print("min")
        servo.min()
        sleep(1)
        print("max")
        servo.max()
        sleep(1)
        print("mid")
        servo.mid()
        sleep(1)
    finally:
        servo.detach()
        servo.close()
        print("detached")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
