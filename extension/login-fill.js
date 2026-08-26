function waitForSelector(selector, timeoutMs = 10000) {
  return new Promise((resolve, reject) => {
    const existing = document.querySelector(selector);
    if (existing) return resolve(existing);
    const observer = new MutationObserver(() => {
      const element = document.querySelector(selector);
      if (!element) return;
      observer.disconnect();
      clearTimeout(timer);
      resolve(element);
    });
    const timer = setTimeout(() => {
      observer.disconnect();
      reject(new Error(`找不到登录控件：${selector}`));
    }, timeoutMs);
    observer.observe(document.documentElement, { childList: true, subtree: true });
  });
}

function setInputValue(element, value) {
  const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value").set;
  setter.call(element, value);
  element.dispatchEvent(new Event("input", { bubbles: true }));
  element.dispatchEvent(new Event("change", { bubbles: true }));
  element.dispatchEvent(new Event("blur", { bubbles: true }));
}

function waitForEnabledSelector(selector, timeoutMs = 10000) {
  return new Promise((resolve, reject) => {
    const findEnabled = () => [...document.querySelectorAll(selector)].find((element) => !element.disabled && element.getAttribute("aria-disabled") !== "true");
    const existing = findEnabled();
    if (existing) return resolve(existing);
    const observer = new MutationObserver(() => {
      const element = findEnabled();
      if (!element) return;
      observer.disconnect();
      clearTimeout(timer);
      resolve(element);
    });
    const timer = setTimeout(() => {
      observer.disconnect();
      reject(new Error(`Login action is still disabled: ${selector}`));
    }, timeoutMs);
    observer.observe(document.documentElement, { attributes: true, childList: true, subtree: true });
  });
}

function findPreLoginEntry(login) {
  const candidates = [...document.querySelectorAll(login.preLoginSelector)];
  const expectedText = (login.preLoginText || "").trim().toUpperCase();
  return candidates.find((element) => !expectedText || (element.textContent || "").toUpperCase().includes(expectedText));
}

function waitForPreLoginEntry(login, timeoutMs = 15000) {
  return new Promise((resolve) => {
    const existing = findPreLoginEntry(login);
    if (existing) return resolve(existing);
    const observer = new MutationObserver(() => {
      const entry = findPreLoginEntry(login);
      if (!entry) return;
      observer.disconnect();
      clearTimeout(timer);
      resolve(entry);
    });
    const timer = setTimeout(() => {
      observer.disconnect();
      resolve(null);
    }, timeoutMs);
    observer.observe(document.documentElement, { childList: true, subtree: true });
  });
}

async function fillLogin() {
  const pending = await chrome.runtime.sendMessage({ kind: "getPendingLogin" });
  if (!pending?.ok || !pending.login) return;
  const { login } = pending;
  if (login.preLoginSelector) {
    const entry = await waitForPreLoginEntry(login);
    if (entry) {
      entry.click();
      return;
    }
    if (login.preLoginOnly) return;
  }
  const [usernameInput, passwordInput] = await Promise.all([
    login.usernameSelector ? waitForSelector(login.usernameSelector) : Promise.resolve(null),
    login.passwordSelector ? waitForSelector(login.passwordSelector) : Promise.resolve(null),
  ]);
  const result = await chrome.runtime.sendMessage({ kind: "requestCredential" });
  if (!result?.ok) return;
  if (usernameInput && result.username) setInputValue(usernameInput, result.username);
  if (passwordInput && result.password) setInputValue(passwordInput, result.password);
  if (login.autoSubmit) (await waitForEnabledSelector(login.submitSelector)).click();
}

fillLogin().catch((error) => console.warn("Local SSO could not fill this login page:", error.message));
