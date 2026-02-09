---
name: browser-ops
description: 浏览器操作。打开网页、点击、输入、截图、填表、多标签等，用终端命令 playwright-cli 完成，无需另装其它浏览器自动化工具。用户说打开网页、打开链接、浏览器截图、页面操作、自动化测试页面时优先用本技能。
metadata: {"nanobot":{"emoji":"🌐","requires":{"bins":["playwright-cli"]},"install":[{"id":"node","kind":"node","package":"@playwright/cli","bins":["playwright-cli"],"label":"Install Playwright CLI (npm)"}]}}
---

# 浏览器操作（Browser Ops）

本技能用 **playwright-cli**（[microsoft/playwright-cli](https://github.com/microsoft/playwright-cli)）在终端完成**浏览器操作**：打开页面、取快照、点击/输入/截图等。直接执行下面命令即可，**不要**去下载或安装其它浏览器自动化库。

**Agent 注意**：本技能只使用命令 **`playwright-cli`**（npm 包 **`@playwright/cli`**）。直接按本页子命令执行，无需根据 help 判断其它。若找不到 `playwright-cli`，提示用户执行 `npm install -g @playwright/cli`，不要改用其它工具。

## 安装

```bash
npm install -g @playwright/cli@latest
playwright-cli --help
```

## 核心流程

1. **打开页面**：`playwright-cli open <url>`（默认有窗口；无头加 `--headless`）
2. **取快照**：`playwright-cli snapshot` → 得到元素 **ref**（如 e21、e35）
3. **交互**：用 ref 执行 `playwright-cli click <ref>`、`playwright-cli fill <ref> <text>`、`playwright-cli type <text>`、`playwright-cli check <ref>` 等
4. **截图/PDF**：`playwright-cli screenshot [ref]`、`playwright-cli pdf`

先 `snapshot` 再根据 ref 操作，避免盲点盲填。

## 常用命令

| 命令 | 说明 |
|------|------|
| `playwright-cli open [url]` | 打开浏览器 / 打开 URL |
| `playwright-cli close` | 关闭页面 |
| `playwright-cli snapshot` | 页面快照，得到可点击元素的 ref |
| `playwright-cli click <ref> [button]` | 点击 |
| `playwright-cli fill <ref> <text>` | 清空并填入文本 |
| `playwright-cli type <text>` | 在当前可编辑元素输入 |
| `playwright-cli hover <ref>` | 悬停 |
| `playwright-cli check <ref>` / `uncheck <ref>` | 勾选/取消勾选 |
| `playwright-cli select <ref> <val>` | 下拉选择 |
| `playwright-cli press <key>` | 按键（如 Enter、ArrowLeft） |
| `playwright-cli screenshot [ref]` | 截图（整页或元素） |
| `playwright-cli pdf` | 导出 PDF |

## 导航与键盘/鼠标

```bash
playwright-cli go-back
playwright-cli go-forward
playwright-cli reload
playwright-cli keydown <key>
playwright-cli keyup <key>
playwright-cli mousemove <x> <y>
playwright-cli mousewheel <dx> <dy>
```

## 多标签与会话

```bash
playwright-cli tab-list
playwright-cli tab-new [url]
playwright-cli tab-close [index]
playwright-cli tab-select <index>
```

会话隔离（独立 cookie/storage）：`-s=名称`

```bash
playwright-cli open https://site1.com
playwright-cli -s=project-a open https://site2.com
playwright-cli list
playwright-cli close-all
playwright-cli kill-all
```

## 配置与有头模式

- 默认有头（可见窗口）；无头：`playwright-cli open https://example.com --headless`
- 指定浏览器：`playwright-cli open --browser=chrome`
- 配置文件：项目下 `playwright-cli.json` 或 `--config=path/to/config.json`

## Agent 使用建议

1. 先 `open` 再 `snapshot`，用快照中的 ref 做 click/fill/type。
2. 需要肉眼确认时不要加 `--headless`（默认即有窗口）。
3. 多任务时用不同 `-s=session-name` 隔离会话。
4. 弹窗：`playwright-cli dialog-accept [prompt]` / `playwright-cli dialog-dismiss`。
5. 更多命令见 `playwright-cli --help`。

## 参考

- 仓库：<https://github.com/microsoft/playwright-cli>
