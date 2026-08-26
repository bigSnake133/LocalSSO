window.addEventListener("message", (event) => {
  if (event.source !== window || event.origin !== "http://127.0.0.1:8765") return;
  if (event.data?.source !== "local-sso-portal" || event.data.kind !== "launch") return;

  chrome.runtime.sendMessage({ kind: "launch", appId: event.data.appId }, (result) => {
    // Read lastError inside the callback so Chrome reports the real bridge failure.
    const runtimeError = chrome.runtime.lastError?.message;
    const message = runtimeError
      ? `启动失败：${runtimeError}`
      : result?.ok
        ? result.message
        : `启动失败：${result?.error || "浏览器扩展没有响应"}`;
    window.postMessage(
      { source: "local-sso-extension", message, error: Boolean(runtimeError) || result?.ok !== true },
      "http://127.0.0.1:8765",
    );
  });
});
