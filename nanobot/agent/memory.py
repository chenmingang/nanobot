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
        """Append content to long-term memory (MEMORY.md). Kept for backward compatibility."""
        self.append_core(content)

    def append_core(self, content: str) -> None:
        """Append core/important content to MEMORY.md (user-requested, identity, preferences)."""
        ensure_dir(self.memory_file.parent)
        if self.memory_file.exists():
            existing = self.memory_file.read_text(encoding="utf-8")
            entry = f"\n\n---\n\n## {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n{content.strip()}"
            self.memory_file.write_text(existing + entry, encoding="utf-8")
        else:
            self.memory_file.write_text(f"# Long-term Memory\n\n{content.strip()}", encoding="utf-8")

    def append_daily(self, content: str) -> None:
        """Append session notes and secondary facts to memory/YYYY-MM-DD.md."""
        self.append_today(content)

    CORE_SECTIONS = ("用户信息 / User Information", "偏好设置 / Preferences")

    def organize_long_term(self) -> str:
        """
        Organize MEMORY.md: keep only core content (user info, preferences),
        move non-core entries to dated memory/YYYY-MM-DD.md files.
        Returns a summary of what was done.
        """
        import re
        from datetime import datetime as dt

        if not self.memory_file.exists():
            return "MEMORY.md does not exist; nothing to organize."

        raw = self.memory_file.read_text(encoding="utf-8")

        categories = [
            ("用户信息 / User Information", ["用户", "姓名", "名字", "我是", "邮箱", "电话", "user", "name", "i am", "email", "phone", "我的"]),
            ("偏好设置 / Preferences", ["偏好", "喜欢", "不喜欢", "习惯", "希望", "prefer", "like", "dislike", "habit", "want", "常用", "习惯用"]),
            ("项目上下文 / Project Context", ["项目", "工作", "代码", "开发", "project", "work", "code", "develop", "仓库", "repo"]),
            ("重要笔记 / Important Notes", ["重要", "注意", "提醒", "记住", "important", "note", "remember", "务必", "必须"]),
        ]
        other_title = "其他 / Other"

        blocks = re.split(r"\n---+\n", raw, flags=re.IGNORECASE)
        entries: list[tuple[str, str, str | None]] = []  # (content, section_key, date_str or None)

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
            entry_date: str | None = None
            for i, line in enumerate(lines):
                stripped = line.strip()
                m = re.match(r"^## (\d{4}-\d{2}-\d{2})\s+\d{2}:\d{2}$", stripped) if i == 0 else None
                if m:
                    entry_date = m.group(1)
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
            entries.append((content, section, entry_date))

        if not entries:
            return "No entries to organize; MEMORY.md may be empty or template-only."

        core_entries: list[str] = []
        non_core_to_daily: list[tuple[str, str]] = []  # (content, date_str)

        for content, section, entry_date in entries:
            if section in self.CORE_SECTIONS:
                core_entries.append(content)
            else:
                date_str = entry_date or today_date()
                non_core_to_daily.append((content, date_str))

        # Deduplicate core entries
        seen_core: set[str] = set()
        unique_core: list[str] = []
        for item in core_entries:
            norm = " ".join(item.split()).strip()
            if norm and norm not in seen_core:
                seen_core.add(norm)
                unique_core.append(item)

        # Group non-core by date, append to respective daily files
        by_date: dict[str, list[str]] = {}
        for content, date_str in non_core_to_daily:
            by_date.setdefault(date_str, []).append(content)

        moved_count = 0
        for date_str, items in by_date.items():
            daily_path = self.memory_dir / f"{date_str}.md"
            appendix = "\n\n---\n\n".join(items)
            if daily_path.exists():
                existing = daily_path.read_text(encoding="utf-8")
                new_content = existing + "\n\n---\n\n" + appendix
            else:
                new_content = f"# {date_str}\n\n{appendix}"
            daily_path.write_text(new_content, encoding="utf-8")
            moved_count += len(items)

        # Rewrite MEMORY.md with only core content
        out_parts = [
            "# Long-term Memory\n",
            "This file stores core information only (user info, preferences).\n",
        ]
        for item in unique_core:
            out_parts.append(f"{item}\n\n")
        out_parts.append("---\n\n*This file is automatically updated by nanobot.*")

        self.memory_file.write_text("".join(out_parts).strip() + "\n", encoding="utf-8")

        summary = f"Organized MEMORY.md: kept {len(unique_core)} core entries, moved {moved_count} non-core entries to daily files."
        return summary
    
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
    
    def get_memory_file(
        self, path: str, start_line: int | None = None, lines: int | None = None
    ) -> str:
        """
        Read a memory file by workspace-relative path.
        path: e.g. "memory/MEMORY.md", "memory/2026-02-06.md", or "MEMORY.md"
        """
        p = Path(path)
        if not p.is_absolute():
            if p.name == "MEMORY.md" and len(p.parts) <= 1:
                p = self.memory_dir / "MEMORY.md"
            else:
                p = self.workspace / p
        p = p.resolve()
        mem_resolved = self.memory_dir.resolve()
        if not p.exists() or not p.is_file():
            return f"File not found: {path}"
        try:
            p.relative_to(mem_resolved)
        except ValueError:
            return f"Path outside memory dir: {path}"
        try:
            content = p.read_text(encoding="utf-8")
        except Exception as e:
            return f"Error reading {path}: {e}"
        if start_line is not None and lines is not None:
            all_lines = content.split("\n")
            start = max(0, start_line - 1)
            end = min(len(all_lines), start + lines)
            content = "\n".join(all_lines[start:end])
        elif start_line is not None:
            all_lines = content.split("\n")
            start = max(0, start_line - 1)
            content = "\n".join(all_lines[start:])
        return content

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
