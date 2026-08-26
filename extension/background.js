const LOCAL_API = "http://127.0.0.1:8765/api";

async function getApps() {
  const response = await fetch(`${LOCAL_API}/apps`, { cache: "no-store" });
  if (!response.ok) throw new Error("本地门户服务未运行");
  return (await response.json()).apps;
}

async function pendingApp(tabId) {
  const key = `pending:${tabId}`;
  const pending = await chrome.storage.session.get(key);
  const appId = pending[key];
  if (!appId) throw new Error("此页面不是从本地门户启动的");
  const app = (await getApps()).find((item) => item.id === appId);
  if (!app) throw new Error("未找到系统配置");
  return { key, app };
}

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.kind === "launch") {
    (async () => {
      const app = (await getApps()).find((item) => item.id === message.appId);
      if (!app) throw new Error("未找到系统配置");
      const tab = await chrome.tabs.create({ url: "about:blank", active: true });
      if (!tab?.id) throw new Error("Unable to create a browser tab");
      await chrome.storage.session.set({ [`pending:${tab.id}`]: app.id });
      await chrome.tabs.update(tab.id, { url: app.url });
      sendResponse({ ok: true, message: `已打开 ${app.name}。` });
    })().catch((error) => sendResponse({ ok: false, error: error.message }));
    return true;
  }

  if (message.kind === "getPendingLogin" && sender.tab?.id !== undefined) {
    pendingApp(sender.tab.id)
      .then(({ app }) => sendResponse({ ok: true, login: app.login || null }))
      .catch((error) => sendResponse({ ok: false, error: error.message }));
    return true;
  }

  if (message.kind === "requestCredential" && sender.tab?.id !== undefined) {
    (async () => {
      const { key, app } = await pendingApp(sender.tab.id);
      if (!app.login) throw new Error("此链接没有登录信息");
      await chrome.storage.session.remove(key);
      const response = await fetch(`${LOCAL_API}/credentials/${encodeURIComponent(app.id)}`, { cache: "no-store" });
      if (!response.ok) throw new Error("无法读取本地凭据");
      sendResponse({ ok: true, ...(await response.json()) });
    })().catch((error) => sendResponse({ ok: false, error: error.message }));
    return true;
  }
});
