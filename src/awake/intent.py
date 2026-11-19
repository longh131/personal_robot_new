# -*- coding: utf-8 -*-
"""AWAKE keyword intents. No remote import. Longest keyword wins, then weight."""

from __future__ import annotations

from dataclasses import dataclass

CAT_SYS = "系统控制"
CAT_MOTOR = "电机控制"
CAT_ASSIST = "助手控制"
CAT_QUERY = "查询类"
CAT_FUN = "娱乐控制"


@dataclass(frozen=True)
class Intent:
    name: str
    category: str
    weight: int
    keywords: tuple[str, ...]


INTENTS: tuple[Intent, ...] = (
    Intent(
        "halt",
        CAT_SYS,
        100,
        ("急停", "停止运动", "停止行走", "别动", "停下", "站住", "不要走了"),
    ),
    Intent("exit", CAT_SYS, 90, ("回去休息", "没事了", "先这样", "拜拜", "再见", "退出")),
    Intent(
        "volume_up",
        CAT_SYS,
        85,
        (
            "音量最大",
            "音量调高",
            "音量调大",
            "调高音量",
            "调大音量",
            "提高音量",
            "大声一点",
            "大声点",
            "大一点",
            "音量大",
            "声音大点",
            "声音大",
            "调大",
            "调高",
        ),
    ),
    Intent(
        "volume_down",
        CAT_SYS,
        85,
        (
            "音量最小",
            "音量调低",
            "音量调小",
            "调低音量",
            "调小音量",
            "降低音量",
            "小声一点",
            "小声点",
            "小一点",
            "音量小",
            "声音小点",
            "声音小",
            "调小",
            "调低",
        ),
    ),
    Intent("volume_unmute", CAT_SYS, 85, ("取消静音", "解除静音")),
    Intent("volume_mute", CAT_SYS, 85, ("静音",)),
    Intent(
        "timer_cancel",
        CAT_ASSIST,
        88,
        ("取消倒计时", "取消提醒", "取消闹钟", "关掉提醒", "不要提醒了"),
    ),
    Intent("time", CAT_QUERY, 80, ("现在时间", "什么时候了", "几点了", "几点", "报时")),
    Intent("date", CAT_QUERY, 80, ("星期几", "今天星期", "几号", "日期")),
    Intent("battery", CAT_QUERY, 80, ("还有电", "电量", "电池")),
    Intent(
        "status_camera",
        CAT_QUERY,
        78,
        (
            "检查一下相机",
            "检查相机",
            "看看相机",
            "相机怎么样",
            "摄像头怎么样",
            "相机怎样",
            "摄像头怎样",
            "相机好不好",
            "摄像头好不好",
            "相机状态",
            "摄像头状态",
            "摄像头",
        ),
    ),
    Intent(
        "status_estop",
        CAT_QUERY,
        78,
        ("急停了吗", "有没有急停", "是不是急停", "急停状态"),
    ),
    Intent(
        "drive_faster",
        CAT_MOTOR,
        76,
        ("走快一点", "再快点", "加速", "快点"),
    ),
    Intent(
        "drive_slower",
        CAT_MOTOR,
        76,
        ("走慢一点", "再慢点", "减速", "慢点"),
    ),
    Intent(
        "drive",
        CAT_MOTOR,
        75,
        (
            "往前走",
            "向前走",
            "向后退",
            "向左移",
            "向右移",
            "向左转",
            "向右转",
            "前进",
            "后退",
            "左移",
            "右移",
            "左转",
            "右转",
        ),
    ),
    Intent("weather", CAT_QUERY, 72, ("天气预报", "多少度", "天气")),
    Intent("news", CAT_QUERY, 72, ("头条", "热点", "新闻")),
    Intent("alarm", CAT_ASSIST, 70, ("定个闹钟", "定闹钟", "闹钟")),
    Intent("countdown", CAT_ASSIST, 68, ("倒计时", "计时")),
    Intent("remind", CAT_ASSIST, 66, ("到点提醒", "提醒我", "事件提醒", "分钟后")),
    Intent(
        "memory_query",
        CAT_ASSIST,
        55,
        ("我喜欢什么", "记住了什么", "你记得什么", "记得什么", "我的档案"),
    ),
    Intent(
        "memory_forget",
        CAT_ASSIST,
        52,
        ("忘掉", "忘记", "删掉记忆", "别记了"),
    ),
    Intent("remember", CAT_ASSIST, 50, ("别忘了", "以后叫", "我喜欢", "记住", "记得")),
    Intent("photo", CAT_FUN, 45, ("拍一张", "照张相", "照相", "拍照")),
    Intent(
        "music_stop",
        CAT_FUN,
        42,
        (
            "关掉音乐",
            "关闭音乐",
            "停止音乐",
            "停止播放",
            "暂停音乐",
            "停音乐",
            "音乐停",
            "别放了",
            "别放音乐",
            "关掉歌",
            "停止播放音乐",
        ),
    ),
    Intent("music_random", CAT_FUN, 40, ("随机播放", "随便放", "乱序播放")),
    Intent("music_named", CAT_FUN, 40, ("播放歌曲", "放一首", "播放")),
    Intent(
        "music_play",
        CAT_FUN,
        40,
        ("播放音乐", "来首歌", "放点音乐", "来点音乐", "放些音乐", "放音乐", "听歌", "放歌"),
    ),
)


def _compact(text: str) -> str:
    return "".join((text or "").split())


def _by_name(name: str) -> Intent:
    for intent in INTENTS:
        if intent.name == name:
            return intent
    raise KeyError(name)


def _soft_status(compact: str) -> Intent | None:
    """Oral variants that pure keyword lists miss (怎样 vs 怎么样, 检查相机…)."""
    if any(k in compact for k in ("相机", "摄像头", "镜头")):
        if any(
            k in compact
            for k in (
                "怎样",
                "怎么样",
                "如何",
                "检查",
                "看看",
                "状态",
                "好不好",
                "能用",
                "坏了",
                "可用",
                "正常",
            )
        ):
            return _by_name("status_camera")
    if "急停" in compact and any(
        k in compact for k in ("吗", "呢", "没有", "是否", "状态", "开着", "拉开")
    ):
        return _by_name("status_estop")
    return None


def match_intent(text: str) -> Intent | None:
    compact = _compact(text)
    if not compact:
        return None
    best: tuple[int, int, Intent] | None = None
    for intent in INTENTS:
        for word in intent.keywords:
            if word and word in compact:
                key = (len(word), intent.weight)
                if best is None or key > (best[0], best[1]):
                    best = (len(word), intent.weight, intent)
    if best is not None:
        return best[2]
    return _soft_status(compact)


def named_music_query(text: str) -> str:
    compact = _compact(text)
    for prefix in ("播放歌曲", "放一首", "播放", "放歌"):
        if prefix in compact:
            rest = compact.split(prefix, 1)[-1]
            rest = rest.replace("这首歌", "").replace("那首歌", "").replace("音乐", "").replace("歌", "")
            return rest.strip()
    return ""
