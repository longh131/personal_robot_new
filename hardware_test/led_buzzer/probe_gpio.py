#!/usr/bin/env python3
"""短测 Pi GPIO：LED BCM16 闪 3 次，蜂鸣 BCM12 软件 PWM 2 kHz 约 0.4s。结束拉低。"""
from __future__ import annotations

import ctypes
import fcntl
import os
import time

CHIP = "/dev/gpiochip4"
LED = 16
BUZZ = 12
CONSUMER = b"pr-led-buzz"

GPIO_V2_LINE_FLAG_OUTPUT = 1 << 3
GPIO_MAX_NAME = 32
GPIO_V2_LINES_MAX = 64
GPIO_V2_LINE_NUM_ATTRS_MAX = 10


def _io(dir_, nr, size, typ=0xB4):
    return (dir_ << 30) | (size << 16) | (typ << 8) | nr


class LineAttr(ctypes.Structure):
    _fields_ = [
        ("id", ctypes.c_uint32),
        ("padding", ctypes.c_uint32),
        ("flags", ctypes.c_uint64),
    ]


class LineConfigAttr(ctypes.Structure):
    _fields_ = [("attr", LineAttr), ("mask", ctypes.c_uint64)]


class LineConfig(ctypes.Structure):
    _fields_ = [
        ("flags", ctypes.c_uint64),
        ("num_attrs", ctypes.c_uint32),
        ("padding", ctypes.c_uint32 * 5),
        ("attrs", LineConfigAttr * GPIO_V2_LINE_NUM_ATTRS_MAX),
    ]


class LineRequest(ctypes.Structure):
    _fields_ = [
        ("offsets", ctypes.c_uint32 * GPIO_V2_LINES_MAX),
        ("consumer", ctypes.c_char * GPIO_MAX_NAME),
        ("config", LineConfig),
        ("num_lines", ctypes.c_uint32),
        ("event_buffer_size", ctypes.c_uint32),
        ("padding", ctypes.c_uint32 * 5),
        ("fd", ctypes.c_int32),
    ]


class LineInfo(ctypes.Structure):
    _fields_ = [
        ("name", ctypes.c_char * GPIO_MAX_NAME),
        ("consumer", ctypes.c_char * GPIO_MAX_NAME),
        ("offset", ctypes.c_uint32),
        ("num_attrs", ctypes.c_uint32),
        ("flags", ctypes.c_uint64),
        ("attrs", LineAttr * GPIO_V2_LINE_NUM_ATTRS_MAX),
        ("padding", ctypes.c_uint32 * 4),
    ]


class LineValues(ctypes.Structure):
    _fields_ = [("bits", ctypes.c_uint64), ("mask", ctypes.c_uint64)]


GPIO_V2_GET_LINEINFO = _io(3, 0x05, ctypes.sizeof(LineInfo))
GPIO_V2_GET_LINE = _io(3, 0x07, ctypes.sizeof(LineRequest))
GPIO_V2_LINE_SET_VALUES = _io(3, 0x0F, ctypes.sizeof(LineValues))


def lineinfo(chip_fd: int, offset: int) -> LineInfo:
    info = LineInfo()
    info.offset = offset
    fcntl.ioctl(chip_fd, GPIO_V2_GET_LINEINFO, info)
    return info


def request_out(chip_fd: int, offset: int) -> int:
    req = LineRequest()
    req.offsets[0] = offset
    req.consumer = CONSUMER
    req.config.flags = GPIO_V2_LINE_FLAG_OUTPUT
    req.num_lines = 1
    fcntl.ioctl(chip_fd, GPIO_V2_GET_LINE, req)
    if req.fd <= 0:
        raise OSError("GET_LINE fd invalid")
    return req.fd


def set_val(line_fd: int, on: bool) -> None:
    v = LineValues()
    v.mask = 1
    v.bits = 1 if on else 0
    fcntl.ioctl(line_fd, GPIO_V2_LINE_SET_VALUES, v)


def main() -> None:
    chip = os.open(CHIP, os.O_RDONLY)
    try:
        for off in (LED, BUZZ):
            info = lineinfo(chip, off)
            used = bool(info.flags & 1)
            print(
                f"GPIO{off} name={info.name!r} consumer={info.consumer!r} "
                f"flags={info.flags:#x} used={used}"
            )
            if used:
                raise SystemExit(f"GPIO{off} 已被占用，停止")

        led_fd = request_out(chip, LED)
        buzz_fd = request_out(chip, BUZZ)
        try:
            print("LED: 闪 3 次")
            for _ in range(3):
                set_val(led_fd, True)
                time.sleep(0.25)
                set_val(led_fd, False)
                time.sleep(0.25)

            print("BUZZ: 2 kHz ~0.4s")
            period = 1.0 / 2000.0
            half = period / 2.0
            end = time.perf_counter() + 0.4
            while time.perf_counter() < end:
                set_val(buzz_fd, True)
                t0 = time.perf_counter()
                while time.perf_counter() - t0 < half:
                    pass
                set_val(buzz_fd, False)
                t0 = time.perf_counter()
                while time.perf_counter() - t0 < half:
                    pass
        finally:
            set_val(led_fd, False)
            set_val(buzz_fd, False)
            os.close(led_fd)
            os.close(buzz_fd)
            print("已拉低并释放 GPIO16/12")
    finally:
        os.close(chip)


if __name__ == "__main__":
    main()
