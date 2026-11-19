from safety_manager.obstacle import (
    apply_front_stop,
    apply_motion_stop,
    direction_mins,
    front_min_range,
)


def test_front_min_finds_ahead():
    n = 720
    ranges = [float('inf')] * n
    ranges[0] = 0.5
    ranges[10] = 0.3
    got = front_min_range(
        ranges,
        angle_min=0.0,
        angle_increment=(2.0 * 3.14159265) / n,
        front_deg=50.0,
        range_min=0.05,
        range_max=8.0,
    )
    assert got is not None
    assert abs(got - 0.3) < 1e-6


def test_ignore_body_return():
    n = 720
    ranges = [float('inf')] * n
    ranges[0] = 0.21
    ranges[5] = 0.50
    got = front_min_range(
        ranges,
        angle_min=0.0,
        angle_increment=(2.0 * 3.14159265) / n,
        front_deg=50.0,
        range_min=0.05,
        range_max=8.0,
        ignore_below_m=0.28,
    )
    assert got is not None
    assert abs(got - 0.50) < 1e-6


def test_apply_blocks_forward():
    vx, vy, wz, blocked = apply_front_stop(0.15, 0.0, 0.0, 0.3, stop_m=0.4, hard_m=0.22)
    assert blocked and vx == 0.0


def test_apply_blocks_reverse():
    mins = {"front": None, "rear": 0.35, "left": None, "right": None}
    vx, vy, wz, blocked, why = apply_motion_stop(
        -0.1, 0.0, 0.0, mins, stop_m=0.4, hard_m=0.22,
    )
    assert blocked and vx == 0.0 and "rear" in why


def test_apply_blocks_strafe():
    mins = {"front": None, "rear": None, "left": 0.32, "right": None}
    vx, vy, wz, blocked, why = apply_motion_stop(
        0.0, 0.1, 0.0, mins, stop_m=0.4, hard_m=0.22,
    )
    assert blocked and vy == 0.0 and "left" in why


def test_hard_stop():
    mins = {"front": None, "rear": None, "left": 0.15, "right": None}
    vx, vy, wz, blocked, why = apply_motion_stop(
        0.0, 0.1, 0.2, mins, stop_m=0.4, hard_m=0.22,
    )
    assert blocked and vx == 0 and vy == 0 and wz == 0 and why.startswith("hard:")


def test_direction_mins_rear():
    n = 720
    inc = (2.0 * 3.14159265) / n
    ranges = [float('inf')] * n
    # ~180 deg index
    idx = int((3.14159265 - 0.0) / inc) % n
    ranges[idx] = 0.4
    mins = direction_mins(
        ranges,
        angle_min=0.0,
        angle_increment=inc,
        half_deg=50.0,
        range_min=0.05,
        range_max=8.0,
        ignore_below_m=0.28,
    )
    assert mins["rear"] is not None
    assert abs(mins["rear"] - 0.4) < 0.05
