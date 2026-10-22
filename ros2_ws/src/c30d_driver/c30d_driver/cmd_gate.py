"""/cmd_vel_safe 超时门闩。halt = 停发非零；Mec-S 离地可停，不是工业级急停。"""

from __future__ import annotations


class CmdVelGate:
    def __init__(self, timeout_s: float) -> None:
        self.timeout_s = timeout_s
        self.last_time: float | None = None
        self.vx = 0.0
        self.vy = 0.0
        self.wz = 0.0
        self.halted = True
        self.halt_reason = 'no_command_yet'

    @staticmethod
    def _near_zero(vx: float, vy: float, wz: float) -> bool:
        return abs(vx) + abs(vy) + abs(wz) < 1e-4

    def on_cmd(self, now: float, vx: float, vy: float, wz: float) -> None:
        self.last_time = now
        self.vx, self.vy, self.wz = vx, vy, wz
        if self._near_zero(vx, vy, wz):
            self.halted = True
            self.halt_reason = 'zero_cmd'
        else:
            self.halted = False
            self.halt_reason = ''

    def tick(self, now: float) -> str:
        """Return 'idle' | 'stream' | 'halt_request'."""
        if self.last_time is None:
            self.halted = True
            self.halt_reason = 'no_command_yet'
            return 'idle'
        if now - self.last_time > self.timeout_s:
            self.halted = True
            self.halt_reason = 'cmd_vel_timeout'
            return 'halt_request'
        if self._near_zero(self.vx, self.vy, self.wz):
            self.halted = True
            self.halt_reason = 'zero_cmd'
            return 'halt_request'
        self.halted = False
        self.halt_reason = ''
        return 'stream'

    def force_halt(self, reason: str) -> None:
        self.halted = True
        self.halt_reason = reason
        self.vx = self.vy = self.wz = 0.0
        # keep last_time so tick stays in halt_request until a new on_cmd
        if self.last_time is None:
            self.last_time = 0.0
