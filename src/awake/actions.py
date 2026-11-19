# -*- coding: utf-8 -*-
"""Dispatch AWAKE intents. No remote import. No chassis serial."""

from __future__ import annotations

import logging

from awake.intent import Intent, named_music_query
from awake.memory import get_store, should_extract

log = logging.getLogger("awake.actions")

_YES = ("记住吧", "要记住", "好的", "可以", "是的", "对", "要", "好")
_NO = ("不要记", "不用了", "算了", "不要", "不是", "别")


def is_yes(text: str) -> bool:
    compact = "".join((text or "").split())
    return any(w in compact for w in _YES) and not is_no(text)


def is_no(text: str) -> bool:
    compact = "".join((text or "").split())
    return any(w in compact for w in _NO)


def run_intent(intent: Intent, text: str, ident: dict, pending: list | None) -> tuple[str, list | None]:
    name = intent.name
    if name == "halt":
        from awake.halt import drive_stop

        drive_stop()
        return "好，已停发。", pending
    if name == "exit":
        return "__exit__", pending
    if name == "volume_up":
        from awake.volume import louder

        return louder(), pending
    if name == "volume_down":
        from awake.volume import quieter

        return quieter(), pending
    if name == "volume_mute":
        from awake.volume import mute

        return mute(), pending
    if name == "volume_unmute":
        from awake.volume import unmute

        return unmute(), pending
    if name == "time":
        from awake.tools import get_time

        return get_time(ident), pending
    if name == "date":
        from awake.tools import get_date

        return get_date(ident), pending
    if name == "battery":
        from awake.tools import get_battery

        try:
            return get_battery(ident), pending
        except Exception as exc:
            log.warning("battery: %s", exc)
            return "电量读不到。", pending
    if name == "drive":
        from awake.halt import drive_hold, parse_drive_cmd

        cmd = parse_drive_cmd(text)
        if cmd is None:
            return "方向没听清，再说前进、后退、左移、右移、左转或右转。", pending
        try:
            return drive_hold(*cmd), pending
        except Exception as exc:
            log.warning("drive: %s", exc)
            return "这步没走成。", pending
    if name in ("weather", "news"):
        from awake.cloud import load_cloud
        from awake.search import web_search

        try:
            return web_search(text, load_cloud()), pending
        except Exception as exc:
            log.warning("%s search: %s", name, exc)
            return "查询暂时不可用，稍后再试。", pending
    if name in ("alarm", "countdown", "remind"):
        return "这个提醒功能还没接上，先记下需求。", pending
    if name == "remember":
        return _ask_remember(text, pending)
    if name == "photo":
        from awake.photo import take_photo

        try:
            path = take_photo()
            return f"拍好了，存在{path.name}。", pending
        except Exception as exc:
            log.warning("photo: %s", exc)
            return "这张没拍上。", pending
    if name == "music_stop":
        from awake.music import stop

        return stop(), pending
    if name == "music_random":
        from awake.music import play

        return play(randomize=True), pending
    if name == "music_named":
        from awake.music import play

        q = named_music_query(text)
        return play(named=q), pending
    if name == "music_play":
        from awake.music import play

        q = named_music_query(text)
        if q:
            return play(named=q), pending
        return play(randomize=False), pending
    return "这句我没做成指令。", pending


def _ask_remember(text: str, pending: list | None) -> tuple[str, list | None]:
    from awake.cloud import extract_facts

    try:
        items = extract_facts(text)
    except Exception as exc:
        log.warning("extract: %s", exc)
        items = []
    if not items:
        return "要记什么再说一遍。", pending
    store = get_store()
    for item in items:
        row = store.get(str(item.get("kind") or "other"), str(item.get("key") or "note"))
        if row is not None and str(row["value"]) != str(item.get("value") or ""):
            return (
                f"主人档案里已有{row['text']}，要改成{item.get('text') or item.get('value')}吗？",
                items,
            )
    summary = "；".join(str(i.get("text") or i.get("value") or "") for i in items)
    return f"要记下{summary}吗？", items


def apply_pending(pending: list | None, text: str) -> tuple[str | None, list | None]:
    if not pending:
        return None, None
    if is_no(text):
        return "好，不记。", None
    if is_yes(text) or should_extract(text):
        store = get_store()
        for item in pending:
            store.upsert(
                kind=str(item.get("kind") or "other"),
                key=str(item.get("key") or "note"),
                value=str(item.get("value") or ""),
                text=str(item.get("text") or item.get("value") or ""),
                source="confirm",
            )
        return "记下了。", None
    return None, pending
