# -*- coding: utf-8 -*-
"""WebRTC preview + two-way voice. No ASR/TTS/LLM."""

from __future__ import annotations

import asyncio
import audioop
import io
import logging
import subprocess
import threading
from collections.abc import Callable

from settings import audio_device, robot_get

log = logging.getLogger("remote.rtc")


class RtcSession:
    def __init__(self, jpeg_fn: Callable[[], bytes]) -> None:
        self._jpeg_fn = jpeg_fn
        self._loop = asyncio.new_event_loop()
        threading.Thread(target=self._run, name="remote-rtc", daemon=True).start()
        self._pc = None
        self._play: subprocess.Popen | None = None
        self._cap: subprocess.Popen | None = None

    def _run(self) -> None:
        asyncio.set_event_loop(self._loop)

        def _handler(_loop, ctx: dict) -> None:
            log.warning("rtc loop: %s", ctx.get("message") or ctx)

        self._loop.set_exception_handler(_handler)
        self._loop.run_forever()

    def close(self) -> None:
        fut = asyncio.run_coroutine_threadsafe(self._close_pc(), self._loop)
        try:
            fut.result(timeout=5)
        except Exception as exc:
            log.warning("rtc close: %s", exc)
        self.stop_audio()

    def answer(self, offer: dict) -> dict:
        fut = asyncio.run_coroutine_threadsafe(self._answer(offer), self._loop)
        return fut.result(timeout=20)

    async def _close_pc(self) -> None:
        pc = self._pc
        self._pc = None
        if pc is not None:
            await pc.close()

    async def _answer(self, offer: dict) -> dict:
        from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack, AudioStreamTrack
        from av import AudioFrame, VideoFrame
        from PIL import Image
        import numpy as np

        jpeg_fn = self._jpeg_fn
        session = self

        class JpegTrack(VideoStreamTrack):
            async def recv(self):
                pts, time_base = await self.next_timestamp()
                raw = jpeg_fn()
                if not raw:
                    arr = np.zeros((480, 640, 3), dtype=np.uint8)
                else:
                    img = Image.open(io.BytesIO(raw)).convert("RGB")
                    arr = np.asarray(img)
                frame = VideoFrame.from_ndarray(arr, format="rgb24")
                frame.pts = pts
                frame.time_base = time_base
                return frame

        class MicTrack(AudioStreamTrack):
            def __init__(self) -> None:
                super().__init__()
                self._state = None

            async def recv(self):
                pts, time_base = await self.next_timestamp()
                cap = session.start_capture()
                raw = b""
                if cap.stdout is not None:
                    raw = await asyncio.to_thread(cap.stdout.read, 640)
                if not raw:
                    raw = b"\x00" * 640
                conv, self._state = audioop.ratecv(raw, 2, 1, 16000, 48000, self._state)
                need = 1920
                if len(conv) < need:
                    conv += b"\x00" * (need - len(conv))
                conv = conv[:need]
                samples = np.frombuffer(conv, dtype=np.int16).reshape(1, -1)
                frame = AudioFrame.from_ndarray(samples, format="s16", layout="mono")
                frame.sample_rate = 48000
                frame.pts = pts
                frame.time_base = time_base
                return frame

        await self._close_pc()
        self.stop_audio()
        pc = RTCPeerConnection()
        self._pc = pc
        pc.addTrack(JpegTrack())
        pc.addTrack(MicTrack())

        @pc.on("track")
        def on_track(track) -> None:
            if track.kind == "audio":
                asyncio.ensure_future(self._play_remote(track))

        await pc.setRemoteDescription(
            RTCSessionDescription(sdp=str(offer.get("sdp") or ""), type=str(offer.get("type") or "offer"))
        )
        answer = await pc.createAnswer()
        await pc.setLocalDescription(answer)
        for _ in range(50):
            if pc.iceGatheringState == "complete":
                break
            await asyncio.sleep(0.05)
        local = pc.localDescription
        log.info("rtc answer ice=%s", pc.iceGatheringState)
        return {"ok": True, "sdp": local.sdp, "type": local.type}

    def start_capture(self) -> subprocess.Popen:
        if self._cap is not None and self._cap.poll() is None:
            return self._cap
        dev = audio_device("capture")
        log.info("rtc capture %s", dev)
        self._cap = subprocess.Popen(
            ["arecord", "-D", dev, "-f", "S16_LE", "-r", "16000", "-c", "1", "-t", "raw", "-q"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        return self._cap

    def stop_audio(self) -> None:
        for proc in (self._cap, self._play):
            if proc is None or proc.poll() is not None:
                continue
            proc.terminate()
            try:
                proc.wait(timeout=1.5)
            except subprocess.TimeoutExpired:
                proc.kill()
        self._cap = None
        self._play = None

    async def _play_remote(self, track) -> None:
        dev = "pipewire" if robot_get("interrupt", "enabled", default=True) else audio_device("playback")
        play = subprocess.Popen(
            ["aplay", "-D", dev, "-f", "S16_LE", "-r", "48000", "-c", "1", "-t", "raw", "-q"],
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self._play = play
        try:
            while True:
                frame = await track.recv()
                if play.stdin is None:
                    break
                pcm = frame.to_ndarray().tobytes()
                if frame.layout.nb_channels > 1:
                    pcm = audioop.tomono(pcm, 2, 0.5, 0.5)
                if frame.sample_rate != 48000:
                    pcm, _ = audioop.ratecv(pcm, 2, 1, frame.sample_rate, 48000, None)
                play.stdin.write(pcm)
        except Exception as exc:
            log.info("rtc play ended: %s", exc)
        finally:
            if play.stdin:
                try:
                    play.stdin.close()
                except BrokenPipeError:
                    pass
            if play.poll() is None:
                play.terminate()
