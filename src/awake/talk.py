# -*- coding: utf-8 -*-
"""AWAKE talk: greet, listen, cloud LLM, TTS. Exit phrases back to IDLE."""

from __future__ import annotations

import logging
import random
import time

from awake.cloud import asr_once, extract_facts, listen_transcribe, llm_chat, tts_say
from awake.memory import get_store, should_extract
from runtime.events import Event
from runtime.machine import Mode
from settings import load_identity, load_idle_timeout_s

log = logging.getLogger("awake.talk")


def _pick(ident: dict, key: str, fallback: str) -> str:
    lines = ident.get(key) or [fallback]
    return random.choice(lines)


def _wants_exit(text: str, phrases: list) -> bool:
    compact = text.replace(" ", "")
    return any(str(p).replace(" ", "") and str(p).replace(" ", "") in compact for p in phrases)


def run_awake(*, machine, session, cues=None, mic=None) -> None:
    ident = load_identity()
    pause = getattr(mic, "set_paused", None)
    speak = getattr(cues, "set_speaking", None)

    def still_awake() -> bool:
        return getattr(machine, "mode", None) == Mode.AWAKE

    def stopped() -> bool:
        return not still_awake()
    if callable(pause):
        pause(True)
    try:
        hello = _pick(ident, "greetings", "我在。")
        log.info("greet %s", hello)
        if callable(speak):
            speak(True)
        pending_wav = None
        try:
            pending_wav = tts_say(hello)
        except Exception as exc:
            log.warning("greet tts failed: %s", exc)
            pending_wav = None
        finally:
            if callable(speak):
                speak(False)

        phrases = ident.get("exit_phrases") or ["再见"]
        history: list[dict] = []
        idle_s = load_idle_timeout_s()
        store = get_store()
        if session is not None:
            session.timeout_s = idle_s
            session.note_entered()

        def farewell() -> None:
            bye = _pick(ident, "farewells", "先这样。")
            log.info("farewell %s", bye)
            if callable(speak):
                speak(True)
            try:
                tts_say(bye, barge_in=False)
            except Exception as exc:
                log.warning("farewell tts failed: %s", exc)
            finally:
                if callable(speak):
                    speak(False)
            if session is not None and getattr(machine, "mode", None) == Mode.AWAKE:
                session.events.put(Event.EXIT_TO_IDLE)

        while getattr(machine, "mode", None) == Mode.AWAKE:
            text = ""
            wav = pending_wav
            pending_wav = None
            try:
                if wav is not None:
                    text = asr_once(wav)
                    wav.unlink(missing_ok=True)
                    wav = None
                    if not text:
                        text = listen_transcribe(should_stop=stopped)
                else:
                    text = listen_transcribe(should_stop=stopped)
            except Exception as exc:
                log.warning("listen/asr failed: %s", exc)
                text = ""
            finally:
                if wav is not None:
                    wav.unlink(missing_ok=True)
            last = getattr(session, "last_active", 0.0) if session is not None else 0.0
            timed_out = getattr(machine, "mode", None) != Mode.AWAKE
            if not timed_out and last > 0 and (time.monotonic() - last) > idle_s:
                log.warning("awake idle timeout")
                timed_out = True
            if not text:
                log.info("asr empty")
                if timed_out:
                    farewell()
                    return
                continue
            log.info("heard %s", text)
            if _wants_exit(text, phrases):
                farewell()
                return
            if session is not None:
                session.note_entered()
            if getattr(machine, "mode", None) != Mode.AWAKE:
                return
            try:
                reply = llm_chat(text, history, ident)
            except Exception as exc:
                log.warning("llm failed: %s", exc)
                reply = "这句我没接上，再说一次？"
            history.append({"role": "user", "content": text})
            history.append({"role": "assistant", "content": reply})
            if callable(speak):
                speak(True)
            try:
                pending_wav = tts_say(reply)
            except Exception as exc:
                log.warning("reply tts failed: %s", exc)
                pending_wav = None
            finally:
                if callable(speak):
                    speak(False)
            if should_extract(text):
                try:
                    for item in extract_facts(text):
                        store.upsert(
                            kind=str(item.get("kind") or "other"),
                            key=str(item.get("key") or "note"),
                            value=str(item.get("value") or ""),
                            text=str(item.get("text") or item.get("value") or ""),
                            source=text,
                        )
                except Exception as exc:
                    log.warning("memory extract failed: %s", exc)
    finally:
        if callable(pause):
            pause(False)
