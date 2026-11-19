# -*- coding: utf-8 -*-
"""REMOTE media gallery: list / serve / delete under known roots only."""

from __future__ import annotations

import mimetypes
from pathlib import Path

from settings import robot_get

REMOTE_ROOT = Path("/opt/personal_robot/data/media/remote")
AWAKE_ROOT = Path("/opt/personal_robot/data/media/awake")

CATEGORIES: dict[str, dict] = {
    "remote_photos": {
        "label": "REMOTE 拍照",
        "key": ("media", "photos"),
        "default": REMOTE_ROOT / "photos",
        "kinds": ("image",),
    },
    "remote_videos": {
        "label": "REMOTE 录像",
        "key": ("media", "videos"),
        "default": REMOTE_ROOT / "videos",
        "kinds": ("video",),
    },
    "remote_recordings": {
        "label": "REMOTE 录音",
        "key": ("media", "recordings"),
        "default": REMOTE_ROOT / "recordings",
        "kinds": ("audio",),
    },
    "sentry": {
        "label": "看守 sentry",
        "key": ("media", "sentry"),
        "default": REMOTE_ROOT / "sentry",
        "kinds": ("image", "video", "audio", "other"),
    },
    "awake_photos": {
        "label": "AWAKE 拍照",
        "key": ("media", "awake_photos"),
        "default": AWAKE_ROOT / "photos",
        "kinds": ("image",),
    },
    "awake_music": {
        "label": "AWAKE 音乐",
        "key": ("media", "awake_music"),
        "default": AWAKE_ROOT / "music",
        "kinds": ("audio",),
    },
}

_IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
_VIDEO_EXT = {".mp4", ".webm", ".mkv", ".avi", ".mjpeg", ".mjpg"}
_AUDIO_EXT = {".wav", ".mp3", ".ogg", ".m4a", ".flac"}


def category_ids() -> list[str]:
    return list(CATEGORIES.keys())


def category_root(cat: str) -> Path | None:
    meta = CATEGORIES.get(cat)
    if meta is None:
        return None
    section, key = meta["key"]
    raw = robot_get(section, key, default=str(meta["default"]))
    path = Path(str(raw or meta["default"])).resolve()
    path.mkdir(parents=True, exist_ok=True)
    return path


def _kind(path: Path) -> str:
    ext = path.suffix.lower()
    if ext in _IMAGE_EXT:
        return "image"
    if ext in _VIDEO_EXT:
        return "video"
    if ext in _AUDIO_EXT:
        return "audio"
    return "other"


def resolve_file(cat: str, name: str) -> Path | None:
    """Resolve name under category root; reject traversal / absolute / missing."""
    if not name or name != Path(name).name or "/" in name or "\\" in name or name in (".", ".."):
        return None
    root = category_root(cat)
    if root is None:
        return None
    path = (root / name).resolve()
    try:
        path.relative_to(root)
    except ValueError:
        return None
    if not path.is_file():
        return None
    return path


def list_category(cat: str) -> dict:
    meta = CATEGORIES.get(cat)
    if meta is None:
        return {"ok": False, "error": "unknown_category"}
    root = category_root(cat)
    assert root is not None
    items = []
    for path in root.iterdir():
        if not path.is_file():
            continue
        if path.name.startswith("."):
            continue
        kind = _kind(path)
        try:
            st = path.stat()
        except OSError:
            continue
        items.append(
            {
                "name": path.name,
                "kind": kind,
                "size": st.st_size,
                "mtime": int(st.st_mtime),
            }
        )
    items.sort(key=lambda x: x["mtime"], reverse=True)
    return {
        "ok": True,
        "category": cat,
        "label": meta["label"],
        "count": len(items),
        "items": items,
    }


def list_categories() -> dict:
    cats = []
    for cid, meta in CATEGORIES.items():
        info = list_category(cid)
        cats.append(
            {
                "id": cid,
                "label": meta["label"],
                "count": info.get("count", 0),
            }
        )
    return {"ok": True, "categories": cats}


def delete_file(cat: str, name: str) -> dict:
    path = resolve_file(cat, name)
    if path is None:
        return {"ok": False, "error": "not_found"}
    try:
        path.unlink()
    except OSError as exc:
        return {"ok": False, "error": str(exc)}
    return {"ok": True, "deleted": name}


def content_type(path: Path) -> str:
    ctype, _ = mimetypes.guess_type(str(path))
    if ctype:
        return ctype
    ext = path.suffix.lower()
    if ext in (".mjpeg", ".mjpg"):
        return "video/x-motion-jpeg"
    return "application/octet-stream"
