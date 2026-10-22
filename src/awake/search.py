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
    from dashscope import Generation

    model = cfg.get("DASHSCOPE_SEARCH_MODEL") or "qwen-turbo"
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
    if resp is None or getattr(resp, "status_code", 200) not in (200, None):
        raise RuntimeError(f"search failed: {resp}")
    text = _choice_text(resp)
    if not text:
        raise RuntimeError(f"search empty: {resp}")
    log.info("search chars=%s", len(text))
    return text
