# -*- coding: utf-8 -*-
"""Dispatch AWAKE intents. No remote import. No chassis serial."""

from __future__ import annotations

import logging
import re

from awake.intent import Intent, named_music_query
from awake.memory import get_store, should_extract
from awake.scheduler import (
    add_job,
    cancel_kind,
    format_remaining,
    list_active,
    parse_duration_s,
    parse_remind_message,
)

log = logging.getLogger("awake.actions")

_YES = ("记住吧", "要记住", "好的", "可以", "是的", "对", "要", "好", "删掉", "忘掉吧")
_NO = ("不要记", "不用了", "算了", "不要", "不是", "别")


def is_yes(text: str) -> bool:
    compact = "".join((text or "").split())
    return any(w in compact for w in _YES) and not is_no(text)


def is_no(text: str) -> bool:
    compact = "".join((text or "").split())
    return any(w in compact for w in _NO)


def run_intent(intent: Intent, text: str, ident: dict, pending) -> tuple[str, object]:
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
            return "电量读不到，UPS 可能没接好。", pending
    if name == "status_camera":
        from awake.status import camera_report

        return camera_report(), pending
    if name == "status_estop":
        from awake.status import estop_report

        return estop_report(), pending
    if name == "drive_faster":
        from awake.halt import drive_faster

        return drive_faster(), pending
    if name == "drive_slower":
        from awake.halt import drive_slower

        return drive_slower(), pending
    if name == "drive":
        from awake.halt import drive_hold, parse_drive_cmd

        cmd = parse_drive_cmd(text)
        if cmd is None:
            return "方向没听清，再说前进、后退、左移、右移、左转或右转。", pending
        try:
            return drive_hold(*cmd), pending
        except Exception as exc:
            log.warning("drive: %s", exc)
            return "运动链路没通，这步没走成。", pending
    if name in ("weather", "news"):
        from awake.cloud import load_cloud
        from awake.search import web_search

        try:
            return web_search(text, load_cloud()), pending
        except Exception as exc:
            log.warning("%s search: %s", name, exc)
            return "云查询超时或不可用，稍后再试。", pending
    if name == "timer_cancel":
        n = cancel_kind(None)
        if n <= 0:
            return "现在没有进行中的倒计时或提醒。", pending
        return f"好，已取消{n}个定时。", pending
    if name == "countdown":
        return _set_timer("countdown", text, pending)
    if name in ("remind", "alarm"):
        return _set_timer("remind" if name == "remind" else "alarm", text, pending)
    if name == "memory_query":
        return _memory_query(), pending
    if name == "memory_forget":
        return _ask_forget(text, pending)
    if name == "remember":
        return _ask_remember(text, pending)
    if name == "photo":
        from awake.photo import take_photo

        try:
            path = take_photo()
            return f"拍好了，存在{path.name}。", pending
        except Exception as exc:
            log.warning("photo: %s", exc)
            return "相机不可用，这张没拍上。", pending
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


def _set_timer(kind: str, text: str, pending) -> tuple[str, object]:
    sec = parse_duration_s(text)
    if sec is None:
        if kind == "countdown":
            return "倒计时多久？可以说倒计时30秒或2分钟。", pending
        return "多久以后提醒？可以说五分钟后提醒我喝水。", pending
    if sec > 2 * 3600 and kind == "countdown":
        return "倒计时最长两小时，改短一点吧。", pending
    msg = "时间到" if kind == "countdown" else parse_remind_message(text)
    if kind == "alarm" and msg == "到时间了":
        msg = "闹钟时间到"
    job = add_job(kind, sec, msg)
    human = format_remaining(job)
    if kind == "countdown":
        return f"好，倒计时{human}。", pending
    return f"好，{human}后提醒你：{job.message}。", pending


def _memory_query() -> str:
    rows = get_store().list_valid(8)
    if not rows:
        return "档案里还没有记下的事。"
    bits = [str(r["text"]) for r in rows[:5]]
    more = f"等{len(rows)}条。" if len(rows) > 5 else ""
    return "我记得：" + "；".join(bits) + ("。" + more if more else "。")


def _ask_forget(text: str, pending) -> tuple[str, object]:
    compact = "".join((text or "").split())
    q = re.sub(r"(忘掉|忘记|删掉记忆|别记了)", "", compact)
    store = get_store()
    rows = store.search_valid(q, limit=5) if q else store.list_valid(5)
    if not rows:
        return "没找到要忘掉的内容。", pending
    if len(rows) == 1:
        summary = str(rows[0]["text"])
        return f"要忘掉{summary}吗？", {"op": "forget", "rows": rows}
    summary = "；".join(str(r["text"]) for r in rows[:3])
    return f"找到多条：{summary}。要全部忘掉吗？", {"op": "forget", "rows": rows}


def _ask_remember(text: str, pending) -> tuple[str, object]:
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


def apply_pending(pending, text: str) -> tuple[str | None, object]:
    if not pending:
        return None, None
    if isinstance(pending, dict) and pending.get("op") == "forget":
        if is_no(text):
            return "好，不删。", None
        if is_yes(text):
            store = get_store()
            n = 0
            for row in pending.get("rows") or []:
                if store.forget(str(row["kind"]), str(row["key"])):
                    n += 1
            return (f"好，忘掉{n}条。" if n else "没有删掉。"), None
        return None, pending
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


def timer_list_speech() -> str:
    jobs = list_active()
    if not jobs:
        return ""
    bits = [f"{j.kind}还剩{format_remaining(j)}" for j in jobs[:3]]
    return "；".join(bits)
