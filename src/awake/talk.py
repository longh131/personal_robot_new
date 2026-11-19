# -*- coding: utf-8 -*-
"""AWAKE talk loop. Independent of remote/."""

from __future__ import annotations

import logging
import random
import time

from awake.actions import apply_pending, run_intent
from awake.cloud import listen_transcribe, llm_chat, tts_say, asr_once
from awake.intent import match_intent
from awake.scheduler import pop_due
from runtime.events import Event
from runtime.machine import Mode
from settings import load_identity, load_idle_timeout_s, robot_get

log = logging.getLogger("awake.talk")


def _pick(ident: dict, key: str, fallback: str) -> str:
    lines = ident.get(key) or [fallback]
    return random.choice(lines)


def run_awake(*, machine, session, cues=None, mic=None) -> None:
    ident = load_identity()
    pause = getattr(mic, "set_paused", None)
    speak = getattr(cues, "set_speaking", None)
    empty_need = int(robot_get("awake", "empty_asr_prompt_n", default=2) or 2)
    warn_s = float(robot_get("awake", "timeout_warn_s", default=20) or 20)

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
            # keep session alive; next loop can still listen
            return None
        finally:
            if callable(speak):
                speak(False)

    def announce_due() -> None:
        due = pop_due()
        if not due:
            return
        if cues is not None:
            try:
                cues.chime()
            except Exception:
                pass
        for job in due:
            line = f"{job.message}。" if job.kind != "countdown" else f"倒计时结束：{job.message}。"
            log.info("timer due kind=%s msg=%s", job.kind, job.message)
            say(line, barge=False)

    def check_obstacle_drive() -> None:
        from awake.halt import drive_stop, is_holding
        from awake.status import obstacle_blocked

        if not is_holding():
            return
        if not obstacle_blocked():
            return
        drive_stop()
        log.info("awake obstacle stop while holding")
        say("前面有障碍，先停住了。", barge=False)

    if callable(pause):
        pause(True)
    pending_mem = None
    empty_streak = 0
    timeout_warned = False
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
            announce_due()
            check_obstacle_drive()

            last = getattr(session, "last_active", 0.0) if session is not None else 0.0
            elapsed = (time.monotonic() - last) if last > 0 else 0.0
            if (
                last > 0
                and warn_s > 0
                and not timeout_warned
                and elapsed >= max(1.0, idle_s - warn_s)
            ):
                timeout_warned = True
                say("还在吗？没听到我就先歇了。", barge=False)
                continue

            text = ""
            wav = pending_wav
            pending_wav = None
            from awake.music import pause_for_listen, resume_after_listen

            pause_for_listen()
            try:
                if wav is not None:
                    # post-TTS buffer often echo; empty → fresh listen, don't trust it
                    text = asr_once(wav)
                    wav.unlink(missing_ok=True)
                    wav = None
                    if not text and still_awake():
                        log.info("post-tts asr empty, fresh listen")
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

            announce_due()
            check_obstacle_drive()

            last = getattr(session, "last_active", 0.0) if session is not None else 0.0
            timed_out = last > 0 and (time.monotonic() - last) > idle_s
            if not text:
                log.info("asr empty")
                empty_streak += 1
                if timed_out:
                    farewell()
                    return
                if empty_streak >= empty_need:
                    empty_streak = 0
                    pending_wav = say("没听清，请再说一遍。")
                continue

            empty_streak = 0
            timeout_warned = False
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
                reply = "这句云端没接上，再说一次？"
            history.append({"role": "user", "content": text})
            history.append({"role": "assistant", "content": reply})
            history = history[-8:]
            pending_wav = say(reply)
    finally:
        try:
            from awake.halt import drive_stop

            drive_stop()
        except Exception:
            pass
        try:
            from awake.music import stop as stop_music

            stop_music()
        except Exception:
            pass
        if callable(pause):
            pause(False)
