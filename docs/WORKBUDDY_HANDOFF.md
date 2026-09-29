# WorkBuddy 接手说明：LocalSSO

## 接手顺序

1. 先阅读本文件。
2. 再阅读 `README.md`、`docs/ENGINEERING_HANDOFF.md` 和 `docs/DEPLOYMENT.md`。
3. 运行测试后再修改代码。

## 项目目标

LocalSSO 是 Windows 单用户本地登录工作台：Python 回环服务提供门户和 API，Chrome/Edge Manifest V3 扩展在用户从门户点击应用后打开目标页、读取本地凭据并填充/提交登录表单。

## 已验证事实

- 仓库：`https://github.com/bigSnake133/LocalSSO`
- 当前主分支最新提交：`0a085a2 Fix login button timeout error`
- 后端入口：`server.py`
- 本地地址：`http://127.0.0.1:8765`
- Python：Windows CPython 3.10+；原开发机验证过 Python 3.14.7
- Python 依赖：无第三方包
- 加密：Windows DPAPI，凭据绑定创建它的 Windows 用户
- 扩展入口：`extension/background.js`、`extension/portal-bridge.js`、`extension/login-fill.js`

## 当前功能状态

- 门户应用、分组、编辑、删除和拖拽排序可用。
- 编辑应用时按需回显本机用户名/密码；密码默认隐藏，可使用眼睛按钮显示。
- 卡片总览显示用户名，密码只显示掩码。
- 扩展支持可见控件筛选、自定义 CSS 选择器、前置入口点击、按按钮文本提交。
- 站点特定的登录规则和真实目标域名不在仓库中；它们位于本机私有 `vault.json` 和 `extension/manifest.json`。

## 不可从 GitHub 直接获得的本机状态

- `vault.json`：含 DPAPI 密文、应用 URL、选择器和本机应用元数据；已被 `.gitignore` 排除。
- `extension/manifest.json`：含真实浏览器 host permissions；已被 `.gitignore` 排除。
- Windows 计划任务 `LocalSSO`：当前用户登录时启动 `pythonw.exe server.py`，异常退出后按重启策略恢复；任务定义不在 Git 中。

不要读取、打印、提交或上传 `vault.json`。不要把真实站点、账号、密码、内网 IP 或浏览器权限写进公开文档。

## 新环境最短启动路径

```powershell
git clone https://github.com/bigSnake133/LocalSSO.git <项目目录>
Set-Location <项目目录>
Copy-Item .\vault.example.json .\vault.json
Copy-Item .\extension\manifest.example.json .\extension\manifest.json
py -3 -m unittest discover -s tests -v
py -3 .\server.py
```

然后在 Chrome/Edge 开发者模式中加载 `<项目目录>\extension`，将 `manifest.json` 中的示例 host permission 替换为已授权的精确站点模式。不要使用 `*://*/*`。

## 修改前验证

```powershell
py -3 -m unittest discover -s tests -v
py -3 -m py_compile .\server.py .\crypto_dpapi.py .\setup_vault.py .\add_standard_apps.py
node --check .\extension\login-fill.js
```

## 已知限制和待办

- 这是可信个人工作站便利工具，不是审计过的密码管理器。
- 同一 Windows 用户下的其他本机进程可访问回环 API。
- DPAPI 不保证跨 Windows 用户、重装后新配置文件或域迁移可恢复。
- 真实站点的选择器、重定向、验证码和登录按钮需逐站验证。
- 当前没有数据库、Redis、MQ、Docker、Nginx 或 HTTPS 反向代理。
- 如修改扩展文件，必须在 `chrome://extensions` / `edge://extensions` 中重新加载扩展。

## 给 WorkBuddy 的操作约束

- 先做只读检查，再做代码修改。
- 不要把 `vault.json` 或私有 `manifest.json` 纳入 Git。
- 不要猜测真实站点权限；让用户提供已授权的非敏感 URL 和选择器。
- 修改后运行测试，并报告实际验证结果。
