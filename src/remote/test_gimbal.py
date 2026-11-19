from remote.gimbal import active_axis, clamp_pulse, pulse_to_value, step_pulse


def test_clamp():
    assert clamp_pulse(0.0005, 0.001, 0.002) == 0.001
    assert clamp_pulse(0.003, 0.001, 0.002) == 0.002


def test_step_one_axis():
    pan = 0.0015
    pan = step_pulse(pan, 0.0001, 0.001, 0.002)
    assert pan == 0.0016
    tilt = 0.0015
    assert tilt == 0.0015


def test_step_stops_at_limit():
    v = 0.0015
    hit = False
    for _ in range(500):
        n = step_pulse(v, -0.000012, 0.001, 0.002)
        if n == v:
            assert v == 0.001
            hit = True
            break
        v = n
    assert hit


def test_active_axis_mutex():
    assert active_axis("left", 0.0015, 0.0015, 0.0015, 0.00004) == "pan"
    assert active_axis("up", 0.0015, 0.0015, 0.0015, 0.00004) == "tilt"
    assert active_axis(None, 0.0015, 0.0015, 0.0015, 0.00004) is None
    assert active_axis("stop", 0.0015, 0.0015, 0.0015, 0.00004) is None
    assert active_axis("home", 0.0012, 0.0018, 0.0015, 0.00004) == "pan"
    assert active_axis("home", 0.0015, 0.0018, 0.0015, 0.00004) == "tilt"
    assert active_axis("home", 0.0015, 0.0015, 0.0015, 0.00004) is None


def test_pulse_to_value():
    assert pulse_to_value(0.0015, 0.001, 0.002) == 0.0
    assert pulse_to_value(0.0010, 0.001, 0.002) == -1.0
    assert pulse_to_value(0.0020, 0.001, 0.002) == 1.0
