from command_bus.validator import AWAKE, IDLE, REMOTE, CommandBus


def test_ping_in_idle():
    b = CommandBus()
    d = b.dispatch(command_id='c1', source='system', skill_id='ping')
    assert d.accepted
    assert d.executed == 'ping'


def test_duplicate_rejected():
    b = CommandBus()
    b.dispatch(command_id='c1', source='system', skill_id='ping')
    d = b.dispatch(command_id='c1', source='system', skill_id='ping')
    assert not d.accepted
    assert d.reason == 'duplicate_command_id'


def test_dance_blocked_by_default():
    b = CommandBus()
    b.set_mode(REMOTE)
    d = b.dispatch(command_id='c2', source='remote', skill_id='dance_1')
    assert not d.accepted
    assert d.reason == 'motion_disabled'


def test_dance_needs_matching_mode_when_enabled():
    b = CommandBus(motion_enabled=True)
    d = b.dispatch(command_id='c3', source='remote', skill_id='dance_1')
    assert d.reason == 'no_motion_permit'
    b.set_mode(REMOTE)
    d = b.dispatch(command_id='c4', source='awake', skill_id='dance_1')
    assert d.reason == 'source_mode_mismatch'
    d = b.dispatch(command_id='c5', source='remote', skill_id='dance_1')
    assert d.accepted
    assert d.executed == 'queued'


def test_estop_blocks():
    b = CommandBus()
    b.set_estop(True)
    d = b.dispatch(command_id='c6', source='system', skill_id='ping')
    assert d.reason == 'estop_latched'


def test_awake_remote_sources():
    b = CommandBus()
    assert b.mode == IDLE


def test_drive_blocked_by_default():
    b = CommandBus()
    b.set_mode(REMOTE)
    d = b.dispatch(command_id='d1', source='remote', skill_id='drive', vx=0.15)
    assert not d.accepted
    assert d.reason == 'motion_disabled'


def test_drive_streams_when_enabled():
    b = CommandBus(motion_enabled=True)
    b.set_mode(REMOTE)
    d = b.dispatch(command_id='d2', source='remote', skill_id='drive', vx=0.15, vy=0, wz=0)
    assert d.accepted
    assert d.executed == 'drive'
    assert b.vx == 0.15
    d = b.dispatch(command_id='d3', source='remote', skill_id='drive', vx=0, vy=0, wz=0)
    assert d.accepted
    assert b.vx == 0.0


def test_drive_needs_remote_source():
    b = CommandBus(motion_enabled=True)
    b.set_mode(REMOTE)
    d = b.dispatch(command_id='d4', source='awake', skill_id='drive', vx=0.1)
    assert d.reason == 'source_mode_mismatch'
