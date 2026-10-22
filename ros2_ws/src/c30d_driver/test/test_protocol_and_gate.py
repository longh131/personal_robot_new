from c30d_driver.protocol import build_velocity_frame, twist_to_counts
from c30d_driver.cmd_gate import CmdVelGate


def test_forward_frame():
    assert build_velocity_frame(60, 0, 0).hex() == '7b0000003c00000000477d'
    assert len(build_velocity_frame(0, 0, 0)) == 11


def test_scale_and_limit():
    vx, vy, wz = twist_to_counts(0.2, 0.0, 0.0, 300.0, 120)
    assert vx == 60
    vx, _, _ = twist_to_counts(2.0, 0.0, 0.0, 300.0, 120)
    assert vx == 120


def test_gate_timeout_and_shutdown():
    g = CmdVelGate(0.30)
    assert g.tick(0.0) == 'idle'
    g.on_cmd(1.0, 0.2, 0.0, 0.0)
    assert g.tick(1.1) == 'stream'
    assert g.tick(1.5) == 'halt_request'
    assert g.halted
    assert g.halt_reason == 'cmd_vel_timeout'
    g.on_cmd(2.0, 0.0, 0.2, 0.0)
    assert g.tick(2.05) == 'stream'
    g.on_cmd(2.1, 0.0, 0.0, 0.0)
    assert g.tick(2.15) == 'halt_request'
    assert g.halt_reason == 'zero_cmd'
    g.force_halt('driver_shutdown')
    assert g.halted
    assert g.tick(2.5) == 'halt_request'
