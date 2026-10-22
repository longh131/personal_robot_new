#!/usr/bin/env python3
"""静态测试：组帧与 CLI 门闩。不开串口、不运动。"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from c30d_frame import LOW_SPEED, build_velocity_frame, command_to_twist  # noqa: E402

SCRIPT = Path(__file__).resolve().parent / "c30d_keyboard_teleop.py"


def test_frames() -> None:
    assert len(build_velocity_frame(60, 0, 0)) == 11
    assert build_velocity_frame(60, 0, 0).hex() == "7b0000003c00000000477d"
    assert build_velocity_frame(-60, 0, 0).hex() == "7b0000ffc400000000407d"
    assert build_velocity_frame(0, 60, 0).hex() == "7b00000000003c0000477d"
    assert build_velocity_frame(0, 0, 0).hex() == "7b00000000000000007b7d"
    assert command_to_twist("w") == (LOW_SPEED, 0, 0)
    assert command_to_twist("s") == (-LOW_SPEED, 0, 0)
    assert command_to_twist(" ") is None


def test_cli() -> None:
    env = os.environ.copy()
    env.pop("C30D_ALLOW_EXECUTE", None)
    r = subprocess.run([sys.executable, str(SCRIPT)], capture_output=True, text=True, env=env)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "CHECK_OK" in r.stdout
    assert "no serial open" in r.stdout
    r2 = subprocess.run(
        [sys.executable, str(SCRIPT), "--execute-teleop"],
        capture_output=True, text=True, env=env,
    )
    assert r2.returncode == 2
    r3 = subprocess.run(
        [
            sys.executable, str(SCRIPT),
            "--execute-teleop", "--confirm-wheels-off", "--confirm-power-cut-ready",
        ],
        capture_output=True, text=True, env=env,
    )
    assert r3.returncode == 2
    assert "C30D_ALLOW_EXECUTE" in r3.stdout


if __name__ == "__main__":
    test_frames()
    test_cli()
    print("STATIC_TESTS_OK")
