"""Memory system for persistent agent memory."""

from pathlib import Path
from datetime import datetime

from nanobot.utils.helpers import ensure_dir, today_date


class MemoryStore:
    """
    Memory system for the agent.
    
    Supports daily notes (memory/YYYY-MM-DD.md) and long-term memory (MEMORY.md).
    """
    
    def __init__(self, workspace: Path):
        self.workspace = workspace
        self.memory_dir = ensure_dir(workspace / "memory")
        self.memory_file = self.memory_dir / "MEMORY.md"
    
    def get_today_file(self) -> Path:
        """Get path to today's memory file."""
        return self.memory_dir / f"{today_date()}.md"
    
    def read_today(self) -> str:
        """Read today's memory notes."""
        today_file = self.get_today_file()
        if today_file.exists():
            return today_file.read_text(encoding="utf-8")
        return ""
    
    def append_today(self, content: str) -> None:
        """Append content to today's memory notes."""
        today_file = self.get_today_file()
        
        if today_file.exists():
            existing = today_file.read_text(encoding="utf-8")
            content = existing + "\n" + content
        else:
            # Add header for new day
            header = f"# {today_date()}\n\n"
            content = header + content
        
        today_file.write_text(content, encoding="utf-8")
    
    def read_long_term(self) -> str:
        """Read long-term memory (MEMORY.md)."""
        if self.memory_file.exists():
            return self.memory_file.read_text(encoding="utf-8")
        return ""
    
    def write_long_term(self, content: str) -> None:
        """Write to long-term memory (MEMORY.md)."""
        self.memory_file.write_text(content, encoding="utf-8")

    def append_long_term(self, content: str) -> None:
        """Append content to long-term memory (MEMORY.md)."""
        ensure_dir(self.memory_file.parent)
        if self.memory_file.exists():
            existing = self.memory_file.read_text(encoding="utf-8")
            entry = f"\n\n---\n\n## {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n{content.strip()}"
            self.memory_file.write_text(existing + entry, encoding="utf-8")
        else:
            self.memory_file.write_text(f"# Long-term Memory\n\n{content.strip()}", encoding="utf-8")

    def organize_long_term(self) -> str:
        """
        Organize MEMORY.md by categorizing entries for better model context.
        Returns a summary of what was done.
        """
        import re

        if not self.memory_file.exists():
            return "MEMORY.md does not exist; nothing to organize."

        raw = self.memory_file.read_text(encoding="utf-8")

        # Category definitions: (section_title, keywords for matching)
        categories = [
            ("用户信息 / User Information", ["用户", "姓名", "名字", "我是", "邮箱", "电话", "user", "name", "i am", "email", "phone", "我的"]),
            ("偏好设置 / Preferences", ["偏好", "喜欢", "不喜欢", "习惯", "希望", "prefer", "like", "dislike", "habit", "want", "常用", "习惯用"]),
            ("项目上下文 / Project Context", ["项目", "工作", "代码", "开发", "project", "work", "code", "develop", "仓库", "repo"]),
            ("重要笔记 / Important Notes", ["重要", "注意", "提醒", "记住", "important", "note", "remember", "务必", "必须"]),
        ]
        other_title = "其他 / Other"

        # Parse entries: blocks separated by ---, each with optional ## YYYY-MM-DD HH:MM header
        blocks = re.split(r"\n---+\n", raw, flags=re.IGNORECASE)
        entries: list[tuple[str, str]] = []  # (content, section_key)

        placeholders = {
            "(important facts about the user)",
            "(user preferences learned over time)",
            "(information about ongoing projects)",
            "(things to remember)",
        }

        for block in blocks:
            block = block.strip()
            if not block or block.startswith("*"):
                continue
            lines = block.split("\n")
            content_lines = []
            for i, line in enumerate(lines):
                stripped = line.strip()
                if i == 0 and re.match(r"^## \d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}$", stripped):
                    continue
                if stripped.lower() in placeholders:
                    continue
                if stripped in ("## User Information", "## Preferences", "## Project Context", "## Important Notes"):
                    continue
                content_lines.append(line)
            content = "\n".join(content_lines).strip()
            if not content or len(content) < 2:
                continue
            skip_phrases = ("# long-term memory", "automatically updated", "this file stores important information")
            if any(p in content.lower() for p in skip_phrases):
                continue

            content_lower = content.lower()
            section = other_title
            for cat_title, keywords in categories:
                if any(kw in content_lower or kw in content for kw in keywords):
                    section = cat_title
                    break
            entries.append((content, section))

        if not entries:
            return "No entries to organize; MEMORY.md may be empty or template-only."

        # Group by section
        by_section: dict[str, list[str]] = {}
        for content, section in entries:
            by_section.setdefault(section, []).append(content)

        # Build output: deduplicate within section
        sections_order = [c[0] for c in categories] + [other_title]
        out_parts = ["# Long-term Memory\n", "This file stores important information that should persist across sessions.\n"]

        for sec in sections_order:
            if sec not in by_section:
                continue
            items = by_section[sec]
            seen: set[str] = set()
            unique: list[str] = []
            for item in items:
                norm = " ".join(item.split()).strip()
                if norm and norm not in seen:
                    seen.add(norm)
                    unique.append(item)
            if not unique:
                continue
            out_parts.append(f"## {sec}\n\n")
            for item in unique:
                out_parts.append(f"{item}\n\n")
            out_parts.append("\n")

        out_parts.append("---\n\n*This file is automatically updated by nanobot when important information should be remembered.*")

        self.memory_file.write_text("".join(out_parts).strip() + "\n", encoding="utf-8")
        return f"Organized {len(entries)} entries into {len(by_section)} sections. MEMORY.md has been rewritten."
    
    def get_recent_memories(self, days: int = 7) -> str:
        """
        Get memories from the last N days.
        
        Args:
            days: Number of days to look back.
        
        Returns:
            Combined memory content.
        """
        from datetime import timedelta
        
        memories = []
        today = datetime.now().date()
        
        for i in range(days):
            date = today - timedelta(days=i)
            date_str = date.strftime("%Y-%m-%d")
            file_path = self.memory_dir / f"{date_str}.md"
            
            if file_path.exists():
                content = file_path.read_text(encoding="utf-8")
                memories.append(content)
        
        return "\n\n---\n\n".join(memories)
    
    def list_memory_files(self) -> list[Path]:
        """List all memory files sorted by date (newest first)."""
        if not self.memory_dir.exists():
            return []
        
        files = list(self.memory_dir.glob("????-??-??.md"))
        return sorted(files, reverse=True)
    
    def get_memory_context(self) -> str:
        """
        Get memory context for the agent.
        
        Returns:
            Formatted memory context including long-term and recent memories.
        """
        parts = []
        
        # Long-term memory
        long_term = self.read_long_term()
        if long_term:
            parts.append("## Long-term Memory\n" + long_term)
        
        # Today's notes
        today = self.read_today()
        if today:
            parts.append("## Today's Notes\n" + today)
        
        return "\n\n".join(parts) if parts else ""
