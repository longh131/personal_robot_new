#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""只读探测 LD14/MS200 系 USB 雷达。不开电机、不写 ROS。"""

from __future__ import annotations

import argparse
import struct
import time
from pathlib import Path

DEFAULT = Path("/dev/serial/by-id/usb-STC_STC_USB_Serial-if00")


def parse_frames(buf: bytes) -> list[tuple[float, float, int, int, int]]:
    out: list[tuple[float, float, int, int, int]] = []
    i = 0
    while i + 10 < len(buf):
        if buf[i] != 0xAA or buf[i + 1] != 0x55:
            i += 1
            continue
        ct = buf[i + 2]
        lsn = buf[i + 3]
        if lsn == 0 or lsn > 100:
            i += 1
            continue
        size = 10 + lsn * 3
        if i + size > len(buf):
            break
        fsa = struct.unpack_from("<H", buf, i + 4)[0]
        lsa = struct.unpack_from("<H", buf, i + 6)[0]
        a0 = ((fsa >> 1) / 64.0) % 360.0
        a1 = ((lsa >> 1) / 64.0) % 360.0
        dist = struct.unpack_from("<H", buf, i + 10)[0] if lsn else 0
        out.append((a0, a1, ct & 0x01, lsn, dist))
        i += size
    return out


def main() -> int:
    p = argparse.ArgumentParser(description="probe LD14/MS200 lidar")
    p.add_argument("--port", default=str(DEFAULT))
    p.add_argument("--baud", type=int, default=150000, help="seller driver uses 150000")
    p.add_argument("--seconds", type=float, default=2.0)
    p.add_argument("--start", action="store_true", help="send A5 60 start")
    args = p.parse_args()

    import serial

    port = Path(args.port)
    if not port.exists():
        print(f"missing {port}")
        return 1
    ser = serial.Serial(str(port), args.baud, timeout=0.5)
    if args.start:
        ser.write(bytes([0xA5, 0x60]))
        time.sleep(0.3)
    buf = bytearray()
    t0 = time.time()
    while time.time() - t0 < args.seconds:
        chunk = ser.read(4096)
        if chunk:
            buf.extend(chunk)
    if args.start:
        ser.write(bytes([0xA5, 0x65]))
    ser.close()
    frames = parse_frames(bytes(buf))
    bins = [0] * 12
    for a0, _a1, ct, _lsn, _d in frames:
        if ct:
            continue
        bins[int(a0) // 30] += 1
    print(f"port={port} baud={args.baud} bytes={len(buf)} frames={len(frames)}")
    print(f"30deg_bins={bins}")
    print("front/back: 360° 扫描。零角度在机壳刻度/线缆侧，装车时对齐车头，软件用 angle_offset。")
    if sum(bins) < 20:
        print("WARN: few frames; check power/USB and that motor spins")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
