# -*- coding: utf-8 -*-
"""AWAKE talk loop. Independent of remote/."""

from __future__ import annotations

import logging
import random
import time

from awake.actions import apply_pending, run_intent
from awake.cloud import listen_transcribe, llm_chat, tts_say, asr_once
from awake.intent import match_intent
from runtime.events import Event
from runtime.machine import Mode
from settings import load_identity, load_idle_timeout_s

log = logging.getLogger("awake.talk")


def _pick(ident: dict, key: str, fallback: str) -> str:
    lines = ident.get(key) or [fallback]
    return random.choice(lines)


def run_awake(*, machine, session, cues=None, mic=None) -> None:
    ident = load_identity()
    pause = getattr(mic, "set_paused", None)
    speak = getattr(cues, "set_speaking", None)

    def still_awake() -> bool:
        return getattr(machine, "mode", None) == Mode.AWAKE

    def stopped() -> bool:
        return not still_awake()

    def say(text: str, *, barge: bool | None = None):
        if not text or not still_awake():
            return None
        if callable(speak):
            speak(True)
        try:
            if barge is False:
                return tts_say(text, barge_in=False, should_stop=stopped)
            return tts_say(text, should_stop=stopped)
        except Exception as exc:
            log.warning("tts failed: %s", exc)
            return None
        finally:
            if callable(speak):
                speak(False)

    if callable(pause):
        pause(True)
    pending_mem: list | None = None
    try:
        hello = _pick(ident, "greetings", "我在。")
        log.info("greet %s", hello)
        pending_wav = say(hello)

        history: list[dict] = []
        idle_s = load_idle_timeout_s()
        if session is not None:
            session.timeout_s = idle_s
            session.note_entered()

        def farewell() -> None:
            if not still_awake():
                return
            bye = _pick(ident, "farewells", "先这样。")
            log.info("farewell %s", bye)
            say(bye, barge=False)
            if session is not None and still_awake():
                session.events.put(Event.EXIT_TO_IDLE)

        while still_awake():
            text = ""
            wav = pending_wav
            pending_wav = None
            from awake.music import pause_for_listen, resume_after_listen

            pause_for_listen()
            try:
                if wav is not None:
                    text = asr_once(wav)
                    wav.unlink(missing_ok=True)
                    wav = None
                    if not text and still_awake():
                        text = listen_transcribe(should_stop=stopped)
                elif still_awake():
                    text = listen_transcribe(should_stop=stopped)
            except Exception as exc:
                log.warning("listen/asr failed: %s", exc)
                text = ""
            finally:
                if wav is not None:
                    wav.unlink(missing_ok=True)
                hit_listen = match_intent(text) if text else None
                if hit_listen is None or hit_listen.name != "music_stop":
                    resume_after_listen()
            if not still_awake():
                log.info("awake preempted, skip farewell")
                return
            last = getattr(session, "last_active", 0.0) if session is not None else 0.0
            timed_out = last > 0 and (time.monotonic() - last) > idle_s
            if not text:
                log.info("asr empty")
                if timed_out:
                    farewell()
                    return
                continue
            log.info("heard %s", text)
            if session is not None:
                session.note_entered()

            spoken, pending_mem = apply_pending(pending_mem, text)
            if spoken:
                pending_wav = say(spoken)
                continue

            hit = match_intent(text)
            if hit is not None:
                log.info("intent %s cat=%s", hit.name, hit.category)
                spoken, pending_mem = run_intent(hit, text, ident, pending_mem)
                if spoken == "__exit__":
                    farewell()
                    return
                pending_wav = say(spoken)
                continue

            try:
                reply = llm_chat(text, history, ident)
            except Exception as exc:
                log.warning("llm failed: %s", exc)
                reply = "这句我没接上，再说一次？"
            history.append({"role": "user", "content": text})
            history.append({"role": "assistant", "content": reply})
            history = history[-8:]
            pending_wav = say(reply)
    finally:
        try:
            from awake.music import stop as stop_music

            stop_music()
        except Exception:
            pass
        if callable(pause):
            pause(False)
