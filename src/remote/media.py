# -*- coding: utf-8 -*-
"""REMOTE photo / video / audio files. No AI."""

from __future__ import annotations

import logging
import subprocess
import threading
import time
from datetime import datetime
from pathlib import Path

from settings import audio_device, robot_get

from .camera import CameraHub

log = logging.getLogger("remote.media")
ROOT = Path("/opt/personal_robot/data/media/remote")


def _stamp(prefix: str, ext: str) -> str:
    return f"{prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{ext}"


class MediaSession:
    def __init__(self) -> None:
        self.camera = CameraHub()
        self._lock = threading.Lock()
        self._video: subprocess.Popen | None = None
        self._audio: subprocess.Popen | None = None
        self._video_path: Path | None = None
        self._audio_path: Path | None = None
        self._video_timer: threading.Timer | None = None
        self._audio_timer: threading.Timer | None = None
        self._video_writer: threading.Thread | None = None
        self._video_stop = threading.Event()

    def dirs(self) -> dict[str, Path]:
        photos = Path(str(robot_get("media", "photos", default=str(ROOT / "photos")) or ROOT / "photos"))
        videos = Path(str(robot_get("media", "videos", default=str(ROOT / "videos")) or ROOT / "videos"))
        recs = Path(
            str(robot_get("media", "recordings", default=str(ROOT / "recordings")) or ROOT / "recordings")
        )
        for path in (photos, videos, recs):
            path.mkdir(parents=True, exist_ok=True)
        return {"photos": photos, "videos": videos, "recordings": recs}

    def video_max_s(self) -> float:
        return max(1.0, min(600.0, float(robot_get("media", "video_max_s", default=60) or 60)))

    def audio_max_s(self) -> float:
        return max(1.0, min(600.0, float(robot_get("media", "audio_max_s", default=60) or 60)))

    def status(self) -> dict:
        return {
            "video": self._video_writer is not None and self._video_writer.is_alive(),
            "audio": self._audio is not None and self._audio.poll() is None,
            "video_max_s": self.video_max_s(),
            "audio_max_s": self.audio_max_s(),
            "preview": self.camera.latest_jpeg() != b"",
        }

    def start_preview(self) -> None:
        self.dirs()
        try:
            self.camera.start()
        except Exception as exc:
            log.warning("camera preview failed: %s", exc)

    def stop_all(self) -> None:
        self.stop_video()
        self.stop_audio()
        self.camera.stop()

    def photo(self) -> Path:
        dest = self.dirs()["photos"] / _stamp("photo", "jpg")
        self.camera.snapshot_file(dest)
        log.info("photo %s", dest)
        return dest

    def start_video(self) -> Path:
        with self._lock:
            if self._video_writer is not None and self._video_writer.is_alive():
                raise RuntimeError("video already recording")
            dest = self.dirs()["videos"] / _stamp("video", "mjpeg")
            self._video_path = dest
            self._video_stop.clear()
            dest.write_bytes(b"")
            self._video_writer = threading.Thread(
                target=self._video_loop, args=(dest,), name="remote-video", daemon=True
            )
            self._video_writer.start()
            self._video_timer = threading.Timer(self.video_max_s(), self.stop_video)
            self._video_timer.daemon = True
            self._video_timer.start()
        log.info("video start %s max_s=%s", dest, self.video_max_s())
        return dest

    def _video_loop(self, dest: Path) -> None:
        last = b""
        with dest.open("ab") as out:
            while not self._video_stop.is_set():
                jpeg = self.camera.latest_jpeg()
                if jpeg and jpeg != last:
                    out.write(jpeg)
                    last = jpeg
                time.sleep(0.08)

    def stop_video(self) -> Path | None:
        with self._lock:
            self._video_stop.set()
            if self._video_timer is not None:
                self._video_timer.cancel()
                self._video_timer = None
            th = self._video_writer
            self._video_writer = None
            path = self._video_path
            self._video_path = None
        if th is not None:
            th.join(timeout=2)
        if path:
            log.info("video stop %s", path)
        return path

    def start_audio(self) -> Path:
        with self._lock:
            if self._audio is not None and self._audio.poll() is None:
                raise RuntimeError("audio already recording")
            dest = self.dirs()["recordings"] / _stamp("audio", "wav")
            self._audio_path = dest
            cap = audio_device("capture")
            self._audio = subprocess.Popen(
                ["arecord", "-D", cap, "-f", "S16_LE", "-r", "16000", "-c", "1", "-t", "wav", str(dest)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            self._audio_timer = threading.Timer(self.audio_max_s(), self.stop_audio)
            self._audio_timer.daemon = True
            self._audio_timer.start()
        log.info("audio start %s max_s=%s", dest, self.audio_max_s())
        return dest

    def stop_audio(self) -> Path | None:
        with self._lock:
            if self._audio_timer is not None:
                self._audio_timer.cancel()
                self._audio_timer = None
            proc = self._audio
            self._audio = None
            path = self._audio_path
            self._audio_path = None
        if proc is not None and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                proc.kill()
        if path:
            log.info("audio stop %s", path)
        return path
