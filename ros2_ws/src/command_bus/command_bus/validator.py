"""Command bus core. No ROS, no serial, no Twist."""

from __future__ import annotations

from dataclasses import dataclass

IDLE, AWAKE, REMOTE, FAULT = 'IDLE', 'AWAKE', 'REMOTE', 'FAULT'
SRC_AWAKE, SRC_REMOTE, SRC_SYSTEM = 'awake', 'remote', 'system'

SKILL_PING = 'ping'
SKILL_DRIVE = 'drive'
SKILL_DANCE_1 = 'dance_1'
SKILL_DANCE_2 = 'dance_2'

NON_MOTION = {SKILL_PING}
MOTION = {SKILL_DRIVE, SKILL_DANCE_1, SKILL_DANCE_2}
ALLOW = NON_MOTION | MOTION
_SEEN_CAP = 256


@dataclass(frozen=True)
class BusDecision:
    accepted: bool
    reason: str
    executed: str = ''


class CommandBus:
    def __init__(self, motion_enabled: bool = False) -> None:
        self.motion_enabled = motion_enabled
        self.mode = IDLE
        self.estop = False
        self.vx = 0.0
        self.vy = 0.0
        self.wz = 0.0
        self._seen: dict[str, str] = {}
        self._active: str | None = None

    def set_mode(self, mode: str) -> None:
        self.mode = mode.strip().upper() or IDLE

    def set_estop(self, latched: bool) -> None:
        self.estop = bool(latched)
        if self.estop:
            self._active = None
            self.zero_drive()

    def zero_drive(self) -> None:
        self.vx = self.vy = self.wz = 0.0

    def _remember(self, cid: str, status: str) -> None:
        self._seen[cid] = status
        extra = len(self._seen) - _SEEN_CAP
        if extra > 0:
            for key in list(self._seen.keys())[:extra]:
                del self._seen[key]

    def cancel(self, command_id: str) -> BusDecision:
        cid = command_id.strip()
        if not cid:
            return BusDecision(False, 'bad_command_id')
        if self._active == cid:
            self._active = None
            self.zero_drive()
            self._remember(cid, 'cancelled')
            return BusDecision(True, '', executed='cancelled')
        if cid in self._seen:
            return BusDecision(True, '', executed='already_done')
        return BusDecision(False, 'unknown_command_id')

    def dispatch(
        self,
        *,
        command_id: str,
        source: str,
        skill_id: str,
        vx: float = 0.0,
        vy: float = 0.0,
        wz: float = 0.0,
    ) -> BusDecision:
        cid = command_id.strip()
        src = source.strip().lower()
        skill = skill_id.strip()
        if not cid:
            return BusDecision(False, 'bad_command_id')
        if cid in self._seen:
            return BusDecision(False, 'duplicate_command_id')
        if src not in (SRC_AWAKE, SRC_REMOTE, SRC_SYSTEM):
            return BusDecision(False, 'bad_source')
        if skill not in ALLOW:
            return BusDecision(False, 'unknown_skill')
        if self.estop:
            return BusDecision(False, 'estop_latched')
        if self.mode == FAULT:
            return BusDecision(False, 'fault_locked')
        if skill in MOTION:
            if not self.motion_enabled:
                return BusDecision(False, 'motion_disabled')
            if self.mode not in (AWAKE, REMOTE):
                return BusDecision(False, 'no_motion_permit')
            if src == SRC_AWAKE and self.mode != AWAKE:
                return BusDecision(False, 'source_mode_mismatch')
            if src == SRC_REMOTE and self.mode != REMOTE:
                return BusDecision(False, 'source_mode_mismatch')
            if src == SRC_SYSTEM:
                return BusDecision(False, 'system_no_motion')
        self._remember(cid, 'accepted')
        if skill == SKILL_PING:
            self._active = None
            return BusDecision(True, '', executed='ping')
        if skill == SKILL_DRIVE:
            self.vx, self.vy, self.wz = float(vx), float(vy), float(wz)
            self._active = None
            return BusDecision(True, '', executed='drive')
        self._active = cid
        return BusDecision(True, '', executed='queued')
