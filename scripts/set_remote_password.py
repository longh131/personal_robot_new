#!/usr/bin/env python3
"""Write config/remote_auth.json (chmod 600). Not committed."""

from __future__ import annotations

import argparse
import getpass
import sys
from pathlib import Path

sys.path.insert(0, str(Path("/opt/personal_robot/src")))
from remote.auth import DEFAULT_PATH, write_auth


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--user", default="andylong")
    p.add_argument("--password", default="")
    args = p.parse_args()
    pw = args.password or getpass.getpass("password: ")
    if len(pw) < 8:
        print("password too short", file=sys.stderr)
        return 1
    write_auth(DEFAULT_PATH, args.user, pw)
    print(f"wrote {DEFAULT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
