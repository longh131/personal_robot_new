"""模式互斥与急停锁存。无 ROS、无串口。"""

from __future__ import annotations

IDLE, AWAKE, REMOTE, FAULT = 'IDLE', 'AWAKE', 'REMOTE', 'FAULT'
NONE, SRC_AWAKE, SRC_REMOTE = 'none', 'awake', 'remote'


class SafetyArbiter:
    def __init__(self, cmd_timeout_s: float = 0.30) -> None:
        self.cmd_timeout_s = cmd_timeout_s
        self.mode = IDLE
        self.permit = NONE
        self.estop = False
        self.fault = ''
        self.vx = 0.0
        self.vy = 0.0
        self.wz = 0.0
        self.last_cmd_time: float | None = None
        self._saw_connected = False

    def _revoke(self) -> None:
        self.permit = NONE
        self.vx = self.vy = self.wz = 0.0
        self.last_cmd_time = None

    def request_mode(self, target: str) -> str:
        target = target.strip().upper()
        if target not in (IDLE, AWAKE, REMOTE):
            return 'bad_mode'
        if self.estop and target in (AWAKE, REMOTE):
            return 'estop_latched'
        if self.mode == FAULT:
            if target != IDLE:
                return 'fault_locked'
            if self.estop:
                return 'estop_latched'
            self._revoke()
            self.mode = IDLE
            self.fault = ''
            return ''
        if target == IDLE:
            self._revoke()
            self.mode = IDLE
            return ''
        if self.mode in (AWAKE, REMOTE) and target != self.mode and target != IDLE:
            return 'must_via_idle'
        if self.mode != IDLE and target != self.mode:
            return 'must_via_idle'
        if target == AWAKE:
            self._revoke()
            self.mode = AWAKE
            self.permit = SRC_AWAKE
            return ''
        self._revoke()
        self.mode = REMOTE
        self.permit = SRC_REMOTE
        return ''

    def set_estop(self, latched: bool) -> None:
        if latched:
            self.estop = True
            self._revoke()
            if self.mode != FAULT:
                self.mode = IDLE
            return
        self.estop = False

    def on_serial_connected(self, connected: bool) -> None:
        if connected:
            self._saw_connected = True
            return
        if self._saw_connected:
            self._revoke()
            self.mode = FAULT
            self.fault = 'serial_disconnect'

    def on_twist(self, source: str, vx: float, vy: float, wz: float, now: float) -> None:
        if self.estop or self.mode in (IDLE, FAULT):
            return
        if source != self.permit:
            return
        self.vx, self.vy, self.wz = vx, vy, wz
        self.last_cmd_time = now

    def tick(self, now: float) -> tuple[str, float, float, float]:
        """Return output: 'none'|'zero'|'stream' and twist."""
        if self.estop or self.mode in (IDLE, FAULT) or self.permit == NONE:
            return 'zero', 0.0, 0.0, 0.0
        if self.last_cmd_time is None:
            return 'zero', 0.0, 0.0, 0.0
        if now - self.last_cmd_time > self.cmd_timeout_s:
            self.vx = self.vy = self.wz = 0.0
            return 'zero', 0.0, 0.0, 0.0
        return 'stream', self.vx, self.vy, self.wz
