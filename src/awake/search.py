# -*- coding: utf-8 -*-
"""AWAKE search plugin. LLM does not search; this does."""

from __future__ import annotations

import logging

log = logging.getLogger("awake.search")

HINTS = ("天气", "温度", "多少度", "热不热", "冷不冷", "新闻", "头条", "热点")


def needs_search(text: str) -> bool:
    return any(k in (text or "") for k in HINTS)


def _choice_text(resp) -> str:
    output = getattr(resp, "output", None)
    if output is None:
        return ""
    choices = getattr(output, "choices", None)
    if choices is None and isinstance(output, dict):
        choices = output.get("choices")
    if not choices:
        return ""
    first = choices[0]
    message = getattr(first, "message", None)
    if message is None and isinstance(first, dict):
        message = first.get("message")
    if isinstance(message, dict):
        return str(message.get("content") or "").strip()
    if message is None:
        return ""
    return str(getattr(message, "content", "") or "").strip()


def web_search(query: str, cfg: dict[str, str]) -> str:
    """Real web search via DashScope enable_search. Never raise — keep AWAKE alive."""
    from dashscope import Generation

    model = cfg.get("DASHSCOPE_SEARCH_MODEL") or "qwen-plus"
    try:
        resp = Generation.call(
            model=model,
            api_key=cfg["DASHSCOPE_API_KEY"],
            messages=[
                {
                    "role": "system",
                    "content": "你是搜索助手。根据联网结果用两三句中文列出事实，不要闲聊、不要扮演机器人。",
                },
                {"role": "user", "content": query},
            ],
            result_format="message",
            enable_search=True,
            max_tokens=200,
        )
    except Exception as exc:
        log.warning("search call failed model=%s: %s", model, exc)
        return "联网查询暂时失败，稍后再试。"
    if resp is None or getattr(resp, "status_code", 200) not in (200, None):
        log.warning("search failed model=%s: %s", model, resp)
        code = getattr(resp, "code", None) or ""
        if "Throttling" in str(code) or "429" in str(resp):
            return "查询有点拥挤，稍后再问天气或新闻。"
        return "联网查询暂时失败，稍后再试。"
    text = _choice_text(resp)
    if not text:
        log.warning("search empty model=%s: %s", model, resp)
        return "没有查到有效结果，换个问法试试。"
    log.info("search chars=%s model=%s", len(text), model)
    return text
