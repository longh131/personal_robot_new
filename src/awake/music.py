# -*- coding: utf-8 -*-
"""AWAKE local mp3 player. Sequential default. No remote import."""

from __future__ import annotations

import logging
import random
import subprocess
import threading
from pathlib import Path

from settings import robot_get

log = logging.getLogger("awake.music")


def music_dir() -> Path:
    raw = robot_get("media", "awake_music", default="/opt/personal_robot/data/media/awake/music")
    path = Path(str(raw or "/opt/personal_robot/data/media/awake/music"))
    path.mkdir(parents=True, exist_ok=True)
    return path


def list_mp3() -> list[Path]:
    return sorted(p for p in music_dir().glob("*.mp3") if p.is_file())


def find_named(query: str) -> Path | None:
    q = (query or "").strip().lower()
    if not q:
        return None
    files = list_mp3()
    for path in files:
        stem = path.stem.lower()
        if q in stem or stem in q:
            return path
    return None


class Player:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._proc: subprocess.Popen | None = None
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._queue: list[Path] = []
        self._index = 0
        self._random = False
        self._listen_paused = False
        self._resume_path: Path | None = None

    def play(self, *, randomize: bool = False, named: str = "") -> str:
        files = list_mp3()
        if not files:
            return "音乐目录里还没有 mp3"
        pick: list[Path]
        if named:
            hit = find_named(named)
            if hit is None:
                return f"没找到叫{named}的歌"
            pick = [hit]
            randomize = False
        elif randomize:
            pick = files[:]
            random.shuffle(pick)
        else:
            pick = files
        self._stop.set()
        self._kill()
        self._stop = threading.Event()
        with self._lock:
            self._queue = pick
            self._index = 0
            self._random = randomize
        self._thread = threading.Thread(target=self._run, name="awake-music", daemon=True)
        self._thread.start()
        if named:
            return f"播放{pick[0].stem}"
        if randomize:
            return "随机播放音乐"
        return "按顺序播放音乐"

    def stop(self) -> str:
        self._listen_paused = False
        self._resume_path = None
        self._stop.set()
        self._kill()
        return "音乐停了"

    def pause_for_listen(self) -> None:
        """Mute playback while ASR listens (loud music kills recognition)."""
        with self._lock:
            proc = self._proc
            if proc is None or proc.poll() is not None:
                return
            # rewind one track so resume can replay current item
            if self._index > 0:
                self._index -= 1
                self._resume_path = self._queue[self._index] if self._queue else None
            self._listen_paused = True
        self._kill()
        log.info("music paused for listen")

    def resume_after_listen(self) -> None:
        with self._lock:
            if not self._listen_paused:
                return
            self._listen_paused = False
            if self._stop.is_set() or not self._queue:
                self._resume_path = None
                return
            alive = self._thread is not None and self._thread.is_alive()
        if alive:
            return
        self._thread = threading.Thread(target=self._run, name="awake-music", daemon=True)
        self._thread.start()
        log.info("music resume after listen")
        self._resume_path = None

    def _kill(self) -> None:
        proc = self._proc
        self._proc = None
        if proc is None or proc.poll() is not None:
            return
        proc.terminate()
        try:
            proc.wait(timeout=1.5)
        except subprocess.TimeoutExpired:
            proc.kill()

    def _run(self) -> None:
        while not self._stop.is_set():
            with self._lock:
                if self._index >= len(self._queue):
                    return
                path = self._queue[self._index]
                self._index += 1
            log.info("play %s", path.name)
            try:
                self._proc = subprocess.Popen(
                    ["gst-play-1.0", "--no-interactive", str(path)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            except OSError as exc:
                log.warning("gst-play: %s", exc)
                return
            while not self._stop.is_set():
                if self._proc.poll() is not None:
                    break
                self._stop.wait(0.2)
            self._kill()


_player = Player()


def play(*, randomize: bool = False, named: str = "") -> str:
    return _player.play(randomize=randomize, named=named)


def stop() -> str:
    return _player.stop()


def pause_for_listen() -> None:
    _player.pause_for_listen()


def resume_after_listen() -> None:
    _player.resume_after_listen()
