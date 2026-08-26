const board = document.querySelector("#group-board");
const status = document.querySelector("#status");
const count = document.querySelector("#app-count");
const dialog = document.querySelector("#app-dialog");
const form = document.querySelector("#app-form");
const formError = document.querySelector("#form-error");
const credentialNote = document.querySelector("#credential-note");
const clearCredentialsRow = document.querySelector("#clear-credentials-row");
const shell = document.querySelector("#shell");
const sidebarToggle = document.querySelector("#toggle-sidebar");
const groupSelect = document.querySelector("#app-group");
let apps = [];
let groups = [];
let launchTimeout;
let draggedAppId = null;
let draggedGroupId = null;
let suppressLaunch = false;
const BRIDGE_RECOVERY_KEY = "local-sso-bridge-recovery";
const PENDING_LAUNCH_KEY = "local-sso-pending-launch";

function setStatus(message, isError = false) {
  status.textContent = message;
  status.classList.toggle("error", isError);
}

function hostOf(url) {
  try { return new URL(url).host; } catch { return url; }
}

function closeMenus() {
  document.querySelectorAll(".action-menu.open").forEach((menu) => menu.classList.remove("open"));
  document.querySelectorAll(".more-button[aria-expanded='true']").forEach((button) => button.setAttribute("aria-expanded", "false"));
}

function launch(app) {
  if (suppressLaunch) return;
  clearTimeout(launchTimeout);
  setStatus(`正在打开 ${app.name}…`);
  window.postMessage({ source: "local-sso-portal", kind: "launch", appId: app.id }, window.location.origin);
  launchTimeout = window.setTimeout(() => {
    if (!sessionStorage.getItem(BRIDGE_RECOVERY_KEY)) {
      sessionStorage.setItem(BRIDGE_RECOVERY_KEY, "1");
      sessionStorage.setItem(PENDING_LAUNCH_KEY, app.id);
      setStatus("扩展连接已过期，正在刷新并重试…");
      window.location.reload();
      return;
    }
    sessionStorage.removeItem(BRIDGE_RECOVERY_KEY);
    sessionStorage.removeItem(PENDING_LAUNCH_KEY);
    setStatus("未检测到浏览器扩展响应。请在 Edge/Chrome 扩展页加载并启用 Local SSO Portal，然后刷新本页。", true);
  }, 3500);
}

function createSystemCard(app) {
  const card = document.createElement("article");
  card.className = "app-card";
  card.draggable = true;
  card.style.setProperty("--card-color", app.color);
  card.addEventListener("dragstart", (event) => {
    draggedAppId = app.id;
    suppressLaunch = true;
    card.classList.add("dragging");
    event.dataTransfer.effectAllowed = "move";
    event.dataTransfer.setData("text/plain", `app:${app.id}`);
  });
  card.addEventListener("dragend", () => {
    card.classList.remove("dragging");
    draggedAppId = null;
    window.setTimeout(() => { suppressLaunch = false; }, 0);
  });

  const open = document.createElement("button");
  open.className = "card-open";
  open.type = "button";
  open.title = `打开 ${app.name}`;
  open.addEventListener("click", () => launch(app));
  const avatar = document.createElement("span");
  avatar.className = "app-avatar";
  avatar.textContent = app.avatar;
  const name = document.createElement("strong");
  name.className = "app-name";
  name.textContent = app.name;
  const host = document.createElement("span");
  host.className = "app-url";
  host.textContent = hostOf(app.url);
  const credentials = document.createElement("div");
  credentials.className = "app-credentials";
  [["账号", app.hasUsername ? "已保存" : ""], ["密码", app.passwordMasked]].forEach(([label, value]) => {
    if (!value) return;
    const row = document.createElement("span");
    const key = document.createElement("b");
    const content = document.createElement("em");
    key.textContent = `${label}:`;
    content.textContent = value;
    row.append(key, content);
    credentials.append(row);
  });
  open.append(avatar, name, host, credentials);

  const actions = document.createElement("div");
  actions.className = "card-actions";
  const more = document.createElement("button");
  more.className = "more-button";
  more.type = "button";
  more.textContent = "⋯";
  more.setAttribute("aria-label", `管理 ${app.name}`);
  more.setAttribute("aria-expanded", "false");
  const menu = document.createElement("div");
  menu.className = "action-menu";
  menu.setAttribute("role", "menu");
  const edit = document.createElement("button");
  edit.type = "button";
  edit.textContent = "修改";
  edit.addEventListener("click", () => openEditor(app));
  const remove = document.createElement("button");
  remove.type = "button";
  remove.className = "delete-action";
  remove.textContent = "删除";
  remove.addEventListener("click", () => deleteApp(app));
  menu.append(edit, remove);
  more.addEventListener("click", (event) => {
    event.stopPropagation();
    const opening = !menu.classList.contains("open");
    closeMenus();
    menu.classList.toggle("open", opening);
    more.setAttribute("aria-expanded", String(opening));
  });
  actions.append(more, menu);
  card.append(open, actions);
  return card;
}

function createGroupBlock(group) {
  const section = document.createElement("section");
  section.className = "system-group";
  section.dataset.groupId = group.id;
  section.style.setProperty("--group-color", group.color);
  const header = document.createElement("header");
  header.className = "group-header";
  header.draggable = true;
  header.title = "拖动此标题可调整区块顺序";
  const heading = document.createElement("h3");
  heading.textContent = group.name;
  const meta = document.createElement("span");
  meta.className = "group-meta";
  meta.textContent = `${apps.filter((app) => app.groupId === group.id).length} 个系统  ⠿`;
  header.append(heading, meta);
  header.addEventListener("dragstart", (event) => {
    draggedGroupId = group.id;
    event.dataTransfer.effectAllowed = "move";
    event.dataTransfer.setData("text/plain", `group:${group.id}`);
    section.classList.add("group-dragging");
  });
  header.addEventListener("dragend", () => {
    draggedGroupId = null;
    section.classList.remove("group-dragging");
  });

  const grid = document.createElement("div");
  grid.className = "app-grid";
  const members = apps.filter((app) => app.groupId === group.id);
  if (members.length) grid.append(...members.map(createSystemCard));
  else {
    const empty = document.createElement("p");
    empty.className = "group-empty";
    empty.textContent = "将系统卡片拖到这里";
    grid.append(empty);
  }
  section.addEventListener("dragover", (event) => {
    if (!draggedAppId && (!draggedGroupId || draggedGroupId === group.id)) return;
    event.preventDefault();
    section.classList.add("drop-target");
  });
  section.addEventListener("dragleave", (event) => {
    if (!section.contains(event.relatedTarget)) section.classList.remove("drop-target");
  });
  section.addEventListener("drop", async (event) => {
    event.preventDefault();
    section.classList.remove("drop-target");
    if (draggedAppId) await moveApp(draggedAppId, group.id);
    if (draggedGroupId && draggedGroupId !== group.id) await reorderGroups(draggedGroupId, group.id);
  });
  section.append(header, grid);
  return section;
}

function renderBoard() {
  count.textContent = apps.length;
  board.replaceChildren(...groups.map(createGroupBlock));
}

function populateGroupSelect(selectedGroupId) {
  groupSelect.replaceChildren(...groups.map((group) => {
    const option = document.createElement("option");
    option.value = group.id;
    option.textContent = group.name;
    return option;
  }));
  groupSelect.value = selectedGroupId || groups.find((group) => group.id === "uncategorized")?.id || groups[0]?.id || "";
}

function openEditor(app = null) {
  closeMenus();
  form.reset();
  formError.textContent = "";
  document.querySelector("#app-id").value = app?.id || "";
  document.querySelector("#app-name").value = app?.name || "";
  document.querySelector("#app-url").value = app?.url || "";
  document.querySelector("#app-avatar").value = app?.avatar || "";
  document.querySelector("#app-color").value = app?.color || "#d3552d";
  populateGroupSelect(app?.groupId);
  document.querySelector("#dialog-kicker").textContent = app ? "EDIT LINK" : "NEW LINK";
  document.querySelector("#dialog-title").textContent = app ? "修改链接" : "添加链接";
  const hasCredentials = Boolean(app?.hasUsername || app?.hasPassword);
  credentialNote.textContent = hasCredentials ? "已保存；留空则不修改" : "留空则直接打开页面";
  clearCredentialsRow.hidden = !hasCredentials;
  document.querySelector("#clear-credentials").checked = false;
  dialog.showModal();
}

async function saveApp(event) {
  event.preventDefault();
  formError.textContent = "";
  const id = document.querySelector("#app-id").value;
  const username = document.querySelector("#app-username").value.trim();
  const password = document.querySelector("#app-password").value;
  const payload = {
    name: document.querySelector("#app-name").value,
    url: document.querySelector("#app-url").value,
    avatar: document.querySelector("#app-avatar").value,
    color: document.querySelector("#app-color").value,
    groupId: groupSelect.value,
  };
  if (id) payload.id = id;
  if (username) payload.username = username;
  if (password) payload.password = password;
  if (document.querySelector("#clear-credentials").checked) payload.clearCredentials = true;
  try {
    const response = await fetch("/api/apps", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || "保存失败");
    dialog.close();
    await loadApps();
    setStatus(`已保存 ${result.app.name}。`);
  } catch (error) { formError.textContent = error.message; }
}

async function deleteApp(app) {
  closeMenus();
  if (!window.confirm(`确定删除“${app.name}”吗？该操作会同时删除本机保存的登录信息。`)) return;
  try {
    const response = await fetch(`/api/apps/${encodeURIComponent(app.id)}`, { method: "DELETE" });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || "删除失败");
    await loadApps();
    setStatus(`已删除 ${app.name}。`);
  } catch (error) { setStatus(`删除失败：${error.message}`, true); }
}

async function moveApp(appId, groupId) {
  const app = apps.find((item) => item.id === appId);
  if (!app || app.groupId === groupId) return;
  try {
    const response = await fetch(`/api/apps/${encodeURIComponent(appId)}/move`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ groupId }) });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || "移动失败");
    await loadApps();
    setStatus(`已将 ${app.name} 移动到对应区块。`);
  } catch (error) { setStatus(`移动失败：${error.message}`, true); }
}

async function reorderGroups(sourceId, targetId) {
  const order = groups.map((group) => group.id).filter((id) => id !== sourceId);
  order.splice(order.indexOf(targetId), 0, sourceId);
  try {
    const response = await fetch("/api/groups/reorder", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ groupIds: order }) });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || "区块排序失败");
    await loadApps();
    setStatus("已调整区块顺序。");
  } catch (error) { setStatus(`区块排序失败：${error.message}`, true); }
}

async function addGroup() {
  const name = window.prompt("新区块名称，例如：测试系统");
  if (!name?.trim()) return;
  try {
    const response = await fetch("/api/groups", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ name: name.trim() }) });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || "创建区块失败");
    await loadApps();
    setStatus(`已创建区块：${result.group.name}。`);
  } catch (error) { setStatus(`创建区块失败：${error.message}`, true); }
}

async function loadApps() {
  if (window.location.protocol === "file:") {
    setStatus("请不要直接双击 index.html。请先运行本地服务，再打开 http://127.0.0.1:8765。", true);
    return;
  }
  try {
    const response = await fetch("/api/apps", { cache: "no-store" });
    if (!response.ok) throw new Error("无法读取本地配置");
    const data = await response.json();
    apps = data.apps;
    groups = data.groups;
    renderBoard();
    setStatus("拖动卡片可切换区块；拖动区块标题可调整顺序。", false);
    const pendingAppId = sessionStorage.getItem(PENDING_LAUNCH_KEY);
    if (pendingAppId) {
      sessionStorage.removeItem(PENDING_LAUNCH_KEY);
      const pendingApp = apps.find((app) => app.id === pendingAppId);
      if (pendingApp) window.setTimeout(() => launch(pendingApp), 0);
    }
  } catch (error) { setStatus("本地服务未运行。请稍后重试或检查 LocalSSOPortal 计划任务。", true); }
}

document.querySelector("#add-app").addEventListener("click", () => openEditor());
document.querySelector("#add-group").addEventListener("click", addGroup);
sidebarToggle.addEventListener("click", () => {
  const expanded = shell.classList.toggle("sidebar-expanded");
  sidebarToggle.setAttribute("aria-expanded", String(expanded));
  sidebarToggle.setAttribute("aria-label", expanded ? "收起工作台" : "展开工作台");
});
form.addEventListener("submit", saveApp);
document.querySelectorAll("[data-close-dialog]").forEach((button) => button.addEventListener("click", () => dialog.close()));
document.addEventListener("click", (event) => { if (!event.target.closest(".card-actions")) closeMenus(); });
window.addEventListener("message", (event) => {
  if (event.source !== window || event.data?.source !== "local-sso-extension") return;
  clearTimeout(launchTimeout);
  sessionStorage.removeItem(BRIDGE_RECOVERY_KEY);
  sessionStorage.removeItem(PENDING_LAUNCH_KEY);
  setStatus(event.data.message, event.data.error === true);
});

loadApps();
