<div align="center">
  <img src="nanobot_logo.png" alt="nanobot" width="500">
  <h1>nanobot：超轻量个人 AI 助手</h1>
  <p>
    <a href="https://pypi.org/project/nanobot-ai/"><img src="https://img.shields.io/pypi/v/nanobot-ai" alt="PyPI"></a>
    <a href="https://pepy.tech/project/nanobot-ai"><img src="https://static.pepy.tech/badge/nanobot-ai" alt="Downloads"></a>
    <img src="https://img.shields.io/badge/python-≥3.11-blue" alt="Python">
    <img src="https://img.shields.io/badge/license-MIT-green" alt="License">
    <a href="./COMMUNICATION.md"><img src="https://img.shields.io/badge/Feishu-Group-E9DBFC?style=flat&logo=feishu&logoColor=white" alt="Feishu"></a>
    <a href="./COMMUNICATION.md"><img src="https://img.shields.io/badge/WeChat-Group-C5EAB4?style=flat&logo=wechat&logoColor=white" alt="WeChat"></a>
    <a href="https://discord.gg/MnCvHqpUGB"><img src="https://img.shields.io/badge/Discord-Community-5865F2?style=flat&logo=discord&logoColor=white" alt="Discord"></a>
  </p>
</div>

🐈 **nanobot** 是一款受 [Clawdbot](https://github.com/openclaw/openclaw) 启发的**超轻量**个人 AI 助手。

⚡️ 核心 agent 仅 **约 4,000 行**代码，相比 Clawdbot 的 43 万+ 行**体量减少约 99%**。

## 📢 动态

- **2026-02-01** 🎉 nanobot 正式发布，欢迎试用 🐈！

## 核心特点

🪶 **超轻量**：约 4,000 行代码，核心功能体量约为 Clawdbot 的 1%。

🔬 **适合研究与二次开发**：结构清晰、易读、易改、易扩展。

⚡️ **启动与运行更快**：占用小，启动快、资源省、迭代快。

💎 **易用**：一键部署即可使用。

## 🏗️ 架构

<p align="center">
  <img src="nanobot_arch.png" alt="nanobot 架构" width="800">
</p>

## ✨ 功能概览

<table align="center">
  <tr align="center">
    <th><p align="center">📈 24/7 实时市场分析</p></th>
    <th><p align="center">🚀 全栈工程师助手</p></th>
    <th><p align="center">📅 智能日程管理</p></th>
    <th><p align="center">📚 个人知识助手</p></th>
  </tr>
  <tr>
    <td align="center"><p align="center"><img src="case/search.gif" width="180" height="400"></p></td>
    <td align="center"><p align="center"><img src="case/code.gif" width="180" height="400"></p></td>
    <td align="center"><p align="center"><img src="case/scedule.gif" width="180" height="400"></p></td>
    <td align="center"><p align="center"><img src="case/memory.gif" width="180" height="400"></p></td>
  </tr>
  <tr>
    <td align="center">发现 · 洞察 · 趋势</td>
    <td align="center">开发 · 部署 · 扩展</td>
    <td align="center">排程 · 自动化 · 整理</td>
    <td align="center">学习 · 记忆 · 推理</td>
  </tr>
</table>

## 📦 安装

**从源码安装**（功能最新，适合开发）

```bash
git clone https://github.com/HKUDS/nanobot.git
cd nanobot
pip install -e .
```

**使用 [uv](https://github.com/astral-sh/uv) 安装**（稳定、快速）

```bash
uv tool install nanobot-ai
```

**从 PyPI 安装**（稳定版）

```bash
pip install nanobot-ai
```

## 🚀 快速开始

> [!TIP]
> 在 `~/.nanobot/config.json` 中配置 API Key。
> 获取方式：[OpenRouter](https://openrouter.ai/keys)（LLM）· [Brave Search](https://brave.com/search/api/)（可选，网页搜索）
> 也可将模型改为 `minimax/minimax-m2` 以降低成本。

**1. 初始化**

```bash
nanobot onboard
```

**2. 配置**（`~/.nanobot/config.json`）

```json
{
  "providers": {
    "openrouter": {
      "enabled": true,
      "apiKey": "sk-or-v1-xxx"
    }
  },
  "agents": {
    "defaults": {
      "model": "anthropic/claude-opus-4-5",
      "max_history_messages": 50
    }
  },
  "webSearch": {
    "apiKey": "BSA-xxx"
  }
}
```

**3. 对话**

```bash
nanobot agent -m "2+2 等于几？"
```

两分钟内即可拥有可用的 AI 助手。

## 🖥️ 本地模型（vLLM）

通过 vLLM 或任意 OpenAI 兼容服务使用本地模型。

**1. 启动 vLLM 服务**

```bash
vllm serve meta-llama/Llama-3.1-8B-Instruct --port 8000
```

**2. 配置**（`~/.nanobot/config.json`）

```json
{
  "providers": {
    "vllm": {
      "enabled": true,
      "apiKey": "dummy",
      "apiBase": "http://localhost:8000/v1"
    }
  },
  "agents": {
    "defaults": {
      "model": "meta-llama/Llama-3.1-8B-Instruct"
    }
  }
}
```

**3. 对话**

```bash
nanobot agent -m "用我的本地模型打个招呼！"
```

> [!TIP]
> 本地服务若不鉴权，`apiKey` 填任意非空字符串即可。

## 🦙 Ollama（本地模型）

通过 [Ollama](https://ollama.com) 在本地运行模型，无需 API Key。

**1. 安装并启动 Ollama**

```bash
# 安装后运行（默认 http://localhost:11434）
ollama serve
ollama pull llama3.2
```

**2. 配置**（`~/.nanobot/config.json`）

```json
{
  "providers": {
    "ollama": {
      "enabled": true,
      "apiBase": "http://localhost:11434"
    }
  },
  "agents": {
    "defaults": {
      "model": "ollama_chat/llama3.2"
    }
  }
}
```

- **模型名**：使用 `ollama/模型名` 或 `ollama_chat/模型名`（推荐 `ollama_chat/` 对话效果更好），如 `ollama_chat/llama3.2`、`ollama/qwen2.5`。
- **apiBase**：不填默认为 `http://localhost:11434`。

**3. 对话**

```bash
nanobot agent -m "用本地 Ollama 打个招呼！"
```

## 💬 聊天渠道

通过 Telegram 或飞书/WhatsApp 与 nanobot 对话，随时随地使用。

| 渠道 | 难度 |
|------|------|
| **Telegram** | 简单（仅需 token） |
| **飞书 Feishu** | 配置 app_id/app_secret 或 tenant_access_token |
| **WhatsApp** | 中等（需扫码绑定） |

<details>
<summary><b>Telegram</b>（推荐）</summary>

**1. 创建 Bot**
- 在 Telegram 中搜索 `@BotFather`
- 发送 `/newbot` 并按提示操作
- 复制得到的 token

**2. 配置**

```json
{
  "channels": {
    "telegram": {
      "enabled": true,
      "token": "YOUR_BOT_TOKEN",
      "allowFrom": ["YOUR_USER_ID"]
    }
  }
}
```

> 在 Telegram 中通过 `@userinfobot` 获取你的 user ID。

**3. 运行**

```bash
nanobot gateway
```

</details>

<details>
<summary><b>飞书 Feishu</b></summary>

支持 `tenant_access_token` 或 `app_id` + `app_secret` 自动拉取 token。  
「正在思考…」消息会在首条用户消息约 1 秒后发送；token 会在发送前自动校验/刷新。

**配置示例**

```json
{
  "channels": {
    "feishu": {
      "enabled": true,
      "app_id": "xxx",
      "app_secret": "xxx",
      "allowFrom": []
    }
  }
}
```

</details>

<details>
<summary><b>WhatsApp</b></summary>

需要 **Node.js ≥18**。

**1. 绑定设备**

```bash
nanobot channels login
# 在 WhatsApp：设置 → 已链接的设备 → 扫码
```

**2. 配置**

```json
{
  "channels": {
    "whatsapp": {
      "enabled": true,
      "allowFrom": ["+1234567890"]
    }
  }
}
```

**3. 运行**（两个终端）

```bash
# 终端 1
nanobot channels login

# 终端 2
nanobot gateway
```

</details>

## ⚙️ 配置说明

配置文件：`~/.nanobot/config.json`

### 模型

- **根级 `model`**（可选）：若设置，将覆盖 `agents.defaults.model`，用于快速切换模型。
- **`agents.defaults.model`**：默认使用的 LLM 模型（如 `anthropic/claude-opus-4-5`、`openai/gpt-4o`）。
- **`providers.<name>.model`**（推荐）：把模型写在具体 provider 内；运行时会选择**第一个 enabled 的 provider**，并优先使用该 provider 的 `model`（未填则回退到 `agents.defaults.model`）。

### 渠道提供商（Provider）

> [!NOTE]
> 仅 **enabled 为 true** 的 provider 会参与 API Key / API Base 选择；未启用项即使配置了 key 也不会被使用。  
> Groq 提供免费语音转写（Whisper），配置后 Telegram 语音消息会自动转文字。

| Provider | 用途 | 获取 API Key |
|----------|------|--------------|
| `openrouter` | LLM（推荐，可访问多模型） | [openrouter.ai](https://openrouter.ai) |
| `anthropic` | LLM（Claude 直连） | [console.anthropic.com](https://console.anthropic.com) |
| `openai` | LLM（GPT 直连） | [platform.openai.com](https://platform.openai.com) |
| `siliconflow` | LLM（硅基流动，Qwen/DeepSeek 等） | [cloud.siliconflow.cn](https://cloud.siliconflow.cn) |
| `groq` | LLM + **语音转写**（Whisper） | [console.groq.com](https://console.groq.com) |
| `gemini` | LLM（Gemini 直连） | [aistudio.google.com](https://aistudio.google.com) |
| `vllm` | 本地/自建 OpenAI 兼容服务 | 无需 key，填 `apiBase` 即可 |
| `ollama` | 本地 Ollama | 无需 key，填 `apiBase`（默认 `http://localhost:11434`） |

每个 provider 支持 **`enabled`**（默认 true），设为 false 即可禁用该渠道而不删配置。

<details>
<summary><b>完整配置示例</b></summary>

```json
{
  "model": "openai/gpt-4o",
  "agents": {
    "defaults": {
      "model": "anthropic/claude-opus-4-5",
      "max_history_messages": 50
    }
  },
  "providers": {
    "openrouter": {
      "enabled": true,
      "apiKey": "sk-or-v1-xxx",
      "model": "anthropic/claude-opus-4-5"
    },
    "anthropic": {
      "enabled": false,
      "apiKey": "",
      "model": ""
    },
    "groq": {
      "enabled": true,
      "apiKey": "gsk_xxx",
      "model": "groq/llama-3.1-70b-versatile"
    },
    "ollama": {
      "enabled": false,
      "apiBase": "http://localhost:11434",
      "model": "ollama_chat/llama3.2"
    }
  },
  "channels": {
    "telegram": {
      "enabled": true,
      "token": "123456:ABC...",
      "allowFrom": ["123456789"]
    },
    "feishu": {
      "enabled": true,
      "app_id": "xxx",
      "app_secret": "xxx"
    },
    "whatsapp": {
      "enabled": false
    }
  },
  "tools": {
    "web": {
      "search": {
        "apiKey": "BSA..."
      }
    }
  }
}
```

</details>

## 📋 记忆与语义检索

- **长期记忆**：`workspace/memory/MEMORY.md`（用户说「记住」时由模型调用 `remember` / `remember_core` 写入）。
- **按日笔记**：`workspace/memory/YYYY-MM-DD.md`（会话小结、次要信息，由 `append_daily` 或压缩前自动写入）。
- **语义检索**：每条用户消息前会**自动**用当前消息对记忆文件做向量检索，结果注入系统提示的 **「Relevant memories (from semantic search)」** 段落，模型无需再调 memory_search。
- **依赖**：需安装 `nanobot-ai[memory]`（含 chromadb、sentence-transformers、torch）。ChromaDB 要求 **sqlite3 ≥ 3.35**；若报错可参考 [Chroma 文档](https://docs.trychroma.com/troubleshooting#sqlite) 升级系统 sqlite 或使用带新 sqlite 的 Python 环境。

## ⏰ 定时任务与到点提醒

- **Cron**：`nanobot cron add --name "reminder" --message "该出门了" --at "2026-02-07T10:00:00" --deliver --to "CHAT_ID" --channel "feishu"` 等。
- **到点提醒**：定时任务触发时，系统会为当次对话注入「当前是到点的定时任务」说明，引导模型用「⏰ 时间到了！」口吻回复，而不是「X 分钟后提醒您」；若任务需要执行工具，模型仍可正常调用并返回结果。

## 📜 CLI 参考

| 命令 | 说明 |
|------|------|
| `nanobot onboard` | 初始化配置与工作区 |
| `nanobot agent -m "..."` | 与 agent 单轮对话 |
| `nanobot agent` | 交互式对话 |
| `nanobot gateway` | 启动网关（渠道 + agent） |
| `nanobot status` | 查看状态与各 provider 启用情况 |
| `nanobot sessions list` | 列出所有会话 |
| `nanobot sessions clear` | 清空所有会话（需确认）；清空后**无需重启 gateway**，下次消息会使用空历史 |
| `nanobot sessions delete <key>` | 删除指定会话 |
| `nanobot channels login` | 绑定 WhatsApp（扫码） |
| `nanobot channels status` | 查看渠道状态 |

<details>
<summary><b>定时任务（Cron）</b></summary>

```bash
# 添加任务
nanobot cron add --name "daily" --message "早上好！" --cron "0 9 * * *"
nanobot cron add --name "hourly" --message "检查状态" --every 3600

# 列出任务
nanobot cron list

# 删除任务
nanobot cron remove <job_id>
```

</details>

## 🐳 Docker

> [!TIP]
> 使用 `-v ~/.nanobot:/root/.nanobot` 可将本机配置目录挂载进容器，配置与工作区在重启后保留。

```bash
# 构建镜像
docker build -t nanobot .

# 首次初始化配置
docker run -v ~/.nanobot:/root/.nanobot --rm nanobot onboard

# 在宿主机编辑配置、填写 API Key
vim ~/.nanobot/config.json

# 运行网关
docker run -v ~/.nanobot:/root/.nanobot -p 18790:18790 nanobot gateway

# 或单次命令
docker run -v ~/.nanobot:/root/.nanobot --rm nanobot agent -m "你好！"
docker run -v ~/.nanobot:/root/.nanobot --rm nanobot status
```

## 📁 项目结构

```
nanobot/
├── agent/          # 🧠 核心 agent（循环、上下文、记忆、技能、子 agent、工具）
│   ├── loop.py     #    Agent 主循环（LLM ↔ 工具执行）
│   ├── context.py  #    系统提示与消息构建
│   ├── memory.py   #    持久记忆（MEMORY.md、按日笔记）
│   ├── memory_search.py # 记忆语义检索（ChromaDB + sentence-transformers）
│   ├── skills.py   #    技能加载
│   ├── subagent.py #    后台子任务
│   └── tools/      #    内置工具（文件、记忆、shell、消息、spawn 等）
├── skills/         # 🎯 内置技能
├── channels/       # 📱 飞书、Telegram、WhatsApp 等
├── bus/            # 🚌 消息总线
├── cron/           # ⏰ 定时任务
├── heartbeat/      # 💓 心跳任务
├── providers/      # 🤖 LLM 提供方（LiteLLM 等）
├── session/        # 💬 会话管理
├── config/         # ⚙️ 配置结构
└── cli/            # 🖥️ 命令行入口
```

## 📝 近期更新与行为说明（chenmingang 等）

- **配置**
  - 根级 **`model`** 可覆盖 `agents.defaults.model`，便于快速切换模型。
  - 各 **Provider 支持 `enabled`**；仅启用的 provider 参与 API Key/Base 选择；`nanobot status` 会显示各渠道启用状态与是否已配置 key。
- **会话**
  - **`sessions clear`** 后，若未重启 gateway，下次请求会检查磁盘文件是否存在；文件已删除则自动丢弃对应缓存，**无需重启**即可生效。
- **工具与记忆**
  - **memory_search**、**web_search**、**web_fetch** 不暴露给模型（由工程侧自动做记忆检索或按需隐藏），减少工具列表干扰。
  - 语义检索结果注入系统提示的 **「Relevant memories (from semantic search)」**；记忆写入后会自动重建向量索引。
- **飞书**
  - 发送「正在思考…」前会**先确保 token**；若接口返回 token 无效/过期（如 99991663），会清空缓存并重试一次。
- **定时任务**
  - Cron 任务使用 **session_key 形如 `cron:job_id`**，系统会注入「当前为到点定时任务」的说明，引导模型用「时间到了」口吻回复；仍支持模型调用工具并返回结果。
- **Thinking 模型**
  - 当 assistant 消息包含 **tool_calls** 时，会补全 **reasoning_content**（空字符串亦可），避免 o1/o3/Claude 等 thinking 模型报错。
- **日志与依赖**
  - 记忆检索相关日志使用 **INFO** 级别（如「Memory recall: N results for query=...」）；日志占位符统一为 loguru 的 `{}`。
  - ChromaDB 若因 **sqlite 版本过旧** 初始化失败，会打出简洁提示并附带官方排错链接。
  - **PyTorch** 为记忆语义检索所必需；未安装时会提示并仅打一次；`nanobot-ai[memory]` 已包含 `torch`。

## 🤝 参与与路线图

欢迎 PR，代码库保持精简可读。🤗

**路线图** — 认领一项并 [提交 PR](https://github.com/HKUDS/nanobot/pulls)：

- [x] **语音转写** — Groq Whisper 支持
- [x] **长期记忆与语义检索** — MEMORY.md、按日笔记、向量检索与自动注入
- [ ] **多模态** — 图像、语音、视频
- [ ] **更强推理** — 多步规划与反思
- [ ] **更多集成** — Discord、Slack、邮件、日历
- [ ] **自我改进** — 从反馈与错误中学习

### 贡献者

<a href="https://github.com/HKUDS/nanobot/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=HKUDS/nanobot" />
</a>

## ⭐ Star History

<div align="center">
  <a href="https://star-history.com/#HKUDS/nanobot&Date">
    <picture>
      <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=HKUDS/nanobot&type=Date&theme=dark" />
      <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=HKUDS/nanobot&type=Date" />
      <img alt="Star History Chart" src="https://api.star-history.com/svg?repos=HKUDS/nanobot&type=Date" style="border-radius: 15px; box-shadow: 0 0 30px rgba(0, 217, 255, 0.3);" />
    </picture>
  </a>
</div>

<p align="center">
  <em>感谢使用 ✨ nanobot！</em><br><br>
  <img src="https://visitor-badge.laobi.icu/badge?page_id=HKUDS.nanobot&style=for-the-badge&color=00d4ff" alt="Views">
</p>

<p align="center">
  <sub>nanobot 仅用于教育、研究及技术交流</sub>
</p>
