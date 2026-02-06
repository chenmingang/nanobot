"""Memory tools for persisting and organizing MEMORY.md."""

from pathlib import Path
from typing import Any

from nanobot.agent.memory import MemoryStore
from nanobot.agent.memory_search import MemorySearchIndex
from nanobot.agent.tools.base import Tool


class OrganizeMemoryTool(Tool):
    """Tool to organize MEMORY.md by categorizing entries for better model context."""

    def __init__(self, workspace: Path):
        self.workspace = Path(workspace).expanduser().resolve()
        self.memory = MemoryStore(self.workspace)

    @property
    def name(self) -> str:
        return "organize_memory"

    @property
    def description(self) -> str:
        return (
            "Organize MEMORY.md: categorize historical entries into sections "
            "(用户信息/User Information, 偏好设置/Preferences, 项目上下文/Project Context, 重要笔记/Important Notes, 其他/Other), "
            "deduplicate, and rewrite the file for better model context. "
            "Use when the user asks to organize/tidy/整理 memory, or when MEMORY.md has grown messy."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {},
            "required": [],
        }

    async def execute(self, **kwargs: Any) -> str:
        try:
            return self.memory.organize_long_term()
        except Exception as e:
            return f"Error organizing memory: {str(e)}"


class RememberTool(Tool):
    """Tool to save information to long-term memory (MEMORY.md). Alias for remember_core."""

    def __init__(self, workspace: Path):
        self.workspace = Path(workspace).expanduser().resolve()
        self.memory = MemoryStore(self.workspace)

    @property
    def name(self) -> str:
        return "remember"

    @property
    def description(self) -> str:
        return (
            "Save important information to long-term memory (MEMORY.md). "
            "Use this when the user asks to remember something (e.g. 记住, remember, 帮我记一下). "
            "Always call this tool when the user explicitly requests to remember/save information."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "The information to save (in Markdown format)",
                }
            },
            "required": ["content"],
        }

    async def execute(self, content: str, **kwargs: Any) -> str:
        try:
            self.memory.append_core(content)
            return f"Successfully saved to MEMORY.md: {content[:100]}{'...' if len(content) > 100 else ''}"
        except Exception as e:
            return f"Error saving to memory: {str(e)}"


class RememberCoreTool(Tool):
    """Tool to save core/important information to MEMORY.md (user-requested, identity, preferences)."""

    def __init__(self, workspace: Path):
        self.workspace = Path(workspace).expanduser().resolve()
        self.memory = MemoryStore(self.workspace)

    @property
    def name(self) -> str:
        return "remember_core"

    @property
    def description(self) -> str:
        return (
            "Save core information to MEMORY.md. Use for: user explicitly requested to remember, "
            "identity (name, email, phone), preferences, critical facts. Keep MEMORY.md concise."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "Core information to save (Markdown format)",
                }
            },
            "required": ["content"],
        }

    async def execute(self, content: str, **kwargs: Any) -> str:
        try:
            self.memory.append_core(content)
            return f"Successfully saved to MEMORY.md (core): {content[:100]}{'...' if len(content) > 100 else ''}"
        except Exception as e:
            return f"Error saving to core memory: {str(e)}"


class AppendDailyTool(Tool):
    """Tool to append session notes and secondary facts to memory/YYYY-MM-DD.md."""

    def __init__(self, workspace: Path):
        self.workspace = Path(workspace).expanduser().resolve()
        self.memory = MemoryStore(self.workspace)

    @property
    def name(self) -> str:
        return "append_daily"

    @property
    def description(self) -> str:
        return (
            "Append notes to today's memory file (memory/YYYY-MM-DD.md). "
            "Use for: session summaries, discussion points, TODO items, secondary facts."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "Notes to append (Markdown format)",
                }
            },
            "required": ["content"],
        }

    async def execute(self, content: str, **kwargs: Any) -> str:
        try:
            self.memory.append_daily(content)
            return f"Successfully appended to {self.memory.get_today_file().name}: {content[:100]}{'...' if len(content) > 100 else ''}"
        except Exception as e:
            return f"Error appending to daily memory: {str(e)}"


class MemorySearchTool(Tool):
    """Tool to semantically search memory files (MEMORY.md, memory/*.md)."""

    def __init__(self, workspace: Path, api_key: str | None = None, api_base: str | None = None):
        self.workspace = Path(workspace).expanduser().resolve()
        self.index = MemorySearchIndex(self.workspace, api_key=api_key, api_base=api_base)

    @property
    def name(self) -> str:
        return "memory_search"

    @property
    def description(self) -> str:
        return (
            "Semantically search memory files (MEMORY.md, memory/YYYY-MM-DD.md). "
            "Use when you need to recall related information that may be stored in memory."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "top_k": {"type": "integer", "description": "Max results (default 5)", "default": 5},
            },
            "required": ["query"],
        }

    async def execute(self, query: str, top_k: int = 5, **kwargs: Any) -> str:
        try:
            results = self.index.search(query, top_k=top_k)
            if not results:
                return "No relevant memories found."
            parts = []
            for i, r in enumerate(results, 1):
                parts.append(f"[{i}] {r['path']} (line {r['start_line']}, score {r['score']}):\n{r['content']}")
            return "\n\n".join(parts)
        except Exception as e:
            return f"Memory search failed: {str(e)}"


class MemoryGetTool(Tool):
    """Tool to read a memory file by path."""

    def __init__(self, workspace: Path):
        self.workspace = Path(workspace).expanduser().resolve()
        self.memory = MemoryStore(self.workspace)

    @property
    def name(self) -> str:
        return "memory_get"

    @property
    def description(self) -> str:
        return (
            "Read a memory file by workspace-relative path. "
            "E.g. memory/MEMORY.md, memory/2026-02-06.md. Use start_line and lines for partial read."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Workspace-relative path (e.g. memory/MEMORY.md)"},
                "start_line": {"type": "integer", "description": "Start line (1-based, optional)"},
                "lines": {"type": "integer", "description": "Number of lines to read (optional)"},
            },
            "required": ["path"],
        }

    async def execute(
        self, path: str, start_line: int | None = None, lines: int | None = None, **kwargs: Any
    ) -> str:
        try:
            return self.memory.get_memory_file(path, start_line=start_line, lines=lines)
        except Exception as e:
            return f"Error reading memory: {str(e)}"
