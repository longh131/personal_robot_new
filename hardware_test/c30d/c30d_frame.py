"""C30D 候选组帧（假设 H1，未证实为当前固件协议）。"""

from __future__ import annotations

DEVICE = "/dev/c30d"
BAUD = 115200
# 低速档整数；单位未证实。与单次前进脚本同量级。
LOW_SPEED = 60

CANDIDATE_NOTE = (
    "HYPOTHESIS H1: 11-byte frame 7B 00 00 vx/vy/wz int16BE xor 7D @115200. "
    "Not confirmed against current firmware."
)


def xor_bcc(data: bytes) -> int:
    r = 0
    for b in data:
        r ^= b
    return r


def build_velocity_frame(vx: int, vy: int, wz: int) -> bytes:
    body = bytearray([0x7B, 0x00, 0x00])
    body += int(vx).to_bytes(2, "big", signed=True)
    body += int(vy).to_bytes(2, "big", signed=True)
    body += int(wz).to_bytes(2, "big", signed=True)
    body.append(xor_bcc(body))
    body.append(0x7D)
    return bytes(body)


def command_to_twist(key: str) -> tuple[int, int, int] | None:
    k = key.lower()
    s = LOW_SPEED
    mapping = {
        "w": (s, 0, 0),
        "s": (-s, 0, 0),
        "a": (0, s, 0),
        "d": (0, -s, 0),
        "q": (0, 0, s),
        "e": (0, 0, -s),
    }
    return mapping.get(k)
