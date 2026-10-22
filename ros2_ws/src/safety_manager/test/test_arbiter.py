from safety_manager.arbiter import (
    AWAKE,
    FAULT,
    IDLE,
    NONE,
    REMOTE,
    SRC_AWAKE,
    SRC_REMOTE,
    SafetyArbiter,
)


def test_idle_no_motion():
    a = SafetyArbiter()
    a.on_twist(SRC_REMOTE, 0.2, 0.0, 0.0, 1.0)
    kind, vx, *_ = a.tick(1.05)
    assert a.mode == IDLE
    assert a.permit == NONE
    assert kind == 'zero'
    assert vx == 0.0


def test_remote_streams_awake_ignored():
    a = SafetyArbiter()
    assert a.request_mode(REMOTE) == ''
    a.on_twist(SRC_AWAKE, 0.5, 0.0, 0.0, 1.0)
    kind, vx, *_ = a.tick(1.05)
    assert kind == 'zero'
    a.on_twist(SRC_REMOTE, 0.2, 0.0, 0.0, 1.1)
    kind, vx, *_ = a.tick(1.15)
    assert kind == 'stream'
    assert vx == 0.2


def test_awake_remote_must_via_idle():
    a = SafetyArbiter()
    assert a.request_mode(AWAKE) == ''
    assert a.request_mode(REMOTE) == 'must_via_idle'
    assert a.mode == AWAKE
    assert a.request_mode(IDLE) == ''
    assert a.request_mode(REMOTE) == ''
    assert a.mode == REMOTE
    assert a.permit == SRC_REMOTE


def test_switch_revokes_old_twist():
    a = SafetyArbiter()
    a.request_mode(REMOTE)
    a.on_twist(SRC_REMOTE, 0.3, 0.0, 0.0, 1.0)
    assert a.tick(1.05)[1] == 0.3
    a.request_mode(IDLE)
    kind, vx, *_ = a.tick(1.1)
    assert kind == 'zero'
    assert vx == 0.0
    assert a.permit == NONE


def test_timeout_zero_not_estop():
    a = SafetyArbiter(0.30)
    a.request_mode(REMOTE)
    a.on_twist(SRC_REMOTE, 0.2, 0.0, 0.0, 1.0)
    assert a.tick(1.1)[0] == 'stream'
    kind, vx, *_ = a.tick(1.4)
    assert kind == 'zero'
    assert vx == 0.0
    assert a.estop is False
    a.on_twist(SRC_REMOTE, 0.2, 0.0, 0.0, 1.5)
    assert a.tick(1.55)[0] == 'stream'


def test_estop_latch_manual_clear():
    a = SafetyArbiter()
    a.request_mode(REMOTE)
    a.on_twist(SRC_REMOTE, 0.2, 0.0, 0.0, 1.0)
    a.set_estop(True)
    assert a.estop is True
    assert a.mode == IDLE
    assert a.permit == NONE
    assert a.request_mode(REMOTE) == 'estop_latched'
    a.on_twist(SRC_REMOTE, 0.2, 0.0, 0.0, 1.2)
    assert a.tick(1.25)[1] == 0.0
    a.set_estop(False)
    assert a.estop is False
    assert a.mode == IDLE
    assert a.request_mode(REMOTE) == ''
    a.on_twist(SRC_REMOTE, 0.2, 0.0, 0.0, 2.0)
    assert a.tick(2.05)[0] == 'stream'


def test_serial_disconnect_fault():
    a = SafetyArbiter()
    a.request_mode(REMOTE)
    a.on_serial_connected(True)
    a.on_serial_connected(False)
    assert a.mode == FAULT
    assert a.fault == 'serial_disconnect'
    assert a.request_mode(REMOTE) == 'fault_locked'
    assert a.request_mode(IDLE) == ''
    assert a.mode == IDLE
    assert a.fault == ''
