# -*- coding: utf-8 -*-
"""AWAKE session: local Unix datagram trigger, idle timeout. No remote import."""

from __future__ import annotations

import logging
import os
import queue
import socket
import threading
import time
from pathlib import Path

from runtime.events import Event
from runtime.machine import Machine, Mode
from settings import load_idle_timeout_s

log = logging.getLogger("awake")

SOCK_NAME = "personal_robot_awake.sock"


def default_sock_path() -> Path:
    runtime = os.environ.get("XDG_RUNTIME_DIR", "/tmp")
    return Path(runtime) / SOCK_NAME


class AwakeSession:
    def __init__(
        self,
        machine: Machine,
        events: queue.Queue[Event],
        *,
        timeout_s: float | None = None,
        sock_path: Path | None = None,
        cues: object | None = None,
    ) -> None:
        self.machine = machine
        self.events = events
        self.timeout_s = load_idle_timeout_s() if timeout_s is None else timeout_s
        self.cues = cues
        self.sock_path = Path(sock_path) if sock_path else default_sock_path()
        self.last_active = 0.0
        self._sock: socket.socket | None = None
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self.sock_path.exists():
            try:
                self.sock_path.unlink()
            except OSError as exc:
                log.warning("unlink %s: %s", self.sock_path, exc)
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        sock.bind(str(self.sock_path))
        os.chmod(self.sock_path, 0o600)
        sock.settimeout(0.3)
        self._sock = sock
        self._stop.clear()
        self._thread = threading.Thread(target=self._recv_loop, name="awake-sock", daemon=True)
        self._thread.start()
        log.info("awake socket %s timeout=%.1fs", self.sock_path, self.timeout_s)

    def close(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=1.5)
            self._thread = None
        if self._sock is not None:
            try:
                self._sock.close()
            except OSError:
                pass
            self._sock = None
        try:
            self.sock_path.unlink(missing_ok=True)
        except OSError:
            pass

    def note_entered(self, now: float | None = None) -> None:
        self.last_active = time.monotonic() if now is None else now

    def handle_text(self, raw: str) -> None:
        cmd = raw.strip().lower()
        if cmd == "wake":
            if self.machine.estop or self.machine.mode in (Mode.FAULT, Mode.REMOTE):
                log.info("wake ignored mode=%s estop=%s", self.machine.mode, self.machine.estop)
                denied = getattr(self.cues, "denied", None)
                if callable(denied):
                    denied()
                return
            self.note_entered()
            self.events.put(Event.WAKE)
            return
        if cmd == "idle":
            if self.machine.mode == Mode.AWAKE:
                self.events.put(Event.EXIT_TO_IDLE)
            return
        log.info("awake ignore cmd=%r", cmd[:32])

    def check_timeout(self, now: float | None = None) -> None:
        t = time.monotonic() if now is None else now
        if self.machine.mode != Mode.AWAKE:
            return
        if self.last_active <= 0:
            self.last_active = t
            return
        if t - self.last_active <= self.timeout_s:
            return
        log.warning("awake idle timeout")
        self.events.put(Event.EXIT_TO_IDLE)
        self.last_active = 0.0

    def _recv_loop(self) -> None:
        sock = self._sock
        if sock is None:
            return
        while not self._stop.is_set():
            try:
                data, _addr = sock.recvfrom(64)
            except socket.timeout:
                continue
            except OSError:
                if self._stop.is_set():
                    return
                log.warning("awake socket recv failed")
                return
            try:
                text = data.decode("utf-8", errors="replace")
            except Exception:
                continue
            self.handle_text(text)
