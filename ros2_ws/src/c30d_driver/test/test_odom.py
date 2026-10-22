from c30d_driver.odom import OdomIntegrator
from c30d_driver.protocol import FeedbackParser, build_feedback_frame, parse_feedback_frame


def test_parse_stationary():
    frame = build_feedback_frame(0, 0, 0, voltage_mv=11710)
    fb = parse_feedback_frame(frame)
    assert fb is not None
    assert fb['vx'] == 0.0
    assert abs(fb['voltage'] - 11.710) < 1e-6


def test_parse_forward_mm():
    fb = parse_feedback_frame(build_feedback_frame(200, 0, 0))
    assert fb is not None
    assert abs(fb['vx'] - 0.2) < 1e-9


def test_parser_resync():
    p = FeedbackParser()
    good = build_feedback_frame(0, 0, 0)
    frames = p.push(b'\x00' + good)
    assert len(frames) == 1


def test_integrate_forward():
    o = OdomIntegrator()
    o.update(0.2, 0.0, 0.0, 1.00)
    o.update(0.2, 0.0, 0.0, 1.05)
    assert abs(o.x - 0.01) < 1e-9
    assert abs(o.y) < 1e-12
