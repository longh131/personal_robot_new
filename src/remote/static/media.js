const authPill = document.getElementById("authPill");
const mediaMsg = document.getElementById("mediaMsg");
const catTabs = document.getElementById("catTabs");
const fileList = document.getElementById("fileList");
const listTitle = document.getElementById("listTitle");
const listCount = document.getElementById("listCount");
const emptyHint = document.getElementById("emptyHint");
const previewCard = document.getElementById("previewCard");
const previewBody = document.getElementById("previewBody");

let currentCat = "";
let selected = null;

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

function banner(text) {
  mediaMsg.hidden = false;
  mediaMsg.textContent = text;
}

function fmtSize(n) {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}

function fmtTime(sec) {
  try {
    return new Date(sec * 1000).toLocaleString();
  } catch {
    return "-";
  }
}

function fileUrl(cat, name, download) {
  const q = new URLSearchParams({ cat, name });
  if (download) q.set("download", "1");
  return `/api/media/file?${q.toString()}`;
}

function clearPreview() {
  selected = null;
  previewCard.hidden = true;
  previewBody.innerHTML = "";
}

function showPreview(item) {
  selected = item;
  previewCard.hidden = false;
  previewBody.innerHTML = "";
  const url = fileUrl(currentCat, item.name, false);
  if (item.kind === "image") {
    const img = document.createElement("img");
    img.src = url;
    img.alt = item.name;
    previewBody.appendChild(img);
  } else if (item.kind === "video") {
    const v = document.createElement("video");
    v.controls = true;
    v.src = url;
    previewBody.appendChild(v);
  } else if (item.kind === "audio") {
    const a = document.createElement("audio");
    a.controls = true;
    a.src = url;
    previewBody.appendChild(a);
  } else {
    const p = document.createElement("p");
    p.className = "muted";
    p.textContent = "此类型请下载查看。";
    previewBody.appendChild(p);
  }
  const meta = document.createElement("p");
  meta.className = "muted";
  meta.textContent = `${item.name} · ${fmtSize(item.size)} · ${fmtTime(item.mtime)}`;
  previewBody.appendChild(meta);
}

async function loadList(cat) {
  currentCat = cat;
  clearPreview();
  const { res, data } = await api(`/api/media/list?cat=${encodeURIComponent(cat)}`);
  if (!res.ok) {
    banner(data.error || "加载失败");
    return;
  }
  listCount.textContent = `${data.count || 0} 个`;
  fileList.innerHTML = "";
  const items = data.items || [];
  emptyHint.hidden = items.length > 0;
  for (const item of items) {
    const row = document.createElement("button");
    row.type = "button";
    row.className = "file-row";
    row.innerHTML = `<span class="file-name">${item.name}</span>`
      + `<span class="file-meta">${item.kind} · ${fmtSize(item.size)}</span>`;
    row.onclick = () => {
      for (const el of fileList.querySelectorAll(".file-row")) el.classList.remove("on");
      row.classList.add("on");
      showPreview(item);
    };
    fileList.appendChild(row);
  }
}

async function loadCategories() {
  const { res, data } = await api("/api/media/categories");
  if (!res.ok) {
    authPill.textContent = "未登录";
    authPill.classList.remove("remote");
    banner("请先在主控页登录 REMOTE，再打开本页。");
    return false;
  }
  authPill.textContent = "已登录";
  authPill.classList.add("remote");
  catTabs.innerHTML = "";
  const cats = data.categories || [];
  for (const c of cats) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "cat-tab";
    btn.textContent = `${c.label} (${c.count})`;
    btn.dataset.id = c.id;
    btn.onclick = () => {
      for (const el of catTabs.querySelectorAll(".cat-tab")) el.classList.remove("on");
      btn.classList.add("on");
      loadList(c.id);
    };
    catTabs.appendChild(btn);
  }
  if (cats.length) {
    const first = catTabs.querySelector(".cat-tab");
    if (first) {
      first.classList.add("on");
      await loadList(cats[0].id);
    }
  }
  return true;
}

document.getElementById("btnClose").onclick = () => window.close();

document.getElementById("btnDownload").onclick = () => {
  if (!selected || !currentCat) return;
  window.open(fileUrl(currentCat, selected.name, true), "_blank");
};

document.getElementById("btnDelete").onclick = async () => {
  if (!selected || !currentCat) return;
  if (!confirm(`确定删除 ${selected.name}？`)) return;
  const name = selected.name;
  const { res, data } = await api("/api/media/delete", { cat: currentCat, name });
  if (!res.ok) {
    banner(data.error || "删除失败");
    return;
  }
  banner(`已删除 ${name}`);
  await loadCategories();
};

setInterval(() => {
  api("/api/heartbeat", {}).catch(() => {});
}, 10000);

loadCategories();
