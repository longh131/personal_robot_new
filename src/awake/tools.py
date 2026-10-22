# -*- coding: utf-8 -*-
"""AWAKE local tools. No motors, no REMOTE."""

from __future__ import annotations

import logging
from datetime import datetime
from zoneinfo import ZoneInfo

log = logging.getLogger("awake.tools")

TIME_HINTS = ("几点", "几點", "什么时候了", "現在時間", "现在时间", "报时", "報時")
DATE_HINTS = ("几号", "幾號", "几月", "日期", "星期几", "星期幾", "周几", "週幾", "今天星期")
BATTERY_HINTS = ("电量", "電量", "电池", "電池", "还有电", "還有電", "充电没", "充電沒")
_WEEK = "一二三四五六日"


def _tz(_ident: dict | None = None) -> ZoneInfo:
    from settings import robot_get

    name = str(robot_get("timezone", default="Asia/Shanghai") or "Asia/Shanghai")
    try:
        return ZoneInfo(name)
    except Exception:
        return ZoneInfo("Asia/Shanghai")


def _now(ident: dict | None) -> datetime:
    return datetime.now(_tz(ident))


def needs_time(text: str) -> bool:
    return any(k in (text or "") for k in TIME_HINTS)


def needs_date(text: str) -> bool:
    return any(k in (text or "") for k in DATE_HINTS)


def needs_battery(text: str) -> bool:
    return any(k in (text or "") for k in BATTERY_HINTS)


def get_time(ident: dict | None = None) -> str:
    now = _now(ident)
    text = f"现在是{now.hour}点{now.minute:02d}分"
    log.info("tool get_time %s", text)
    return text


def get_date(ident: dict | None = None) -> str:
    now = _now(ident)
    week = _WEEK[now.weekday()]
    text = f"今天是{now.year}年{now.month}月{now.day}日，星期{week}"
    log.info("tool get_date %s", text)
    return text


def read_battery(ident: dict | None = None) -> tuple[int, str]:
    from settings import robot_get

    _ = ident
    try:
        import smbus
    except ImportError as exc:
        raise RuntimeError("no smbus") from exc
    bus_n = int(robot_get("ups", "i2c_bus", default=1) or 1)
    addr = int(str(robot_get("ups", "i2c_addr", default="0x2d") or "0x2d"), 0)
    bus = smbus.SMBus(bus_n)
    try:
        st = bus.read_i2c_block_data(addr, 0x02, 1)[0]
        data = bus.read_i2c_block_data(addr, 0x20, 12)
    finally:
        bus.close()
    if len(data) < 6:
        raise RuntimeError("ups short read")
    pct = max(0, min(100, int(data[4] | data[5] << 8)))
    current = data[2] | data[3] << 8
    if current > 0x7FFF:
        current -= 0xFFFF
    if st & 0x40:
        state = "快充"
    elif st & 0x80 or current > 50:
        state = "充电"
    elif st & 0x20 or current < -50:
        state = "放电"
    else:
        state = "空闲"
    return pct, state


def get_battery(ident: dict | None = None) -> str:
    pct, state = read_battery(ident)
    text = f"电池大约{pct}%，目前{state}"
    log.info("tool get_battery %s", text)
    return text
