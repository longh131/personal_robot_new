# -*- coding: utf-8 -*-
"""Mic wake: arecord Y1076 + Sherpa-ONNX KWS. No remote import. No motion."""

from __future__ import annotations

import logging
import os
import subprocess
import threading
import time
from pathlib import Path

import numpy as np

from awake.session import AwakeSession

log = logging.getLogger("awake.mic")

DEVICE = os.environ.get("PERSONAL_ROBOT_MIC", "plughw:Y1076,0")
RATE = 16000
CHUNK = 1600
COOLDOWN_S = 3.0
MODEL_DIR = Path("/opt/personal_robot/data/models/wake")
ENCODER = "encoder-epoch-12-avg-2-chunk-16-left-64.int8.onnx"
DECODER = "decoder-epoch-12-avg-2-chunk-16-left-64.onnx"
JOINER = "joiner-epoch-12-avg-2-chunk-16-left-64.int8.onnx"
NEEDED = (ENCODER, DECODER, JOINER, "tokens.txt", "keywords.txt")


class MicWake:
    def __init__(self, session: AwakeSession, *, device: str = DEVICE) -> None:
        self.session = session
        self.device = device
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._proc: subprocess.Popen[bytes] | None = None
        self._last = 0.0
        self._paused = False
        self._kws = None
        self._stream = None

    def set_paused(self, on: bool) -> None:
        self._paused = bool(on)
        if on:
            self._stop_capture()

    def _stop_capture(self) -> None:
        proc = self._proc
        if proc is None or proc.poll() is not None:
            return
        proc.terminate()
        try:
            proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            proc.kill()
        self._proc = None

    def start(self) -> None:
        import sherpa_onnx

        from awake.keywords import write_keywords

        missing = [n for n in NEEDED if n != "keywords.txt" and not (MODEL_DIR / n).is_file()]
        if missing:
            raise FileNotFoundError(f"wake models missing in {MODEL_DIR}: {missing}")
        keys = write_keywords(MODEL_DIR / "keywords.txt")
        self._kws = sherpa_onnx.KeywordSpotter(
            tokens=str(MODEL_DIR / "tokens.txt"),
            encoder=str(MODEL_DIR / ENCODER),
            decoder=str(MODEL_DIR / DECODER),
            joiner=str(MODEL_DIR / JOINER),
            keywords_file=str(keys),
            num_threads=2,
            provider="cpu",
        )
        self._stream = self._kws.create_stream()
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, name="awake-mic", daemon=True)
        self._thread.start()
        log.info("mic wake device=%s kws=sherpa keywords=%s", self.device, keys)

    def close(self) -> None:
        self._stop.set()
        self._paused = False
        self._stop_capture()
        if self._thread is not None:
            self._thread.join(timeout=2)
            self._thread = None

    def _loop(self) -> None:
        kws = self._kws
        stream = self._stream
        if kws is None or stream is None:
            return
        cmd = [
            "arecord",
            "-D",
            self.device,
            "-f",
            "S16_LE",
            "-r",
            str(RATE),
            "-c",
            "1",
            "-t",
            "raw",
            "-q",
        ]
        nbytes = CHUNK * 2
        while not self._stop.is_set():
            if self._paused:
                time.sleep(0.1)
                continue
            try:
                self._proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
            except OSError as exc:
                log.warning("arecord failed: %s", exc)
                return
            assert self._proc.stdout is not None
            while not self._stop.is_set() and not self._paused:
                raw = self._proc.stdout.read(nbytes)
                if not raw or len(raw) < nbytes:
                    break
                samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
                stream.accept_waveform(RATE, samples)
                while kws.is_ready(stream):
                    kws.decode_stream(stream)
                result = kws.get_result(stream)
                if not result:
                    continue
                now = time.monotonic()
                kws.reset_stream(stream)
                if now - self._last < COOLDOWN_S:
                    continue
                self._last = now
                log.info("mic detected %s", result)
                self.session.handle_text("wake")
            self._stop_capture()
