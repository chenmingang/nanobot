---
name: assistant-ops
description: 对当前 nanobot 助手本身的操作。包括使用 gateway.sh 重启/启停、使用 memory skill 脚本操作记忆、使用 nanobot 命令处理 session。用户说「重启助手」「清空会话」「整理记忆」等时使用本 skill。
---

# Assistant Ops Skill（助手自身操作）

本 skill 用于操作**当前 nanobot 助手本身**：重启网关、操作记忆、管理会话。记忆部分使用 **memory** skill 的脚本（exec）；网关与 session 通过 **exec** 执行命令，执行前请确认工作目录或 PATH。

**助手本身的目录位置**：指**代码目录**（nanobot 项目/代码所在目录），不是配置的 workspace 工作目录。需通过执行 `pwd` 获取当前所在目录（即代码目录）；在此目录下可执行 `gateway.sh` 等。

## 1. Gateway 启停与重启（gateway.sh）

- **脚本位置**：nanobot 项目根目录下的 `gateway.sh`（与 `nanobot` 包同级；若为 pip 安装，需在拷贝了该脚本的目录执行）。
- **用法**：在脚本所在目录执行（或先 `cd` 到该目录）：
  - 重启：`./gateway.sh restart` 或 `bash gateway.sh restart`
  - 启动：`./gateway.sh start`
  - 停止：`./gateway.sh stop`
  - 状态：`./gateway.sh status`
- **示例**（exec，工作目录为项目根时）：
  - `bash gateway.sh restart`
  - `bash gateway.sh status`
- 用户说「重启助手」「重启 nanobot」「重启网关」时，执行 `gateway.sh restart`。

## 2. 记忆操作（memory skill 脚本）

- 记忆相关工具已不对模型暴露，需通过 **memory** skill 的脚本 `nanobot/skills/memory/scripts/memory_cli.py` 操作（exec）。
- 记忆目录为配置的 **workspace / memory**（如 `~/.nanobot/workspace/memory/`）。
- **示例**（exec；需在项目根或设置 `NANOBOT_WORKSPACE` 后执行）：
  - 记住：`python nanobot/skills/memory/scripts/memory_cli.py remember "内容"`
  - 当日笔记：`python nanobot/skills/memory/scripts/memory_cli.py append_daily "内容"`
  - 整理：`python nanobot/skills/memory/scripts/memory_cli.py organize_memory`
  - 读取：`python nanobot/skills/memory/scripts/memory_cli.py get memory/MEMORY.md`
  - 列出：`python nanobot/skills/memory/scripts/memory_cli.py list`
- 用户说「整理记忆」「记住 X」「读一下记忆」等时，用 exec 调用上述命令。

## 3. Session 会话管理（nanobot CLI）

- 会话存储在 **~/.nanobot/sessions/**（*.jsonl）。
- 使用 **nanobot** 子命令（需已安装且 `nanobot` 在 PATH 中）：
  - **列出会话**：`nanobot sessions list`
  - **清空所有会话**：`nanobot sessions clear`（会确认；加 `-f` 跳过确认：`nanobot sessions clear -f`）
  - **删除指定会话**：`nanobot sessions delete <key>`，其中 `key` 为 list 输出的 key（如 `feishu:oc_xxx`、`cli_direct`；文件名中 `:` 会显示为 `_`，delete 时可用 `_` 或 `:`）。
- **示例**（exec）：
  - `nanobot sessions list`
  - `nanobot sessions clear -f`
  - `nanobot sessions delete feishu_oc_2f6d660926625766c3aed94040f4d94e`
- 用户说「清空会话」「删除所有对话」「删掉某个会话」时，选用 list/clear/delete。

## 4. 使用建议

- **重启**：仅在用户明确要求重启助手/网关时执行 `gateway.sh restart`；执行后网关会短暂不可用再恢复。
- **记忆**：用 exec 运行 memory skill 的 memory_cli.py（模型不暴露记忆工具）。
- **会话**：list 查看；clear 慎用（清空所有）；delete 按 key 删除单会话。执行 clear/delete 前可根据需要先 list 确认。
- 所有命令均通过 **exec** 执行；若 exec 的 working_dir 不是项目根，gateway.sh 与 memory_cli.py 需用绝对路径或先 cd。
