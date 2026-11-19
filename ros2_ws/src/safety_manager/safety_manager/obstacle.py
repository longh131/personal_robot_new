# -*- coding: utf-8 -*-
"""Directional obstacle ranges from LaserScan. Pure helpers for tests."""

from __future__ import annotations

import math
from typing import Sequence


def _norm_pi(ang: float) -> float:
    return (ang + math.pi) % (2.0 * math.pi) - math.pi


def sector_min_range(
    ranges: Sequence[float],
    *,
    angle_min: float,
    angle_increment: float,
    center_deg: float,
    half_deg: float,
    range_min: float,
    range_max: float,
    ignore_below_m: float = 0.0,
    angle_offset_deg: float = 0.0,
) -> float | None:
    """Minimum valid range in a sector centered at center_deg (robot frame)."""
    if not ranges or angle_increment == 0.0:
        return None
    half = math.radians(max(1.0, half_deg))
    center = math.radians(center_deg) + math.radians(angle_offset_deg)
    floor = max(float(range_min), float(ignore_below_m))
    best: float | None = None
    for i, raw in enumerate(ranges):
        r = float(raw)
        if not math.isfinite(r) or r < floor or r > range_max:
            continue
        ang = angle_min + i * angle_increment
        if abs(_norm_pi(ang - center)) > half:
            continue
        if best is None or r < best:
            best = r
    return best


def front_min_range(
    ranges: Sequence[float],
    *,
    angle_min: float,
    angle_increment: float,
    front_deg: float,
    range_min: float,
    range_max: float,
    ignore_below_m: float = 0.0,
    angle_offset_deg: float = 0.0,
) -> float | None:
    """Backward-compatible: front sector about +x (0°)."""
    return sector_min_range(
        ranges,
        angle_min=angle_min,
        angle_increment=angle_increment,
        center_deg=0.0,
        half_deg=front_deg,
        range_min=range_min,
        range_max=range_max,
        ignore_below_m=ignore_below_m,
        angle_offset_deg=angle_offset_deg,
    )


def direction_mins(
    ranges: Sequence[float],
    *,
    angle_min: float,
    angle_increment: float,
    half_deg: float,
    range_min: float,
    range_max: float,
    ignore_below_m: float = 0.0,
    angle_offset_deg: float = 0.0,
) -> dict[str, float | None]:
    """Mins for forward/back/left/right. ROS: +x forward, +y left."""
    kw = dict(
        angle_min=angle_min,
        angle_increment=angle_increment,
        half_deg=half_deg,
        range_min=range_min,
        range_max=range_max,
        ignore_below_m=ignore_below_m,
        angle_offset_deg=angle_offset_deg,
    )
    return {
        "front": sector_min_range(ranges, center_deg=0.0, **kw),
        "rear": sector_min_range(ranges, center_deg=180.0, **kw),
        "left": sector_min_range(ranges, center_deg=90.0, **kw),
        "right": sector_min_range(ranges, center_deg=-90.0, **kw),
    }


def apply_motion_stop(
    vx: float,
    vy: float,
    wz: float,
    mins: dict[str, float | None],
    *,
    stop_m: float,
    hard_m: float,
    eps: float = 1e-4,
) -> tuple[float, float, float, bool, str]:
    """Zero velocity components that drive into a near obstacle.

    hard_m in the travel direction → full stop. stop_m → zero that axis only.
    """
    active: list[tuple[str, float | None]] = []
    if vx > eps:
        active.append(("front", mins.get("front")))
    if vx < -eps:
        active.append(("rear", mins.get("rear")))
    if vy > eps:
        active.append(("left", mins.get("left")))
    if vy < -eps:
        active.append(("right", mins.get("right")))

    if not active:
        return vx, vy, wz, False, ""

    for name, d in active:
        if d is not None and d < hard_m:
            return 0.0, 0.0, 0.0, True, f"hard:{name}:{d:.3f}"

    blocked = False
    reasons: list[str] = []
    if vx > eps:
        d = mins.get("front")
        if d is not None and d < stop_m:
            vx = 0.0
            blocked = True
            reasons.append(f"front:{d:.3f}")
    if vx < -eps:
        d = mins.get("rear")
        if d is not None and d < stop_m:
            vx = 0.0
            blocked = True
            reasons.append(f"rear:{d:.3f}")
    if vy > eps:
        d = mins.get("left")
        if d is not None and d < stop_m:
            vy = 0.0
            blocked = True
            reasons.append(f"left:{d:.3f}")
    if vy < -eps:
        d = mins.get("right")
        if d is not None and d < stop_m:
            vy = 0.0
            blocked = True
            reasons.append(f"right:{d:.3f}")

    return vx, vy, wz, blocked, ",".join(reasons)


def apply_front_stop(
    vx: float,
    vy: float,
    wz: float,
    front_min: float | None,
    *,
    stop_m: float,
    hard_m: float,
) -> tuple[float, float, float, bool]:
    """Legacy helper kept for older tests."""
    mins = {"front": front_min, "rear": None, "left": None, "right": None}
    out_vx, out_vy, out_wz, blocked, _ = apply_motion_stop(
        vx, vy, wz, mins, stop_m=stop_m, hard_m=hard_m,
    )
    return out_vx, out_vy, out_wz, blocked
