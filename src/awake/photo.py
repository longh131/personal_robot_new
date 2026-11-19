# -*- coding: utf-8 -*-
"""AWAKE still capture. Own files, no remote import."""

from __future__ import annotations

import logging
import subprocess
from datetime import datetime
from pathlib import Path

from settings import robot_get

log = logging.getLogger("awake.photo")
RPICAM = Path("/opt/personal_robot/scripts/rpicam.sh")


def photos_dir() -> Path:
    raw = robot_get("media", "awake_photos", default="/opt/personal_robot/data/media/awake/photos")
    path = Path(str(raw or "/opt/personal_robot/data/media/awake/photos"))
    path.mkdir(parents=True, exist_ok=True)
    return path


def take_photo() -> Path:
    dest = photos_dir() / datetime.now().strftime("%Y%m%d-%H%M%S.jpg")
    proc = subprocess.run(
        [str(RPICAM), "rpicam-jpeg", "-n", "-t", "2000", "-o", str(dest)],
        capture_output=True,
        text=True,
        timeout=10,
    )
    if proc.returncode != 0 or not dest.is_file() or dest.stat().st_size < 100:
        raise RuntimeError(proc.stderr.strip() or "拍照失败")
    log.info("awake photo %s", dest)
    return dest
