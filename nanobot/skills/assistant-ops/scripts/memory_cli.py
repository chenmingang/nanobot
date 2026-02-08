#!/usr/bin/env python3
"""
Memory CLI for nanobot: remember, append_daily, organize_memory, get, list.
Use from nanobot project root: python nanobot/skills/assistant-ops/scripts/memory_cli.py <cmd> ...
"""
from __future__ import annotations

import sys
from pathlib import Path

# Ensure project root is on path (script at nanobot/skills/assistant-ops/scripts/memory_cli.py -> 5 levels up to root)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from nanobot.agent.memory import MemoryStore
from nanobot.config.loader import load_config


def _store() -> MemoryStore:
    config = load_config()
    return MemoryStore(config.workspace_path)


def cmd_remember(content: str) -> str:
    _store().append_core(content)
    return f"已记住：{content[:80]}{'...' if len(content) > 80 else ''}"


def cmd_append_daily(content: str) -> str:
    store = _store()
    store.append_daily(content)
    return f"已写入当日笔记 {store.get_today_file().name}"


def cmd_organize_memory() -> str:
    return _store().organize_long_term()


def cmd_get(path: str, start_line: int | None = None, lines: int | None = None) -> str:
    return _store().get_memory_file(path, start_line=start_line, lines=lines)


def cmd_list() -> str:
    store = _store()
    files = store.list_memory_files()
    if not files:
        mem_path = store.memory_file
        out = [f"memory/{mem_path.name} (长期记忆)"]
        if mem_path.exists():
            out[0] += " [存在]"
        else:
            out[0] += " [尚未创建]"
        return "\n".join(out)
    lines = ["memory/MEMORY.md (长期记忆)"]
    for p in files:
        lines.append(f"memory/{p.name}")
    return "\n".join(lines)


def main() -> None:
    argv = sys.argv[1:]
    if not argv:
        print("用法: memory_cli.py <remember|append_daily|organize_memory|get|list> [参数...]", file=sys.stderr)
        sys.exit(1)
    sub = argv[0].strip().lower()
    try:
        if sub == "remember":
            if len(argv) < 2:
                print("用法: memory_cli.py remember \"内容\"", file=sys.stderr)
                sys.exit(1)
            print(cmd_remember(argv[1]))
        elif sub == "append_daily":
            if len(argv) < 2:
                print("用法: memory_cli.py append_daily \"内容\"", file=sys.stderr)
                sys.exit(1)
            print(cmd_append_daily(argv[1]))
        elif sub == "organize_memory":
            print(cmd_organize_memory())
        elif sub == "get":
            if len(argv) < 2:
                print("用法: memory_cli.py get <path> [start_line] [lines]", file=sys.stderr)
                sys.exit(1)
            path = argv[1]
            start = int(argv[2]) if len(argv) > 2 else None
            nlines = int(argv[3]) if len(argv) > 3 else None
            print(cmd_get(path, start_line=start, lines=nlines))
        elif sub == "list":
            print(cmd_list())
        else:
            print(f"未知子命令: {sub}", file=sys.stderr)
            sys.exit(1)
    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
