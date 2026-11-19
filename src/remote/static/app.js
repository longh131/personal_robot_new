const loginView = document.getElementById("loginView");
const panelView = document.getElementById("panelView");
const loginErr = document.getElementById("loginErr");
const msg = document.getElementById("msg");

async function api(path, body) {
  const opt = { method: body ? "POST" : "GET", credentials: "same-origin", headers: {} };
  if (body) {
    opt.headers["Content-Type"] = "application/json; charset=utf-8";
    opt.body = JSON.stringify(body);
  }
  const res = await fetch(path, opt);
  const data = await res.json().catch(() => ({}));
  return { res, data };
}

function showPanel(on) {
  loginView.hidden = on;
  panelView.hidden = !on;
}

let pc = null;
let talkOn = false;
let driveTimer = null;
let driveCmd = { vx: 0, vy: 0, wz: 0 };
let driveHeld = null;
let lastRttMs = null;
let scaleSyncing = false;

function fmtDist(v) {
  if (v == null || Number.isNaN(Number(v))) return "--";
  return `${Number(v).toFixed(2)}m`;
}

function paintObstacle(obs) {
  const hint = document.getElementById("obsHint");
  const stop = document.getElementById("obsStopBanner");
  const map = { front: "obsFront", rear: "obsRear", left: "obsLeft", right: "obsRight" };
  if (!obs || obs.enabled === false) {
    if (hint) hint.textContent = obs ? "未启用" : "无数据";
    for (const id of Object.values(map)) {
      const el = document.getElementById(id);
      if (el) el.textContent = "--";
    }
    if (stop) stop.hidden = true;
    document.querySelectorAll(".obs-cell").forEach((el) => el.classList.remove("near", "hard"));
    return;
  }
  const stale = !!obs.stale_ui || !obs.fresh;
  if (hint) {
    hint.textContent = obs.blocked
      ? "已刹停"
      : stale
        ? "雷达陈旧"
        : `阈 ${obs.stop_m ?? "-"}/${obs.hard_m ?? "-"}m`;
  }
  if (stop) stop.hidden = !obs.blocked;
  const stopM = Number(obs.stop_m) || 0.45;
  const hardM = Number(obs.hard_m) || 0.3;
  for (const [dir, id] of Object.entries(map)) {
    const el = document.getElementById(id);
    const cell = el?.closest(".obs-cell");
    const v = obs[dir];
    if (el) el.textContent = fmtDist(v);
    if (!cell) continue;
    cell.classList.toggle("hard", v != null && v <= hardM);
    cell.classList.toggle("near", v != null && v > hardM && v <= stopM);
  }
}

function paintDriveLimits(d) {
  if (!d) return;
  const pct = Math.round((d.scale ?? 1) * 100);
  const slider = document.getElementById("speedScale");
  const label = document.getElementById("speedLabel");
  const hint = document.getElementById("speedHint");
  if (slider && !scaleSyncing && document.activeElement !== slider) {
    slider.value = String(pct);
  }
  if (label) label.textContent = `${pct}%`;
  if (hint) {
    hint.textContent = `有效上限 vx ${d.vx_eff ?? "-"} / vy ${d.vy_eff ?? "-"} / wz ${d.wz_eff ?? "-"}（配置 ${d.vx_max}/${d.vy_max}/${d.wz_max}）`;
  }
}

function paintSession(session) {
  const st = document.getElementById("stSession");
  const link = document.getElementById("linkPill");
  const hb = session ? `${session.hb_left_s ?? "--"}s` : "--";
  const rtt = lastRttMs != null ? `${lastRttMs}ms` : "--";
  if (st) {
    st.textContent = session
      ? `心跳剩 ${hb} / ${session.timeout_s ?? "-"}s · 单会话`
      : "-";
  }
  if (link) {
    link.textContent = `链路 ${rtt} · 心跳 ${hb}`;
    link.classList.toggle("warn", session != null && Number(session.hb_left_s) < 8);
  }
}

function paintState(s) {
  const modeEl = document.getElementById("stMode");
  if (modeEl) modeEl.textContent = s.mode;
  const estopEl = document.getElementById("stEstop");
  if (estopEl) {
    estopEl.textContent = s.estop ? "锁存（需人工）" : "否";
    estopEl.classList.toggle("estop-latched", !!s.estop);
  }
  const pill = document.getElementById("modePill");
  pill.textContent = s.mode;
  pill.classList.toggle("remote", s.mode === "REMOTE");
  const bat = s.battery;
  const batText = bat ? `${bat.pct}% ${bat.state}` : "--";
  document.getElementById("stBat").textContent = batText;
  document.getElementById("batPill").textContent = bat ? `电量 ${bat.pct}%` : "电量 --";
  const media = s.media || {};
  document.getElementById("stVidMax").textContent = media.video_max_s ? `${media.video_max_s}s` : "-";
  document.getElementById("stRecMax").textContent = media.audio_max_s ? `${media.audio_max_s}s` : "-";
  document.getElementById("btnVid").classList.toggle("on", !!media.video);
  document.getElementById("btnRec").classList.toggle("on", !!media.audio);
  document.getElementById("btnTalk").classList.toggle("on", talkOn);
  const g = s.gimbal || {};
  const gimLine = document.getElementById("stGimbal");
  if (gimLine) {
    gimLine.textContent = g.connected ? (g.dir || "stop") : (g.error || "未接入");
  }
  const d = s.drive || {};
  paintDriveLimits(d);
  paintSession(s.session);
  paintObstacle(s.obstacle);
  const mot = document.getElementById("stMotion");
  if (mot && !driveHeld) {
    mot.textContent = s.motion
      ? `按住 vx≤${d.vx_eff ?? d.vx_max ?? "-"}`
      : "未批准";
  }
}

async function refresh() {
  const { data } = await api("/api/state");
  if (!data.authed) {
    showPanel(false);
    return;
  }
  showPanel(true);
  paintState(data);
}

document.getElementById("btnLogin").onclick = async () => {
  loginErr.hidden = true;
  const { res, data } = await api("/api/login", {
    username: document.getElementById("user").value,
    password: document.getElementById("pass").value,
  });
  if (!res.ok) {
    loginErr.hidden = false;
    const err = data.error || "登录失败";
    loginErr.textContent =
      err === "awake_busy"
        ? "正在语音交互（AWAKE），请先说「再见」退出后再登录"
        : err;
    return;
  }
  showPanel(true);
  refresh();
  startRtc(false);
};

document.getElementById("btnLogout").onclick = async () => {
  releaseGim();
  releaseDrive();
  if (pc) {
    pc.close();
    pc = null;
  }
  talkOn = false;
  document.getElementById("btnTalk").classList.remove("on");
  document.getElementById("btnVid").classList.remove("on");
  document.getElementById("btnRec").classList.remove("on");
  await api("/api/logout", {});
  showPanel(false);
};

document.getElementById("btnEstop").onclick = async () => {
  if (!confirm("确认软件急停？将锁存并退出 REMOTE（非工业硬件急停）。")) return;
  releaseGim();
  releaseDrive();
  await api("/api/estop", {});
  msg.hidden = false;
  msg.textContent = "已请求软件急停并退出 REMOTE（锁存，需人工恢复）";
  showPanel(false);
};

const speedScale = document.getElementById("speedScale");
let scaleTimer = null;
speedScale?.addEventListener("input", () => {
  document.getElementById("speedLabel").textContent = `${Number(speedScale.value)}%`;
});
speedScale?.addEventListener("change", () => {
  const pct = Number(speedScale.value);
  if (scaleTimer) clearTimeout(scaleTimer);
  scaleTimer = setTimeout(async () => {
    scaleSyncing = true;
    const { res, data } = await api("/api/drive/scale", { scale: pct / 100 });
    scaleSyncing = false;
    if (!res.ok) {
      banner(data.error || "限速失败");
      return;
    }
    paintDriveLimits(data);
  }, 80);
});

document.getElementById("btnPing").onclick = async () => {
  const { res } = await api("/api/ping", {});
  msg.hidden = false;
  msg.textContent = res.ok ? "已发 ping" : "ping 失败";
};

document.getElementById("btnMedia")?.addEventListener("click", () => {
  const w = window.open("/media.html", "robot-media", "noopener,noreferrer");
  if (!w) {
    banner("浏览器拦截了弹窗，请允许后重试");
  }
});

function banner(text) {
  msg.hidden = false;
  msg.textContent = text;
}

function waitIce(peer) {
  if (peer.iceGatheringState === "complete") return Promise.resolve();
  return new Promise((resolve) => {
    const t = setTimeout(resolve, 2000);
    peer.onicegatheringstatechange = () => {
      if (peer.iceGatheringState === "complete") {
        clearTimeout(t);
        resolve();
      }
    };
  });
}

async function startRtc(withMic) {
  if (pc) {
    pc.close();
    pc = null;
  }
  talkOn = withMic;
  const live = document.getElementById("live");
  const jpg = document.getElementById("liveJpg");
  const remoteStream = new MediaStream();
  pc = new RTCPeerConnection({ iceServers: [{ urls: "stun:stun.l.google.com:19302" }] });
  pc.ontrack = (ev) => {
    if (!remoteStream.getTracks().some((t) => t.id === ev.track.id)) {
      remoteStream.addTrack(ev.track);
    }
    live.srcObject = remoteStream;
    live.muted = false;
    live.volume = 1;
    jpg.hidden = true;
    live.hidden = false;
    live.play().catch(() => {});
  };
  pc.addTransceiver("video", { direction: "recvonly" });
  pc.addTransceiver("audio", { direction: withMic ? "sendrecv" : "recvonly" });
  if (withMic) {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
    stream.getAudioTracks().forEach((t) => pc.addTrack(t, stream));
  }
  const offer = await pc.createOffer();
  await pc.setLocalDescription(offer);
  await waitIce(pc);
  const { res, data } = await api("/api/rtc", {
    sdp: pc.localDescription.sdp,
    type: pc.localDescription.type,
  });
  if (!res.ok) {
    banner("WebRTC 失败，改用静图预览");
    document.getElementById("rtcHint").textContent = "静图预览";
    fallbackJpg();
    return;
  }
  await pc.setRemoteDescription({ sdp: data.sdp, type: data.type });
  document.getElementById("rtcHint").textContent = withMic ? "通话中" : "预览已连接";
  document.getElementById("btnTalk").classList.toggle("on", withMic);
}

function fallbackJpg() {
  const live = document.getElementById("live");
  const jpg = document.getElementById("liveJpg");
  live.hidden = true;
  jpg.hidden = false;
  jpg.src = "/api/preview.jpg?t=" + Date.now();
}

document.getElementById("btnTalk").onclick = async () => {
  try {
    await startRtc(!talkOn);
  } catch (err) {
    banner(String(err));
    fallbackJpg();
  }
};

document.getElementById("btnPhoto").onclick = async () => {
  const btn = document.getElementById("btnPhoto");
  btn.classList.add("on");
  const { res, data } = await api("/api/photo", {});
  banner(res.ok ? "已拍照" : data.error || "拍照失败");
  setTimeout(() => btn.classList.remove("on"), 400);
};
document.getElementById("btnVid").onclick = async () => {
  const on = document.getElementById("btnVid").classList.contains("on");
  const { res, data } = await api(on ? "/api/video/stop" : "/api/video/start", {});
  if (!res.ok) {
    banner(data.error || "录像失败");
    return;
  }
  document.getElementById("btnVid").classList.toggle("on", !on);
  banner(on ? "录像结束" : "录像中");
};
document.getElementById("btnRec").onclick = async () => {
  const on = document.getElementById("btnRec").classList.contains("on");
  const { res, data } = await api(on ? "/api/audio/stop" : "/api/audio/start", {});
  if (!res.ok) {
    banner(data.error || "录音失败");
    return;
  }
  document.getElementById("btnRec").classList.toggle("on", !on);
  banner(on ? "录音结束" : "录音中");
};

function fsEl() {
  return document.fullscreenElement || document.webkitFullscreenElement;
}
function syncFsBtn() {
  const on = !!fsEl();
  document.getElementById("btnFs").classList.toggle("on-fs", on);
  document.getElementById("btnFs").title = on ? "缩小" : "最大化";
}
document.getElementById("btnFs").onclick = async () => {
  const stage = document.getElementById("stage");
  const live = document.getElementById("live");
  try {
    if (fsEl()) {
      if (document.exitFullscreen) await document.exitFullscreen();
      else if (document.webkitExitFullscreen) document.webkitExitFullscreen();
    } else if (stage.requestFullscreen) {
      await stage.requestFullscreen();
    } else if (stage.webkitRequestFullscreen) {
      stage.webkitRequestFullscreen();
    } else if (live.webkitEnterFullscreen) {
      live.webkitEnterFullscreen();
    }
  } catch (err) {
    banner(String(err));
  }
  syncFsBtn();
};
document.addEventListener("fullscreenchange", syncFsBtn);
document.addEventListener("webkitfullscreenchange", syncFsBtn);

let gimHeld = null;
let gimTimer = null;
const gimBtns = ["gimUp", "gimDown", "gimLeft", "gimRight", "gimStop"];

function markGim(id) {
  gimBtns.forEach((k) => document.getElementById(k)?.classList.toggle("hold", k === id));
}

async function sendGim(dir) {
  const { res, data } = await api("/api/gimbal", { dir });
  if (!res.ok) {
    banner(data.error || "云台失败");
    return;
  }
  banner(dir === "stop" ? "云台停" : dir === "home" ? "云台回中" : `云台 ${dir}`);
}

function holdGim(id, dir) {
  if (gimHeld) return;
  gimHeld = id;
  markGim(id);
  sendGim(dir);
}

function releaseGim() {
  const was = gimHeld || gimTimer;
  if (gimTimer) {
    clearInterval(gimTimer);
    gimTimer = null;
  }
  gimHeld = null;
  markGim(null);
  if (was) sendGim("stop");
}

function stopGim() {
  if (gimTimer) {
    clearInterval(gimTimer);
    gimTimer = null;
  }
  gimHeld = null;
  markGim("gimStop");
  sendGim("stop");
}

function bindGim(id, dir) {
  const el = document.getElementById(id);
  if (!el) return;
  const down = (ev) => {
    ev.preventDefault();
    ev.stopPropagation();
    if (typeof ev.button === "number" && ev.button !== 0) return;
    holdGim(id, dir);
  };
  el.addEventListener("pointerdown", down);
  el.addEventListener("touchstart", down, { passive: false });
  el.addEventListener("mousedown", down);
  el.addEventListener("contextmenu", (ev) => ev.preventDefault());
  el.addEventListener("selectstart", (ev) => ev.preventDefault());
}
bindGim("gimUp", "up");
bindGim("gimDown", "down");
bindGim("gimLeft", "left");
bindGim("gimRight", "right");
document.getElementById("gimStop")?.addEventListener("pointerdown", (ev) => {
  ev.preventDefault();
  ev.stopPropagation();
  stopGim();
});
document.getElementById("gimHome")?.addEventListener("pointerdown", (ev) => {
  ev.preventDefault();
  releaseGim();
  sendGim("home");
});
document.getElementById("gimPad")?.addEventListener("selectstart", (ev) => ev.preventDefault());

setInterval(() => {
  const jpg = document.getElementById("liveJpg");
  if (!jpg || jpg.hidden || panelView.hidden) return;
  jpg.src = "/api/preview.jpg?t=" + Date.now();
}, 1200);

setInterval(async () => {
  if (panelView.hidden) return;
  const t0 = performance.now();
  const { res, data } = await api("/api/heartbeat", {});
  lastRttMs = Math.round(performance.now() - t0);
  if (!res.ok) {
    showPanel(false);
    return;
  }
  paintSession(data.session);
  paintObstacle(data.obstacle);
  refresh();
}, 3000);

const driveBtns = ["drvFwd", "drvBack", "drvLeft", "drvRight", "drvYawL", "drvYawR", "drvStop"];

function markHold(id) {
  driveBtns.forEach((k) => document.getElementById(k)?.classList.toggle("hold", k === id));
}

function driveLabel(cmd) {
  if (!cmd.vx && !cmd.vy && !cmd.wz) return "已停发";
  if (cmd.vx > 0) return "前进";
  if (cmd.vx < 0) return "后退";
  if (cmd.vy > 0) return "左移";
  if (cmd.vy < 0) return "右移";
  if (cmd.wz > 0) return "左转";
  if (cmd.wz < 0) return "右转";
  return "转动";
}

async function sendDrive(cmd) {
  const { res, data } = await api("/api/drive", cmd);
  const mot = document.getElementById("stMotion");
  if (!res.ok) {
    banner(data.error || "发送失败");
    if (mot) mot.textContent = data.error || "发送失败";
    return;
  }
  const moving = !!(cmd.vx || cmd.vy || cmd.wz);
  const text = moving
    ? `${driveLabel(cmd)} vx=${data.vx ?? cmd.vx} wz=${data.wz ?? cmd.wz}`
    : "已停发";
  banner(text);
  if (mot) mot.textContent = moving ? driveLabel(cmd) : "按住行走";
}

function holdDrive(id, vx, vy, wz) {
  if (driveHeld === id && driveTimer) return;
  driveHeld = id;
  driveCmd = { vx, vy, wz };
  markHold(id);
  sendDrive(driveCmd);
  if (driveTimer) clearInterval(driveTimer);
  driveTimer = setInterval(() => sendDrive(driveCmd), 400);
}

function releaseDrive() {
  if (!driveHeld && !driveTimer) return;
  if (driveTimer) {
    clearInterval(driveTimer);
    driveTimer = null;
  }
  driveHeld = null;
  driveCmd = { vx: 0, vy: 0, wz: 0 };
  markHold(null);
  sendDrive(driveCmd);
}

function bindHold(id, vx, vy, wz) {
  const el = document.getElementById(id);
  if (!el) return;
  const down = (ev) => {
    ev.preventDefault();
    ev.stopPropagation();
    if (typeof ev.button === "number" && ev.button !== 0) return;
    holdDrive(id, vx, vy, wz);
  };
  el.addEventListener("pointerdown", down);
  el.addEventListener("touchstart", down, { passive: false });
  el.addEventListener("mousedown", down);
  el.addEventListener("contextmenu", (ev) => ev.preventDefault());
  el.addEventListener("selectstart", (ev) => ev.preventDefault());
}
bindHold("drvFwd", 1, 0, 0);
bindHold("drvBack", -1, 0, 0);
bindHold("drvLeft", 0, 1, 0);
bindHold("drvRight", 0, -1, 0);
bindHold("drvYawL", 0, 0, 1);
bindHold("drvYawR", 0, 0, -1);
document.getElementById("drvStop")?.addEventListener("pointerdown", (ev) => {
  ev.preventDefault();
  releaseDrive();
});
document.getElementById("drivePad")?.addEventListener("selectstart", (ev) => ev.preventDefault());
const keyMap = {
  KeyW: ["drvFwd", 1, 0, 0],
  ArrowUp: ["drvFwd", 1, 0, 0],
  KeyS: ["drvBack", -1, 0, 0],
  ArrowDown: ["drvBack", -1, 0, 0],
  KeyA: ["drvLeft", 0, 1, 0],
  ArrowLeft: ["drvLeft", 0, 1, 0],
  KeyD: ["drvRight", 0, -1, 0],
  ArrowRight: ["drvRight", 0, -1, 0],
  KeyQ: ["drvYawL", 0, 0, 1],
  KeyE: ["drvYawR", 0, 0, -1],
};
document.addEventListener("keydown", (ev) => {
  if (panelView.hidden) return;
  if (ev.repeat) return;
  if (ev.code === "Space") {
    ev.preventDefault();
    releaseDrive();
    return;
  }
  const spec = keyMap[ev.code];
  if (!spec) return;
  ev.preventDefault();
  holdDrive(...spec);
});
document.addEventListener("keyup", (ev) => {
  if (!keyMap[ev.code]) return;
  releaseDrive();
});
window.addEventListener("pointerup", () => {
  releaseGim();
  releaseDrive();
});
window.addEventListener("mouseup", () => {
  releaseGim();
  releaseDrive();
});
window.addEventListener("touchend", () => {
  releaseGim();
  releaseDrive();
});
window.addEventListener("blur", () => {
  releaseGim();
  releaseDrive();
});
document.addEventListener("visibilitychange", () => {
  if (document.hidden) {
    releaseGim();
    releaseDrive();
  }
});

refresh();
