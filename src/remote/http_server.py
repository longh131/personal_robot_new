# -*- coding: utf-8 -*-
"""REMOTE HTTP on 127.0.0.1 only. Stdlib, no Flask."""

from __future__ import annotations

import json
import logging
import queue
import secrets
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse
from runtime.events import Event
from runtime.machine import Machine, Mode

from . import gimbal, media_library, ros_bridge
from .auth import load_auth, verify_password
from .media import MediaSession
from .rtc import RtcSession

log = logging.getLogger("remote.http")
STATIC = Path(__file__).resolve().parent / "static"


class RemoteGate:
    def __init__(self, machine: Machine, events: queue.Queue[Event], auth: dict) -> None:
        self.machine = machine
        self.events = events
        self.auth = auth
        self.token: str | None = None
        self.last_hb = 0.0
        self.lock = threading.Lock()
        self.media = MediaSession()
        self.rtc = RtcSession(self.media.camera.latest_jpeg)
        self.mic = None

    def timeout_s(self) -> float:
        from settings import robot_get

        return max(8.0, float(robot_get("remote", "heartbeat_timeout_s", default=30) or 30))

    def check_timeout(self) -> None:
        with self.lock:
            if self.machine.mode != Mode.REMOTE or self.token is None:
                return
            if time.monotonic() - self.last_hb <= self.timeout_s():
                return
        log.warning("remote heartbeat timeout")
        self._leave()

    def _leave(self) -> None:
        with self.lock:
            self.token = None
        try:
            self.rtc.close()
        except Exception as exc:
            log.warning("rtc leave: %s", exc)
        self.media.stop_all()
        ros_bridge.drive_stop()
        gimbal.shutdown(home=True)
        self.events.put(Event.EXIT_TO_IDLE)
        ros_bridge.mode_cmd("IDLE")

    def login(self, username: str, password: str) -> tuple[int, dict]:
        if not verify_password(self.auth, username, password):
            return 401, {"ok": False, "error": "bad_credentials"}
        if self.machine.estop:
            return 403, {"ok": False, "error": "estop_latched"}
        if self.machine.mode == Mode.FAULT:
            return 409, {"ok": False, "error": "fault_locked"}
        # AWAKE↔REMOTE 不得互抢：须先退出 AWAKE 回 IDLE，再登录 REMOTE
        if self.machine.mode == Mode.AWAKE:
            return 409, {"ok": False, "error": "awake_busy"}
        token = secrets.token_urlsafe(24)
        with self.lock:
            self.token = token
            self.last_hb = time.monotonic()
        if self.mic is not None:
            self.mic.set_paused(True)
        self.machine.apply(Event.REMOTE_LOGIN)
        self.events.put(Event.REMOTE_LOGIN)
        # skill_pub first, then MODE via ros2 pub --once (reliable)
        ros_bridge.ensure_skill_pub()
        ros_bridge.set_speed_scale(1.0)
        ros_bridge.mode_cmd("REMOTE")
        self.media.start_preview()
        gimbal.start()
        return 200, {"ok": True, "token": token, "user": username}

    def logout(self) -> None:
        self._leave()

    def heartbeat(self, token: str) -> bool:
        with self.lock:
            if token != self.token:
                return False
            self.last_hb = time.monotonic()
            return True

    def session_info(self) -> dict | None:
        with self.lock:
            if self.token is None:
                return None
            left = self.timeout_s() - (time.monotonic() - self.last_hb)
            return {
                "hb_left_s": max(0.0, round(left, 1)),
                "timeout_s": round(self.timeout_s(), 1),
                "exclusive": True,
            }


def _make_handler(gate: RemoteGate):
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, fmt: str, *args: object) -> None:
            log.info("%s " + fmt, self.address_string(), *args)

        def _secure(self) -> bool:
            return self.headers.get("X-Forwarded-Proto", "").lower() == "https"

        def _cookie_token(self) -> str:
            raw = self.headers.get("Cookie", "")
            for part in raw.split(";"):
                k, _, v = part.strip().partition("=")
                if k == "session":
                    return v
            return self.headers.get("X-Session", "")

        def _json(self, code: int, body: dict, set_cookie: str | None = None) -> None:
            data = json.dumps(body).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            if set_cookie is not None:
                bits = [f"session={set_cookie}", "HttpOnly", "Path=/", "SameSite=Lax"]
                if self._secure():
                    bits.append("Secure")
                self.send_header("Set-Cookie", "; ".join(bits))
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _read_json(self) -> dict:
            n = int(self.headers.get("Content-Length", "0") or 0)
            raw = self.rfile.read(n) if n else b"{}"
            try:
                return json.loads(raw.decode("utf-8") or "{}")
            except json.JSONDecodeError:
                return {}

        def _static(self, name: str, ctype: str) -> None:
            path = (STATIC / name).resolve()
            if not str(path).startswith(str(STATIC.resolve())) or not path.is_file():
                self.send_error(404)
                return
            data = path.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)

        def _authed(self) -> bool:
            tok = self._cookie_token()
            return bool(tok) and tok == gate.token

        def _send_file(self, path: Path, ctype: str, *, download: bool = False) -> None:
            data = path.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            if download:
                self.send_header("Content-Disposition", f'attachment; filename="{path.name}"')
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            path = parsed.path
            qs = parse_qs(parsed.query)
            if path in ("/", "/index.html"):
                return self._static("index.html", "text/html; charset=utf-8")
            if path in ("/media", "/media.html"):
                return self._static("media.html", "text/html; charset=utf-8")
            if path == "/static/app.js":
                return self._static("app.js", "application/javascript; charset=utf-8")
            if path == "/static/media.js":
                return self._static("media.js", "application/javascript; charset=utf-8")
            if path == "/static/styles.css":
                return self._static("styles.css", "text/css; charset=utf-8")
            if path == "/api/state":
                authed = self._authed()
                battery = None
                if authed:
                    try:
                        from awake.tools import read_battery

                        pct, state = read_battery()
                        battery = {"pct": pct, "state": state}
                    except Exception:
                        battery = None
                body = {
                    "ok": True,
                    "authed": authed,
                    "mode": gate.machine.mode,
                    "estop": gate.machine.estop,
                    "motion": True,
                    "drive": ros_bridge.motion_limits(),
                    "battery": battery,
                    "media": gate.media.status() if authed else None,
                    "gimbal": gimbal.status(),
                    "session": gate.session_info() if authed else None,
                    "obstacle": ros_bridge.obstacle_status() if authed else None,
                }
                return self._json(200, body)
            if path == "/api/preview.jpg":
                if not self._authed():
                    self.send_error(401)
                    return
                jpeg = gate.media.camera.latest_jpeg()
                if not jpeg:
                    self.send_error(503)
                    return
                self.send_response(200)
                self.send_header("Content-Type", "image/jpeg")
                self.send_header("Content-Length", str(len(jpeg)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(jpeg)
                return
            if path == "/api/media/categories":
                if not self._authed():
                    return self._json(401, {"ok": False, "error": "unauthorized"})
                return self._json(200, media_library.list_categories())
            if path == "/api/media/list":
                if not self._authed():
                    return self._json(401, {"ok": False, "error": "unauthorized"})
                cat = unquote((qs.get("cat") or [""])[0])
                out = media_library.list_category(cat)
                return self._json(200 if out.get("ok") else 404, out)
            if path == "/api/media/file":
                if not self._authed():
                    self.send_error(401)
                    return
                cat = unquote((qs.get("cat") or [""])[0])
                name = unquote((qs.get("name") or [""])[0])
                download = (qs.get("download") or ["0"])[0] in ("1", "true", "yes")
                file_path = media_library.resolve_file(cat, name)
                if file_path is None:
                    self.send_error(404)
                    return
                return self._send_file(
                    file_path,
                    media_library.content_type(file_path),
                    download=download,
                )
            self.send_error(404)

        def do_POST(self) -> None:
            body = self._read_json()
            if self.path == "/api/login":
                code, out = gate.login(str(body.get("username", "")), str(body.get("password", "")))
                cookie = out.get("token") if code == 200 else ""
                return self._json(code, out, set_cookie=cookie)
            tok = self._cookie_token()
            if not tok or tok != gate.token:
                return self._json(401, {"ok": False, "error": "unauthorized"})
            if self.path == "/api/logout":
                gate.logout()
                return self._json(200, {"ok": True}, set_cookie="")
            if self.path == "/api/heartbeat":
                if not gate.heartbeat(tok):
                    return self._json(401, {"ok": False, "error": "unauthorized"})
                return self._json(
                    200,
                    {
                        "ok": True,
                        "mode": gate.machine.mode,
                        "session": gate.session_info(),
                        "obstacle": ros_bridge.obstacle_status(),
                    },
                )
            if self.path == "/api/drive/scale":
                try:
                    scale = float(body.get("scale"))
                except (TypeError, ValueError):
                    return self._json(400, {"ok": False, "error": "bad_scale"})
                limits = ros_bridge.set_speed_scale(scale)
                return self._json(200, {"ok": True, **limits})
            if self.path == "/api/estop":
                gate.machine.apply(Event.ESTOP)
                ros_bridge.drive_stop()
                gimbal.shutdown(home=False)
                ros_bridge.estop(True)
                gate.logout()
                return self._json(200, {"ok": True, "estop": True})
            if self.path == "/api/ping":
                ros_bridge.skill_ping(secrets.token_hex(4))
                return self._json(200, {"ok": True, "skill": "ping"})
            if self.path == "/api/photo":
                try:
                    path = gate.media.photo()
                except Exception as exc:
                    return self._json(500, {"ok": False, "error": str(exc)})
                return self._json(200, {"ok": True, "path": str(path)})
            if self.path == "/api/video/start":
                try:
                    path = gate.media.start_video()
                except Exception as exc:
                    return self._json(409, {"ok": False, "error": str(exc)})
                return self._json(200, {"ok": True, "path": str(path), "max_s": gate.media.video_max_s()})
            if self.path == "/api/video/stop":
                path = gate.media.stop_video()
                return self._json(200, {"ok": True, "path": str(path) if path else ""})
            if self.path == "/api/audio/start":
                try:
                    path = gate.media.start_audio()
                except Exception as exc:
                    return self._json(409, {"ok": False, "error": str(exc)})
                return self._json(200, {"ok": True, "path": str(path), "max_s": gate.media.audio_max_s()})
            if self.path == "/api/audio/stop":
                path = gate.media.stop_audio()
                return self._json(200, {"ok": True, "path": str(path) if path else ""})
            if self.path == "/api/rtc":
                try:
                    out = gate.rtc.answer(body)
                except Exception as exc:
                    return self._json(500, {"ok": False, "error": str(exc)})
                return self._json(200, out)
            if self.path == "/api/gimbal":
                if gate.machine.mode != Mode.REMOTE or gate.machine.estop:
                    gimbal.move("stop")
                    return self._json(409, {"ok": False, "error": "no_gimbal_permit"})
                return self._json(200, gimbal.move(str(body.get("dir") or "stop")))
            if self.path == "/api/drive":
                if gate.machine.mode != Mode.REMOTE or gate.machine.estop:
                    ros_bridge.drive_stop()
                    return self._json(409, {"ok": False, "error": "no_motion_permit"})
                try:
                    applied = ros_bridge.drive(
                        float(body.get("vx") or 0),
                        float(body.get("vy") or 0),
                        float(body.get("wz") or 0),
                    )
                except Exception as exc:
                    return self._json(503, {"ok": False, "error": str(exc)})
                return self._json(200, {"ok": True, **applied})
            if self.path == "/api/media/delete":
                cat = str(body.get("cat") or "")
                name = str(body.get("name") or "")
                out = media_library.delete_file(cat, name)
                return self._json(200 if out.get("ok") else 404, out)
            self.send_error(404)

    return Handler


def start(gate: RemoteGate, host: str = "127.0.0.1", port: int = 5000) -> ThreadingHTTPServer:
    httpd = ThreadingHTTPServer((host, port), _make_handler(gate))
    t = threading.Thread(target=httpd.serve_forever, name="remote-http", daemon=True)
    t.start()
    log.info("REMOTE http://%s:%s (bind local only)", host, port)
    return httpd
