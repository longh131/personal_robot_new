# -*- coding: utf-8 -*-
"""In-process countdown / remind jobs. No motors. Survives AWAKE→IDLE until process exit."""

from __future__ import annotations

import logging
import re
import threading
import time
import uuid
from dataclasses import dataclass

log = logging.getLogger("awake.scheduler")

_CN = {
    "半": 0.5,
    "零": 0,
    "一": 1,
    "二": 2,
    "两": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
    "十": 10,
}


@dataclass
class Job:
    id: str
    kind: str  # countdown | remind | alarm
    fire_at: float
    message: str
    cancelled: bool = False


_lock = threading.Lock()
_jobs: list[Job] = []


def _parse_cn_int(chunk: str) -> float | None:
    chunk = (chunk or "").strip()
    if not chunk:
        return None
    if chunk.isdigit():
        return float(chunk)
    if chunk in _CN:
        return float(_CN[chunk])
    if chunk.startswith("十"):
        rest = chunk[1:]
        return 10.0 + (_CN.get(rest, 0) if rest else 0)
    if "十" in chunk:
        left, _, right = chunk.partition("十")
        tens = _CN.get(left, 1) if left else 1
        ones = _CN.get(right, 0) if right else 0
        return float(tens * 10 + ones)
    return None


def parse_duration_s(text: str) -> float | None:
    """Parse '...N秒/分钟/小时...' → seconds. None if missing."""
    t = "".join((text or "").split())
    # N小时M分 / N分M秒 / plain
    m = re.search(
        r"([半零一二两三四五六七八九十\d]+)(?:个)?(小时|钟头|分钟|分|秒钟|秒)",
        t,
    )
    if not m:
        return None
    n = _parse_cn_int(m.group(1))
    if n is None:
        return None
    unit = m.group(2)
    if unit in ("小时", "钟头"):
        sec = n * 3600.0
    elif unit in ("分钟", "分"):
        sec = n * 60.0
    else:
        sec = n
    # optional second unit: 1小时30分
    rest = t[m.end() :]
    m2 = re.search(
        r"([半零一二两三四五六七八九十\d]+)(?:个)?(分钟|分|秒钟|秒)",
        rest,
    )
    if m2 and unit in ("小时", "钟头"):
        n2 = _parse_cn_int(m2.group(1))
        if n2 is not None:
            if m2.group(2) in ("分钟", "分"):
                sec += n2 * 60.0
            else:
                sec += n2
    return max(1.0, min(24 * 3600.0, float(sec)))


def parse_remind_message(text: str) -> str:
    t = "".join((text or "").split())
    for sep in ("提醒我", "叫我", "告诉我"):
        if sep in t:
            msg = t.split(sep, 1)[-1]
            msg = re.sub(
                r"^([半零一二两三四五六七八九十\d]+)(?:个)?(小时|钟头|分钟|分|秒钟|秒)后?",
                "",
                msg,
            )
            msg = msg.strip("，,。 ")
            return msg or "到时间了"
    return "到时间了"


def add_job(kind: str, seconds: float, message: str) -> Job:
    job = Job(
        id=uuid.uuid4().hex[:8],
        kind=kind,
        fire_at=time.monotonic() + max(1.0, float(seconds)),
        message=(message or "到时间了").strip()[:120],
    )
    with _lock:
        _jobs.append(job)
    log.info("timer add id=%s kind=%s in=%.1fs msg=%s", job.id, kind, seconds, job.message)
    return job


def cancel_kind(kind: str | None = None) -> int:
    n = 0
    with _lock:
        for j in _jobs:
            if j.cancelled:
                continue
            if kind is None or j.kind == kind:
                j.cancelled = True
                n += 1
    log.info("timer cancel kind=%s n=%s", kind or "all", n)
    return n


def list_active() -> list[Job]:
    now = time.monotonic()
    with _lock:
        return [j for j in _jobs if not j.cancelled and j.fire_at > now]


def pop_due() -> list[Job]:
    now = time.monotonic()
    due: list[Job] = []
    with _lock:
        keep: list[Job] = []
        for j in _jobs:
            if j.cancelled:
                continue
            if j.fire_at <= now:
                due.append(j)
            else:
                keep.append(j)
        _jobs[:] = keep
    return due


def format_remaining(job: Job) -> str:
    left = max(0, int(job.fire_at - time.monotonic()))
    if left >= 3600:
        return f"{left // 3600}小时{(left % 3600) // 60}分"
    if left >= 60:
        return f"{left // 60}分{left % 60}秒"
    return f"{left}秒"
