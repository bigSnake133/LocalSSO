# LocalSSO

一个仅限 Windows 本机使用的本地登录门户示例：本地 Python 服务提供应用列表，浏览器扩展在用户从门户发起打开操作后，向本机服务读取凭据并填写指定登录页面。凭据使用 Windows DPAPI 保护，绑定到创建它的 Windows 用户。

这是公开的脱敏模板：仓库不包含任何真实账号、密码、令牌、私有网址、内网地址、应用名称或运行时凭据。请只为你有权使用的系统配置条目。

> **安全边界**：这是可信个人工作站上的便利工具，不是经过安全审计的密码管理器。服务仅监听 `127.0.0.1`，但同一 Windows 用户下的其他本机进程仍可能访问本地服务。自动填充期间凭据会短暂出现在浏览器内存中。不要将服务暴露到局域网或公网，不要将 `vault.json` 上传、同步或共享。

## 功能与目录

| 路径 | 用途 |
| --- | --- |
| `server.py` | 本机门户和 JSON API，仅监听 `127.0.0.1:8765`。 |
| `crypto_dpapi.py` | Windows DPAPI 加密与解密帮助函数。 |
| `setup_vault.py` | 交互式添加一个应用和凭据。 |
| `add_standard_apps.py` | 仅添加通用示例应用的批量示例脚本。 |
| `portal/` | 本地门户页面。 |
| `extension/` | Chrome/Edge Manifest V3 扩展。 |
| `vault.example.json` | 无凭据的配置结构示例；不能直接当作真实凭据库。 |
| `docs/` | 安装部署、工程交接与安全说明。 |

## 环境要求

- Windows 10/11，使用保存凭据的同一 Windows 用户运行。
- CPython 3.10 或更高版本；本公开版以 CPython 3.14.0 做过语法和单元测试验证。
- Google Chrome 或 Microsoft Edge，用于加载未打包扩展。
- 无第三方 Python 依赖；`requirements.txt` 仅作此事实记录。

## 快速开始（PowerShell）

```powershell
git clone https://github.com/bigSnake133/LocalSSO.git
Set-Location .\LocalSSO
Copy-Item .\vault.example.json .\vault.json
py -3 .\server.py
```

在浏览器打开 `http://127.0.0.1:8765`。首次使用可在门户中新增应用，输入凭据后由 Windows DPAPI 加密写入未跟踪的 `vault.json`。也可以停止服务后运行：

```powershell
py -3 .\setup_vault.py
```

不要复制他人的 `vault.json`：DPAPI 默认只能由创建它的 Windows 用户解密。

## 加载浏览器扩展与授权域名

1. 在 Chrome 打开 `chrome://extensions`，或在 Edge 打开 `edge://extensions`。
2. 开启“开发者模式”，选择“加载已解压的扩展程序”，选择本仓库的 `extension` 目录。
3. 先复制示例清单：`Copy-Item .\extension\manifest.example.json .\extension\manifest.json`。然后编辑 `extension/manifest.json` 中的 `host_permissions` 和第二个 `content_scripts[].matches`，将 `https://example.com/*` 精确替换成你**有权使用**的登录域名模式。
4. 在扩展页点击重新加载，然后刷新本地门户。
5. 为每个应用在门户中填写正确的 URL 和 CSS 选择器。默认选择器只是常见网页的回退值；请先在非生产账号或测试页面上验证，必要时关闭“自动提交”。

浏览器扩展不能为未声明的站点执行内容脚本，因此第 3 步是必需的。不要使用宽泛的 `*://*/*` 权限。

## 日常操作

- 启动：`py -3 .\server.py`，然后访问 `http://127.0.0.1:8765`。
- 停止：在运行服务的窗口按 `Ctrl+C`。
- 新增/修改应用：使用门户的“添加链接”或编辑操作。空凭据表示只打开链接。
- 删除应用：门户删除操作会从本机 `vault.json` 移除该应用及其加密凭据；删除前请自行备份。
- 备份：关闭服务后，将 `vault.json` 加密保存到只有本人可访问的位置。备份只能在同一 Windows 用户下恢复使用。

完整安装、更新、备份与故障排查请见 [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)。

## 验证

```powershell
py -3 -m unittest discover -s tests -v
py -3 -m py_compile .\server.py .\crypto_dpapi.py .\setup_vault.py .\add_standard_apps.py
Get-Content .\extension\manifest.json -Raw | ConvertFrom-Json | Out-Null
```

这些检查不读取真实 `vault.json`。详细的已验证与未验证项见 [docs/ENGINEERING_HANDOFF.md](docs/ENGINEERING_HANDOFF.md)。

## 不适用的场景

- 多用户共享电脑、远程桌面共享会话或不可信本机软件环境。
- 需要集中密钥管理、审计、轮换、强访问控制或企业级密钥保管的场景。
- 未获得授权的网站、账户或系统。

请先阅读 [SECURITY.md](SECURITY.md)。
