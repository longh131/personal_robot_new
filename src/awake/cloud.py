# -*- coding: utf-8 -*-
"""Cloud ASR/TTS/LLM. Put secrets in config/cloud.env, not here."""

from __future__ import annotations

import audioop
import json
import logging
import os
import select
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
import wave
from collections import deque
from collections.abc import Callable
from pathlib import Path

log = logging.getLogger("awake.cloud")

ENV_PATH = Path("/opt/personal_robot/config/cloud.env")
REQUIRED = ("DASHSCOPE_API_KEY",)


def load_cloud(path: Path = ENV_PATH) -> dict[str, str]:
    if not path.is_file():
        raise FileNotFoundError(f"missing {path}; copy config/cloud.env.example")
    out: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        out[key.strip()] = val.strip().strip('"').strip("'")
    missing = [k for k in REQUIRED if not out.get(k)]
    if missing:
        raise ValueError(f"fill {path}: {', '.join(missing)}")
    return out


_LLM_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "查询天气、新闻、时事等需要上网的信息。",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string", "description": "搜索词"}},
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_time",
            "description": "查询当前本地时间（几点几分）。不要自己编时间。",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_date",
            "description": "查询今天的日期和星期。不要自己编日期。",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_battery",
            "description": "查询机器人电池电量和充放电状态。不要自己编电量。",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "remember_fact",
            "description": "把主人的长期偏好或身份事实写入记忆。问句不要调用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "kind": {"type": "string", "description": "preference/person/habit/other"},
                    "key": {"type": "string", "description": "如 drink、name"},
                    "value": {"type": "string"},
                    "text": {"type": "string", "description": "一句中文事实"},
                },
                "required": ["kind", "key", "value", "text"],
            },
        },
    },
]


def _run_tool(name: str, args: dict, cfg: dict[str, str], ident: dict) -> str:
    from awake.search import web_search
    from awake.memory import get_store
    from awake.tools import get_battery, get_date, get_time

    if name == "web_search":
        return web_search(str(args.get("query") or ""), cfg)
    if name == "get_time":
        return get_time(ident)
    if name == "get_date":
        return get_date(ident)
    if name == "get_battery":
        return get_battery(ident)
    if name == "remember_fact":
        get_store().upsert(
            kind=str(args.get("kind") or "other"),
            key=str(args.get("key") or "note"),
            value=str(args.get("value") or ""),
            text=str(args.get("text") or args.get("value") or ""),
            source="tool",
        )
        return "已记住"
    return f"没有这个工具：{name}"


def _deepseek_url(cfg: dict[str, str]) -> str:
    base = (cfg.get("DEEPSEEK_BASE_URL") or "https://api.deepseek.com").rstrip("/")
    if base.endswith("/anthropic"):
        raise ValueError("use OpenAI base_url, not Anthropic")
    if base.endswith("/v1"):
        return base + "/chat/completions"
    return base + "/v1/chat/completions"


def _deepseek_complete(
    cfg: dict[str, str],
    messages: list[dict],
    *,
    tools: list[dict] | None = None,
) -> dict:
    key = cfg.get("DEEPSEEK_API_KEY") or ""
    if not key:
        raise ValueError("fill DEEPSEEK_API_KEY in config/cloud.env")
    model = cfg.get("DEEPSEEK_LLM_MODEL") or "deepseek-flash"
    payload: dict = {"model": model, "messages": messages, "max_tokens": 256}
    if tools:
        payload["tools"] = tools
    req = urllib.request.Request(
        _deepseek_url(cfg),
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Accept-Encoding": "identity",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8")
            status = getattr(resp, "status", 200)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")[:300]
        raise RuntimeError(f"llm http {exc.code}: {body}") from exc
    data = json.loads(raw)
    if status != 200:
        raise RuntimeError(f"llm http {status}: {raw[:300]}")
    return data


def _choice_message(data: dict) -> dict:
    choices = data.get("choices") or []
    if not choices:
        raise RuntimeError("llm empty choices")
    msg = choices[0].get("message") or {}
    return msg


def llm_chat(
    user_text: str,
    history: list[dict],
    ident: dict,
    cfg: dict[str, str] | None = None,
) -> str:
    cfg = cfg or load_cloud()
    from awake.search import needs_search, web_search
    from awake.tools import get_battery, get_date, get_time, needs_battery, needs_date, needs_time

    name = str(ident.get("name") or "小派")
    who = str(ident.get("addressing") or "你")
    persona = str(ident.get("persona") or "")
    system = (
        f"你是名为{name}的个人机器人，称呼对方为{who}。"
        f"{persona}"
        "用一两句中文口语回答，不要列清单，不要提自己是大模型。"
        "不会的事就直说。运动、底盘控制你做不了。"
        "问几点用 get_time，问日期或星期用 get_date，电量用 get_battery，天气新闻用 web_search。"
        "主人说出长期偏好时调用 remember_fact。回答口味、习惯、称呼时必须用系统里的长期事实，不要编。"
        "不要编造实时信息。"
    )
    from awake.memory import get_store

    mem = get_store().prompt_block(user_text)
    if mem:
        system = system + "\n" + mem
    messages: list[dict] = [{"role": "system", "content": system}]
    messages.extend(history[-8:])
    facts: list[str] = []
    if needs_time(user_text):
        facts.append(get_time(ident))
    if needs_date(user_text):
        facts.append(get_date(ident))
    if needs_battery(user_text):
        try:
            facts.append(get_battery(ident))
        except Exception as exc:
            log.warning("battery failed: %s", exc)
            facts.append("电量读不到")
    if needs_search(user_text):
        facts.append(web_search(user_text, cfg))
    content = user_text
    use_tools = True
    if facts:
        content = f"{user_text}\n\n查到：{' '.join(facts)}\n用一两句口语告诉{who}。"
        use_tools = False
    messages.append({"role": "user", "content": content})
    data = _deepseek_complete(cfg, messages, tools=_LLM_TOOLS if use_tools else None)
    msg = _choice_message(data)
    calls = msg.get("tool_calls") or []
    if calls:
        messages.append(
            {
                "role": "assistant",
                "content": msg.get("content") or "",
                "tool_calls": calls,
            }
        )
        for call in calls:
            if not isinstance(call, dict):
                continue
            fn = call.get("function") or {}
            try:
                args = json.loads(fn.get("arguments") or "{}")
            except json.JSONDecodeError:
                args = {}
            if not isinstance(args, dict):
                args = {}
            try:
                result = _run_tool(str(fn.get("name") or ""), args, cfg, ident)
            except Exception as exc:
                result = f"工具失败：{exc}"
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call.get("id"),
                    "content": result,
                }
            )
        data = _deepseek_complete(cfg, messages)
        msg = _choice_message(data)
    text = str(msg.get("content") or "").strip()
    if not text:
        raise RuntimeError("llm empty")
    log.info("llm chars=%s model=%s", len(text), cfg.get("DEEPSEEK_LLM_MODEL") or "deepseek-flash")
    return text


TTS_URL = "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation"


def _read_chunk(fp, n: int, timeout: float) -> bytes | None:
    """None = timeout; b'' = EOF."""
    ready, _, _ = select.select([fp], [], [], timeout)
    if not ready:
        return None
    return os.read(fp.fileno(), n)


def _stop_proc(proc: subprocess.Popen | None) -> None:
    if proc is None or proc.poll() is not None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=1.5)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=1)


def _open_arecord(device: str, rate: int) -> subprocess.Popen:
    return subprocess.Popen(
        ["arecord", "-D", device, "-f", "S16_LE", "-r", str(rate), "-c", "1", "-t", "raw", "-q"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def _talk_capture_dev() -> str:
    from settings import robot_get

    if robot_get("interrupt", "enabled", default=True):
        return "pipewire"
    from settings import audio_device

    return audio_device("capture")


def record_utterance(
    seconds: float | None = None,
    cfg: dict[str, str] | None = None,
    should_stop: Callable[[], bool] | None = None,
) -> Path | None:
    """Record until silence after speech. Return None if nobody spoke."""
    from settings import robot_get

    _ = cfg
    device = _talk_capture_dev()
    wait_s = float(robot_get("listen", "wait_s", default=8) or 8)
    max_s = float(seconds if seconds is not None else robot_get("listen", "max_s", default=12) or 12)
    silence_s = float(robot_get("listen", "silence_s", default=0.8) or 0.8)
    rate = 16000
    chunk_n = 512
    chunk_b = chunk_n * 2
    thresh = int(robot_get("listen", "rms", default=500) or 500)
    dt = chunk_n / rate
    pre_n = max(4, int(0.55 / dt))
    pcm = bytearray()
    voiced = False
    heard_s = 0.0
    for attempt in range(5):
        time.sleep(0.2 + 0.25 * attempt)
        proc = _open_arecord(device, rate)
        assert proc.stdout is not None
        quiet = 0.0
        elapsed = 0.0
        pcm.clear()
        voiced = False
        heard_s = 0.0
        pre: deque[bytes] = deque(maxlen=pre_n)
        try:
            time.sleep(0.05)
            if proc.poll() is not None:
                err = (proc.stderr.read() or b"").decode("utf-8", "replace").strip()
                log.warning("arecord exit %s %s", proc.returncode, err or "no stderr")
                continue
            while elapsed < (wait_s if not voiced else max_s):
                if should_stop and should_stop():
                    break
                buf = _read_chunk(proc.stdout, chunk_b, 0.05)
                if buf is None:
                    elapsed += 0.05
                    continue
                if not buf:
                    break
                elapsed += dt
                level = audioop.rms(buf, 2)
                pre.append(bytes(buf))
                if not voiced:
                    if level >= thresh:
                        voiced = True
                        quiet = 0.0
                        pcm.extend(b"".join(pre))
                        heard_s = len(pcm) / 2 / rate
                    continue
                pcm.extend(buf)
                heard_s += dt
                if level < thresh:
                    quiet += dt
                    if quiet >= silence_s and heard_s >= 0.25:
                        break
                else:
                    quiet = 0.0
        finally:
            _stop_proc(proc)
        if voiced:
            break
        if proc.returncode in (0, None, -15, -9):
            break
    if not voiced or len(pcm) < chunk_b:
        log.info("listen no speech")
        return None
    fd, path = tempfile.mkstemp(suffix=".wav", prefix="pr-asr-")
    os.close(fd)
    wav = Path(path)
    with wave.open(str(wav), "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(rate)
        out.writeframes(bytes(pcm))
    log.info("listen wav bytes=%s voiced=%.1fs", len(pcm), heard_s)
    return wav


def listen_transcribe(
    should_stop: Callable[[], bool] | None = None,
    cfg: dict[str, str] | None = None,
) -> str:
    wav = record_utterance(should_stop=should_stop, cfg=cfg)
    if wav is None:
        return ""
    try:
        return asr_once(wav, cfg)
    finally:
        wav.unlink(missing_ok=True)


def asr_once(wav_path: Path, cfg: dict[str, str] | None = None) -> str:
    cfg = cfg or load_cloud()
    import dashscope
    from dashscope.audio.asr import Recognition, RecognitionCallback

    dashscope.api_key = cfg["DASHSCOPE_API_KEY"]
    model = cfg.get("DASHSCOPE_ASR_MODEL") or "paraformer-realtime-v2"
    rec = Recognition(
        model=model,
        format="wav",
        sample_rate=16000,
        callback=RecognitionCallback(),
    )
    result = rec.call(file=str(wav_path))
    if result is None:
        raise RuntimeError("asr empty result")
    if getattr(result, "status_code", 200) not in (200, None):
        raise RuntimeError(f"asr failed: {result}")
    sentence = result.get_sentence()
    parts: list[str] = []
    if isinstance(sentence, dict):
        t = str(sentence.get("text") or "").strip()
        if t:
            parts.append(t)
    elif isinstance(sentence, list):
        for item in sentence:
            if isinstance(item, dict):
                t = str(item.get("text") or "").strip()
                if t:
                    parts.append(t)
    text = "".join(parts).strip()
    log.info("asr chars=%s", len(text))
    return text


def extract_facts(user_text: str, cfg: dict[str, str] | None = None) -> list[dict]:
    cfg = cfg or load_cloud()
    data = _deepseek_complete(
        cfg,
        [
            {
                "role": "system",
                "content": (
                    "从用户话里抽出0到3条可长期保存的个人事实。"
                    "只输出JSON数组，不要其它字。"
                    '元素: {"kind":"preference|person|habit|other","key":"drink|name|...","value":"...","text":"一句中文事实"}。'
                    "问句、天气、时间、指令不要抽。没有则[]。"
                ),
            },
            {"role": "user", "content": user_text},
        ],
    )
    raw = str(_choice_message(data).get("content") or "").strip()
    start = raw.find("[")
    end = raw.rfind("]")
    if start < 0 or end <= start:
        return []
    try:
        items = json.loads(raw[start : end + 1])
    except json.JSONDecodeError:
        return []
    if not isinstance(items, list):
        return []
    out = []
    for item in items[:3]:
        if isinstance(item, dict) and item.get("value"):
            out.append(item)
    return out


def _tts_fetch(text: str, cfg: dict[str, str]) -> tuple[bytes, str]:
    import base64

    model = cfg.get("DASHSCOPE_TTS_MODEL") or "qwen3-tts-flash"
    voice = cfg.get("DASHSCOPE_TTS_VOICE") or "Cherry"
    payload = json.dumps(
        {
            "model": model,
            "input": {"text": text, "voice": voice, "language_type": "Chinese"},
        }
    ).encode()
    req = urllib.request.Request(
        TTS_URL,
        data=payload,
        method="POST",
        headers={
            "Authorization": f"Bearer {cfg['DASHSCOPE_API_KEY']}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:400]
        raise RuntimeError(f"tts http {exc.code}: {detail}") from exc
    output = body.get("output") if isinstance(body, dict) else None
    audio = output.get("audio") if isinstance(output, dict) else None
    raw = b""
    if isinstance(audio, dict):
        url = audio.get("url")
        data = audio.get("data")
        if url:
            with urllib.request.urlopen(str(url), timeout=10) as resp:
                raw = resp.read()
        elif data:
            raw = base64.b64decode(data)
    if not raw:
        raise RuntimeError(f"tts empty: {body}")
    return raw, voice


def _pcm_wav(pcm: bytes, rate: int = 16000) -> Path:
    fd, path = tempfile.mkstemp(suffix=".wav", prefix="pr-barge-")
    os.close(fd)
    outp = Path(path)
    with wave.open(str(outp), "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(rate)
        out.writeframes(pcm)
    return outp


def tts_say(
    text: str,
    cfg: dict[str, str] | None = None,
    *,
    barge_in: bool | None = None,
    should_stop: Callable[[], bool] | None = None,
) -> Path | None:
    """Play TTS. Optional barge-in via PipeWire duplex (not exclusive plughw)."""
    cfg = cfg or load_cloud()
    text = (text or "").strip()
    if not text:
        return None
    from settings import audio_device, robot_get

    log.info("tts synth chars=%s", len(text))
    raw, voice = _tts_fetch(text, cfg)
    play_dev = audio_device("playback")
    if barge_in is None:
        barge_in = bool(robot_get("interrupt", "enabled", default=True))
    fd, path = tempfile.mkstemp(suffix=".wav", prefix="pr-tts-")
    os.close(fd)
    wav = Path(path)
    wav.write_bytes(raw)
    if not barge_in:
        try:
            proc = subprocess.run(
                ["aplay", "-D", play_dev, "-q", str(wav)],
                capture_output=True,
                text=True,
                timeout=20,
            )
            if proc.returncode != 0:
                raise RuntimeError(proc.stderr.strip() or f"aplay {proc.returncode}")
            log.info("tts played chars=%s voice=%s device=%s", len(text), voice, play_dev)
        finally:
            wav.unlink(missing_ok=True)
            time.sleep(0.25)
        return None
    duplex = "pipewire"
    grace = float(robot_get("interrupt", "grace_s", default=0.5) or 0.5)
    thresh = int(robot_get("interrupt", "rms", default=0) or 0) or 1400
    hold_s = float(robot_get("interrupt", "hold_s", default=0.18) or 0.18)
    silence_s = float(robot_get("listen", "silence_s", default=0.8) or 0.8)
    max_s = float(robot_get("listen", "max_s", default=12) or 12)
    rate = 16000
    chunk_n = 512
    chunk_b = chunk_n * 2
    dt = chunk_n / rate
    play = None
    cap = None
    pcm = bytearray()
    interrupted = False
    pre_n = max(4, int(0.55 / dt))
    pre: deque[bytes] = deque(maxlen=pre_n)
    try:
        play = subprocess.Popen(
            ["aplay", "-D", duplex, "-q", str(wav)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        cap = subprocess.Popen(
            ["arecord", "-D", duplex, "-f", "S16_LE", "-r", str(rate), "-c", "1", "-t", "raw", "-q"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        time.sleep(0.08)
        if cap.poll() is not None:
            log.warning("tts barge capture failed, play only")
            try:
                play.wait(timeout=20)
            except subprocess.TimeoutExpired:
                play.kill()
                play.wait(timeout=1)
            log.info("tts played chars=%s voice=%s device=%s", len(text), voice, duplex)
            return None
        elapsed = 0.0
        hot = 0.0
        quiet = 0.0
        heard_s = 0.0
        listen_th = int(robot_get("listen", "rms", default=500) or 500)
        wait_s = float(robot_get("listen", "wait_s", default=8) or 8)
        phase = "play"
        voiced = False
        deadline = time.monotonic() + 22.0 + wait_s
        while time.monotonic() < deadline:
            if should_stop and should_stop():
                break
            play_done = play.poll() is not None
            chunk = _read_chunk(cap.stdout, chunk_b, 0.05) if cap.stdout else None
            if chunk is None:
                if play_done and phase == "play":
                    phase = "listen"
                    log.info("tts played chars=%s voice=%s device=%s", len(text), voice, duplex)
                    pre.clear()
                    pcm.clear()
                    voiced = False
                    elapsed = 0.0
                    continue
                if phase == "listen" and not voiced:
                    elapsed += 0.05
                    if elapsed >= wait_s:
                        break
                continue
            if chunk == b"":
                break
            level = audioop.rms(chunk, 2)
            if phase == "play":
                elapsed += dt
                pre.append(bytes(chunk))
                if elapsed >= grace and level >= thresh:
                    hot += dt
                    if hot >= hold_s:
                        phase = "listen"
                        voiced = True
                        interrupted = True
                        pcm.extend(b"".join(pre))
                        heard_s = len(pcm) / 2 / rate
                        quiet = 0.0
                        play.terminate()
                        log.info("tts barge-in rms=%s", level)
                else:
                    hot = 0.0
                if play_done and phase == "play":
                    phase = "listen"
                    log.info("tts played chars=%s voice=%s device=%s", len(text), voice, duplex)
                    pre.clear()
                    elapsed = 0.0
                    voiced = False
                    pcm.clear()
                continue
            if not voiced:
                elapsed += dt
                pre.append(bytes(chunk))
                if level >= listen_th:
                    voiced = True
                    pcm.extend(b"".join(pre))
                    heard_s = len(pcm) / 2 / rate
                    quiet = 0.0
                elif elapsed >= wait_s:
                    break
                continue
            pcm.extend(chunk)
            heard_s += dt
            if level < listen_th:
                quiet += dt
                if quiet >= silence_s and heard_s >= 0.25:
                    break
            else:
                quiet = 0.0
            if heard_s >= max_s:
                break
        if interrupted:
            log.info("tts interrupted chars=%s pcm=%s", len(text), len(pcm))
        elif voiced:
            log.info("tts then listen pcm=%s", len(pcm))
        if voiced and len(pcm) >= chunk_b * 8:
            return _pcm_wav(bytes(pcm), rate)
        return None
    finally:
        _stop_proc(cap)
        _stop_proc(play)
        wav.unlink(missing_ok=True)
