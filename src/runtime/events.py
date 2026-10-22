from enum import Enum, auto


class Event(Enum):
    WAKE = auto()
    REMOTE_LOGIN = auto()
    EXIT_TO_IDLE = auto()
    ESTOP = auto()
    FAULT = auto()
    CLEAR_ESTOP = auto()
