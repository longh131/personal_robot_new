# -*- coding: utf-8 -*-
"""IDLE motion sentry: clip_s video + wav. No chassis, no gimbal."""

from __future__ import annotations

import json
import logging
import subprocess
import time
from datetime import datetime
from io import BytesIO
from pathlib import Path

from PIL import Image

from runtime.machine import Mode
from settings import audio_device, robot_get

log = logging.getLogger("sentry")
ROOT = Path("/opt/personal_robot/data/media/remote")
GRAY_SIZE = (80, 60)


def gray_small(jpeg: bytes) -> bytes | None:
    if not jpeg:
        return None
    try:
        im = Image.open(BytesIO(jpeg)).convert("L").resize(GRAY_SIZE)
    except Exception:
        return None
    return im.tobytes()


def mean_abs_diff(a: bytes | None, b: bytes | None) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    total = 0
    for x, y in zip(a, b, strict=True):
        total += abs(x - y)
    return total / len(a)


def pick_main(shots: list[dict]) -> dict | None:
    if not shots:
        return None
    return max(shots, key=lambda s: float(s.get("score") or 0))


def events_in_hour(stamps: list[float], now: float) -> int:
    cutoff = now - 3600.0
    return sum(1 for t in stamps if t >= cutoff)


class Sentry:
    def __init__(self, machine, camera, cues=None, mic=None) -> None:
        self.machine = machine
        self.camera = camera
        self.cues = cues
        self.mic = mic
        self._phase = "watch"
        self._prev: bytes | None = None
        self._last_seq = -1
        self._t0 = 0.0
        self._stamp = ""
        self._event_times: list[float] = []
        self._cooldown_until = 0.0
        self._warmup_until = 0.0
        self._cam_mine = False
        self._video_path: Path | None = None
        self._audio_path: Path | None = None
        self._poster_path: Path | None = None
        self._video_fh = None
        self._arecord: subprocess.Popen | None = None
        self._held_mic = False

    def _cfg(self) -> dict:
        clip = float(robot_get("sentry", "clip_s", default=10) or 10)
        return {
            "enabled": bool(robot_get("sentry", "enabled", default=True)),
            "threshold": float(robot_get("sentry", "threshold", default=10) or 10),
            "cooldown_s": float(robot_get("sentry", "cooldown_s", default=8) or 8),
            "max_events_per_hour": int(robot_get("sentry", "max_events_per_hour", default=12) or 12),
            "warmup_s": float(robot_get("sentry", "warmup_s", default=2) or 2),
            "clip_s": max(2.0, min(60.0, clip)),
            "buzzer": bool(robot_get("sentry", "buzzer", default=False)),
        }

    def _dir(self) -> Path:
        path = Path(str(robot_get("media", "sentry", default=str(ROOT / "sentry")) or ROOT / "sentry"))
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _allowed(self) -> bool:
        return (
            self._cfg()["enabled"]
            and self.machine.mode == Mode.IDLE
            and not self.machine.estop
        )

    def tick(self) -> None:
        if not self._allowed():
            release = self.machine.mode != Mode.REMOTE
            self.pause(release_camera=release, resume_mic=release)
            return
        self._ensure_camera()
        now = time.monotonic()
        if now < self._warmup_until:
            self._sample(store_prev=True)
            return
        if self._phase == "cooldown":
            if now >= self._cooldown_until:
                self._phase = "watch"
                self._prev = None
            else:
                self._sample(store_prev=True)
            return
        if self._phase == "watch":
            self._watch(now)
            return
        if self._phase == "clip":
            self._clip(now)

    def pause(self, *, release_camera: bool, resume_mic: bool = True) -> None:
        if self._phase == "clip":
            self._finish(time.monotonic(), partial=True, resume_mic=resume_mic)
        else:
            self._stop_arecord()
            self._close_video()
            if resume_mic:
                self._resume_mic()
        self._phase = "watch"
        self._prev = None
        if release_camera and self._cam_mine:
            try:
                self.camera.stop()
            except Exception as exc:
                log.warning("sentry camera stop: %s", exc)
            self._cam_mine = False

    def close(self) -> None:
        self.pause(release_camera=True, resume_mic=True)

    def _ensure_camera(self) -> None:
        if self.camera.running():
            return
        self.camera.start()
        self._cam_mine = True
        self._warmup_until = time.monotonic() + self._cfg()["warmup_s"]
        self._prev = None
        self._last_seq = -1
        log.info("sentry camera on")

    def _sample(self, *, store_prev: bool) -> tuple[bytes, bytes, float] | None:
        seq, jpeg = self.camera.latest_frame()
        if seq == self._last_seq or not jpeg:
            return None
        self._last_seq = seq
        small = gray_small(jpeg)
        if small is None:
            return None
        score = mean_abs_diff(self._prev, small)
        if store_prev:
            self._prev = small
        return jpeg, small, score

    def _watch(self, now: float) -> None:
        got = self._sample(store_prev=False)
        if got is None:
            return
        jpeg, small, score = got
        cfg = self._cfg()
        if self._prev is None:
            self._prev = small
            return
        if score < cfg["threshold"]:
            self._prev = small
            return
        if events_in_hour(self._event_times, now) >= cfg["max_events_per_hour"]:
            log.warning("sentry hour cap, skip")
            self._prev = small
            return
        self._prev = small
        self._t0 = now
        self._stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._start_clip(jpeg)
        self._phase = "clip"
        log.info("sentry clip start score=%.1f s=%s", score, cfg["clip_s"])
        if cfg["buzzer"] and self.cues is not None:
            try:
                self.cues.denied()
            except Exception:
                pass

    def _start_clip(self, jpeg: bytes) -> None:
        folder = self._dir()
        self._poster_path = folder / f"{self._stamp}.jpg"
        self._video_path = folder / f"{self._stamp}.mjpeg"
        self._audio_path = folder / f"{self._stamp}.wav"
        if jpeg:
            self._poster_path.write_bytes(jpeg)
        self._close_video()
        self._video_fh = self._video_path.open("wb")
        if jpeg:
            self._video_fh.write(jpeg)
        self._hold_mic()
        self._start_arecord()

    def _hold_mic(self) -> None:
        if self.mic is None or self._held_mic:
            return
        self.mic.set_paused(True)
        self._held_mic = True

    def _resume_mic(self) -> None:
        if not self._held_mic or self.mic is None:
            self._held_mic = False
            return
        if self.machine.mode == Mode.REMOTE:
            self._held_mic = False
            return
        self.mic.set_paused(False)
        self._held_mic = False

    def _start_arecord(self) -> None:
        self._stop_arecord()
        dest = self._audio_path
        if dest is None:
            return
        clip = int(round(self._cfg()["clip_s"]))
        cmd = [
            "arecord",
            "-D",
            audio_device("capture"),
            "-f",
            "S16_LE",
            "-r",
            "16000",
            "-c",
            "1",
            "-d",
            str(clip),
            "-t",
            "wav",
            "-q",
            str(dest),
        ]
        try:
            self._arecord = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except OSError as exc:
            log.warning("sentry arecord: %s", exc)
            self._arecord = None

    def _stop_arecord(self) -> None:
        proc = self._arecord
        self._arecord = None
        if proc is None or proc.poll() is not None:
            return
        proc.terminate()
        try:
            proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            proc.kill()

    def _close_video(self) -> None:
        fh = self._video_fh
        self._video_fh = None
        if fh is not None:
            try:
                fh.close()
            except OSError:
                pass

    def _clip(self, now: float) -> None:
        got = self._sample(store_prev=True)
        if got and self._video_fh is not None:
            self._video_fh.write(got[0])
        if now - self._t0 >= self._cfg()["clip_s"]:
            self._finish(now, partial=False, resume_mic=True)

    def _finish(self, now: float, *, partial: bool, resume_mic: bool) -> None:
        self._close_video()
        self._stop_arecord()
        if resume_mic:
            self._resume_mic()
        rec = {
            "ts": datetime.now().isoformat(timespec="seconds"),
            "reason": "motion",
            "partial": partial,
            "poster": None if self._poster_path is None else str(self._poster_path),
            "video": None if self._video_path is None else str(self._video_path),
            "audio": None if self._audio_path is None else str(self._audio_path),
            "notify": {"status": "pending", "channel": None},
        }
        with (self._dir() / "events.jsonl").open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        self._event_times.append(now)
        self._event_times = [t for t in self._event_times if t >= now - 3600.0]
        self._cooldown_until = now + self._cfg()["cooldown_s"]
        self._phase = "cooldown"
        self._video_path = None
        self._audio_path = None
        self._poster_path = None
        log.info("sentry clip done partial=%s", partial)
