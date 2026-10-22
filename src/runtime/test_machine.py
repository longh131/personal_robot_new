import queue
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from awake.session import AwakeSession
from runtime.events import Event
from runtime.machine import Machine, Mode


def test_idle_exclusive_entries() -> None:
    m = Machine()
    assert m.mode == Mode.IDLE
    m.apply(Event.WAKE)
    assert m.mode == Mode.AWAKE
    m.apply(Event.REMOTE_LOGIN)
    assert m.mode == Mode.AWAKE
    m.apply(Event.EXIT_TO_IDLE)
    assert m.mode == Mode.IDLE
    m.apply(Event.REMOTE_LOGIN)
    assert m.mode == Mode.REMOTE
    m.apply(Event.WAKE)
    assert m.mode == Mode.REMOTE


def test_estop_is_not_a_mode() -> None:
    m = Machine()
    m.apply(Event.WAKE)
    m.apply(Event.ESTOP)
    assert m.estop is True
    assert m.mode == Mode.AWAKE


def test_awake_timeout_and_remote_blocks_wake() -> None:
    events: queue.Queue[Event] = queue.Queue()
    m = Machine()
    s = AwakeSession(m, events, timeout_s=5.0)
    s.handle_text("wake")
    assert events.get_nowait() is Event.WAKE
    m.apply(Event.WAKE)
    s.last_active = 100.0
    s.check_timeout(now=103.0)
    assert events.empty()
    s.check_timeout(now=106.0)
    assert events.get_nowait() is Event.EXIT_TO_IDLE
    m.apply(Event.EXIT_TO_IDLE)
    m.apply(Event.REMOTE_LOGIN)
    hits: list[str] = []

    class _Cues:
        def denied(self) -> None:
            hits.append("denied")

    s.cues = _Cues()
    s.handle_text("wake")
    assert events.empty()
    assert hits == ["denied"]


if __name__ == "__main__":
    test_idle_exclusive_entries()
    test_estop_is_not_a_mode()
    test_awake_timeout_and_remote_blocks_wake()
    print("ok")
