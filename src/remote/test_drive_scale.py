# -*- coding: utf-8 -*-
from remote import ros_bridge


def test_speed_scale_clamps(monkeypatch):
    monkeypatch.setattr(ros_bridge, "_limits", lambda: (0.15, 0.15, 0.40))
    writes = []

    class Stdin:
        def write(self, s):
            writes.append(s)

        def flush(self):
            pass

    class FakeProc:
        def __init__(self):
            self.stdin = Stdin()

    monkeypatch.setattr(ros_bridge, "_ensure_twist", lambda: FakeProc())
    ros_bridge.set_speed_scale(1.0)
    out = ros_bridge.drive(1, 0, 0)
    assert abs(out["vx"] - 0.15) < 1e-6
    ros_bridge.set_speed_scale(0.5)
    out = ros_bridge.drive(1, 0, 0)
    assert abs(out["vx"] - 0.075) < 1e-6
    assert ros_bridge.set_speed_scale(9)["scale"] == 1.0
    assert ros_bridge.set_speed_scale(0.01)["scale"] == 0.2
