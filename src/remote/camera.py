# -*- coding: utf-8 -*-
"""CSI preview via project rpicam MJPEG. One owner."""

from __future__ import annotations

import logging
import subprocess
import threading
import time
from pathlib import Path

from settings import robot_get

log = logging.getLogger("remote.camera")
RPICAM = Path("/opt/personal_robot/scripts/rpicam.sh")


class CameraHub:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._proc: subprocess.Popen | None = None
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._jpeg = b""
        self._seq = 0

    def latest_jpeg(self) -> bytes:
        with self._lock:
            return self._jpeg

    def latest_frame(self) -> tuple[int, bytes]:
        with self._lock:
            return self._seq, self._jpeg

    def running(self) -> bool:
        return self._proc is not None and self._proc.poll() is None

    def start(self) -> None:
        if self._proc is not None and self._proc.poll() is None:
            return
        self._stop.clear()
        w = int(robot_get("camera", "width", default=640) or 640)
        h = int(robot_get("camera", "height", default=480) or 480)
        fps = int(robot_get("camera", "fps", default=10) or 10)
        cmd = [
            str(RPICAM),
            "rpicam-vid",
            "-n",
            "-t",
            "0",
            "--codec",
            "mjpeg",
            "--width",
            str(w),
            "--height",
            str(h),
            "--framerate",
            str(fps),
            "--inline",
            "-o",
            "-",
        ]
        self._proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        self._thread = threading.Thread(target=self._loop, name="remote-cam", daemon=True)
        self._thread.start()
        log.info("camera preview %sx%s@%s", w, h, fps)

    def stop(self) -> None:
        self._stop.set()
        proc = self._proc
        if proc is not None and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                proc.kill()
        self._proc = None

    def snapshot_file(self, dest: Path) -> None:
        jpeg = self.latest_jpeg()
        if jpeg:
            dest.write_bytes(jpeg)
            return
        dest.parent.mkdir(parents=True, exist_ok=True)
        cmd = [str(RPICAM), "rpicam-jpeg", "-n", "-t", "2000", "-o", str(dest)]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=8)
        if proc.returncode != 0 or not dest.is_file() or dest.stat().st_size < 100:
            raise RuntimeError(proc.stderr.strip() or "rpicam-jpeg failed")

    def _loop(self) -> None:
        proc = self._proc
        if proc is None or proc.stdout is None:
            return
        buf = bytearray()
        try:
            while not self._stop.is_set() and proc.poll() is None:
                chunk = proc.stdout.read(4096)
                if not chunk:
                    break
                buf.extend(chunk)
                while True:
                    start = buf.find(b"\xff\xd8")
                    end = buf.find(b"\xff\xd9", start + 2) if start >= 0 else -1
                    if start < 0 or end < 0:
                        if start > 0:
                            del buf[:start]
                        break
                    jpeg = bytes(buf[start : end + 2])
                    del buf[: end + 2]
                    with self._lock:
                        self._jpeg = jpeg
                        self._seq += 1
        finally:
            log.info("camera preview stopped")
