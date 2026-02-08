# nanobot Skills

This directory contains built-in skills that extend nanobot's capabilities.

## Skill Format

Each skill is a directory containing a `SKILL.md` file with:
- YAML frontmatter (name, description, metadata)
- Markdown instructions for the agent

## Attribution

These skills are adapted from [OpenClaw](https://github.com/openclaw/openclaw)'s skill system.
The skill format and metadata structure follow OpenClaw's conventions to maintain compatibility.

## Available Skills

| Skill | Description |
|-------|-------------|
| `assistant-ops` | 助手自身操作：gateway.sh 重启/启停、memory 脚本、nanobot sessions 管理 |
| `code-assistant` | 代码分析/重构/生成（Java、Python、前端），配套脚本 |
| `github` | Interact with GitHub using the `gh` CLI |
| `memory` | 记忆读写与整理（memory_cli.py），与 loop 工程侧并存 |
| `summarize` | Summarize URLs, files, and YouTube videos |
| `tmux` | Remote-control tmux sessions |
| `weather` | Get weather info using wttr.in and Open-Meteo |
| `skill-creator` | Create new skills |