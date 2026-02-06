"""Memory tools for persisting and organizing MEMORY.md."""

from pathlib import Path
from typing import Any

from nanobot.agent.memory import MemoryStore
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
    """Tool to save information to long-term memory (MEMORY.md)."""

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
            self.memory.append_long_term(content)
            return f"Successfully saved to MEMORY.md: {content[:100]}{'...' if len(content) > 100 else ''}"
        except Exception as e:
            return f"Error saving to memory: {str(e)}"
