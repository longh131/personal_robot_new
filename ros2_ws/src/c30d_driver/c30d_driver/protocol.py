"""C30D 11-byte velocity frame (H1). Mec-S: zero/timeout PWM=0, not industrial e-stop."""

from __future__ import annotations


def xor_bcc(data: bytes) -> int:
    r = 0
    for b in data:
        r ^= b
    return r


def build_velocity_frame(vx: int, vy: int, wz: int) -> bytes:
    body = bytearray([0x7B, 0x00, 0x00])
    body += int(vx).to_bytes(2, 'big', signed=True)
    body += int(vy).to_bytes(2, 'big', signed=True)
    body += int(wz).to_bytes(2, 'big', signed=True)
    body.append(xor_bcc(body))
    body.append(0x7D)
    return bytes(body)


def clamp_int16(value: float) -> int:
    v = int(round(value))
    return max(-32768, min(32767, v))


def twist_to_counts(lin_x: float, lin_y: float, ang_z: float, scale: float, limit: int) -> tuple[int, int, int]:
    vx = clamp_int16(lin_x * scale)
    vy = clamp_int16(lin_y * scale)
    wz = clamp_int16(ang_z * scale)
    lim = abs(int(limit))
    vx = max(-lim, min(lim, vx))
    vy = max(-lim, min(lim, vy))
    wz = max(-lim, min(lim, wz))
    return vx, vy, wz


def _i16be(high: int, low: int) -> int:
    v = (high << 8) | low
    if v >= 32768:
        v -= 65536
    return v


def parse_feedback_frame(frame: bytes) -> dict | None:
    if len(frame) != 24 or frame[0] != 0x7B or frame[23] != 0x7D:
        return None
    if xor_bcc(frame[:22]) != frame[22]:
        return None
    return {
        'flag_stop': frame[1],
        'vx': _i16be(frame[2], frame[3]) / 1000.0,
        'vy': _i16be(frame[4], frame[5]) / 1000.0,
        'wz': _i16be(frame[6], frame[7]) / 1000.0,
        'voltage': _i16be(frame[20], frame[21]) / 1000.0,
    }


def build_feedback_frame(vx_mm: int, vy_mm: int, wz_mm: int, flag_stop: int = 0, voltage_mv: int = 12000) -> bytes:
    buf = bytearray(24)
    buf[0] = 0x7B
    buf[1] = flag_stop & 0xFF
    buf[2:4] = int(vx_mm).to_bytes(2, 'big', signed=True)
    buf[4:6] = int(vy_mm).to_bytes(2, 'big', signed=True)
    buf[6:8] = int(wz_mm).to_bytes(2, 'big', signed=True)
    buf[20:22] = int(voltage_mv).to_bytes(2, 'big', signed=True)
    buf[22] = xor_bcc(bytes(buf[:22]))
    buf[23] = 0x7D
    return bytes(buf)


class FeedbackParser:
    def __init__(self, max_buf: int = 256) -> None:
        self._buf = bytearray()
        self._max = max_buf

    def push(self, data: bytes) -> list[dict]:
        if data:
            self._buf.extend(data)
        if len(self._buf) > self._max:
            del self._buf[:-self._max]
        out: list[dict] = []
        while len(self._buf) >= 24:
            if self._buf[0] != 0x7B:
                del self._buf[0]
                continue
            if self._buf[23] != 0x7D:
                del self._buf[0]
                continue
            parsed = parse_feedback_frame(bytes(self._buf[:24]))
            del self._buf[:24]
            if parsed is not None:
                out.append(parsed)
        return out
