# -*- coding: utf-8 -*-
from __future__ import annotations

import hashlib
import json
import os
import secrets
from pathlib import Path

DEFAULT_PATH = Path("/opt/personal_robot/config/remote_auth.json")
ITER = 200_000


def load_auth(path: Path = DEFAULT_PATH) -> dict:
    if not path.is_file():
        raise FileNotFoundError(f"missing {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    for key in ("username", "password_salt", "password_hash"):
        if key not in data:
            raise ValueError(f"auth file missing {key}")
    data.setdefault("heartbeat_timeout_s", 8)
    return data


def hash_password(password: str, salt_hex: str | None = None) -> tuple[str, str]:
    salt = bytes.fromhex(salt_hex) if salt_hex else os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, ITER)
    return salt.hex(), digest.hex()


def verify_password(data: dict, username: str, password: str) -> bool:
    if username != data["username"]:
        return False
    salt, expect = hash_password(password, data["password_salt"])
    return secrets.compare_digest(expect, data["password_hash"])


def write_auth(path: Path, username: str, password: str, heartbeat_timeout_s: int = 8) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    salt, pw_hash = hash_password(password)
    body = {
        "username": username,
        "password_salt": salt,
        "password_hash": pw_hash,
        "heartbeat_timeout_s": heartbeat_timeout_s,
    }
    path.write_text(json.dumps(body, indent=2) + "\n", encoding="utf-8")
    os.chmod(path, 0o600)
