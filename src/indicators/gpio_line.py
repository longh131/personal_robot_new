# -*- coding: utf-8 -*-
"""RP1 gpiochip output line."""

from __future__ import annotations

import ctypes
import fcntl
import os

CHIP = "/dev/gpiochip4"
GPIO_V2_LINE_FLAG_OUTPUT = 1 << 3
GPIO_MAX_NAME = 32
GPIO_V2_LINES_MAX = 64
GPIO_V2_ATTRS = 10


def _io(dir_: int, nr: int, size: int, typ: int = 0xB4) -> int:
    return (dir_ << 30) | (size << 16) | (typ << 8) | nr


class _LineAttr(ctypes.Structure):
    _fields_ = [("id", ctypes.c_uint32), ("padding", ctypes.c_uint32), ("flags", ctypes.c_uint64)]


class _LineConfigAttr(ctypes.Structure):
    _fields_ = [("attr", _LineAttr), ("mask", ctypes.c_uint64)]


class _LineConfig(ctypes.Structure):
    _fields_ = [
        ("flags", ctypes.c_uint64),
        ("num_attrs", ctypes.c_uint32),
        ("padding", ctypes.c_uint32 * 5),
        ("attrs", _LineConfigAttr * GPIO_V2_ATTRS),
    ]


class _LineRequest(ctypes.Structure):
    _fields_ = [
        ("offsets", ctypes.c_uint32 * GPIO_V2_LINES_MAX),
        ("consumer", ctypes.c_char * GPIO_MAX_NAME),
        ("config", _LineConfig),
        ("num_lines", ctypes.c_uint32),
        ("event_buffer_size", ctypes.c_uint32),
        ("padding", ctypes.c_uint32 * 5),
        ("fd", ctypes.c_int32),
    ]


class _LineValues(ctypes.Structure):
    _fields_ = [("bits", ctypes.c_uint64), ("mask", ctypes.c_uint64)]


_GET_LINE = _io(3, 0x07, ctypes.sizeof(_LineRequest))
_SET_VALUES = _io(3, 0x0F, ctypes.sizeof(_LineValues))


class GpioLine:
    def __init__(self, offset: int, consumer: bytes = b"personal-ai") -> None:
        self._chip = os.open(CHIP, os.O_RDONLY)
        req = _LineRequest()
        req.offsets[0] = offset
        req.consumer = consumer
        req.config.flags = GPIO_V2_LINE_FLAG_OUTPUT
        req.num_lines = 1
        fcntl.ioctl(self._chip, _GET_LINE, req)
        if req.fd <= 0:
            os.close(self._chip)
            raise OSError("GPIO_V2_GET_LINE failed")
        self._fd = req.fd

    def set(self, on: bool) -> None:
        v = _LineValues()
        v.mask = 1
        v.bits = 1 if on else 0
        fcntl.ioctl(self._fd, _SET_VALUES, v)

    def close(self) -> None:
        try:
            self.set(False)
        except OSError:
            pass
        os.close(self._fd)
        os.close(self._chip)
