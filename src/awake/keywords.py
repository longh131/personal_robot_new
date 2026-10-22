# -*- coding: utf-8 -*-
"""Build Sherpa keywords.txt from identity.json wake_words."""

from __future__ import annotations

import logging
from pathlib import Path

from settings import load_identity

log = logging.getLogger("awake.keywords")
MODEL_DIR = Path("/opt/personal_robot/data/models/wake")
KEYWORDS_PATH = MODEL_DIR / "keywords.txt"


def _boost(phrase: str) -> tuple[str, str]:
    n = len(phrase)
    if n <= 2:
        return "2.0", "0.20"
    if n <= 4:
        return "1.8", "0.20"
    return "1.6", "0.22"


def _ppinyin(phrase: str) -> list[str]:
    from pypinyin import pinyin
    from pypinyin.contrib.tone_convert import to_finals_tone, to_initials

    out: list[str] = []
    for item in pinyin(phrase):
        syl = item[0]
        initial = to_initials(syl, strict=False)
        final = to_finals_tone(syl, strict=False)
        if initial == "" and final == "":
            out.append(syl)
            continue
        if initial:
            out.append(initial)
        if final:
            out.append(final)
    return out


def write_keywords(path: Path = KEYWORDS_PATH) -> Path:
    ident = load_identity()
    phrases: list[str] = []
    seen: set[str] = set()
    for raw in ident.get("wake_words") or []:
        phrase = str(raw).strip().replace(" ", "")
        if not phrase or phrase in seen:
            continue
        seen.add(phrase)
        phrases.append(phrase)
    if not phrases:
        raise ValueError("identity.json wake_words is empty")
    lines: list[str] = []
    for phrase in phrases:
        tokens = _ppinyin(phrase)
        if not tokens:
            log.warning("skip wake word with no pinyin: %s", phrase)
            continue
        boost, th = _boost(phrase)
        lines.append(f"{' '.join(tokens)} :{boost} #{th} @{phrase}")
    if not lines:
        raise ValueError("no valid wake_words to compile")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    log.info("kws from identity.json n=%s file=%s", len(lines), path)
    return path
