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
            # Remove date markers - only store core content without timestamps
            entry = f"\n\n---\n\n{content.strip()}"
            self.memory_file.write_text(existing + entry, encoding="utf-8")
        else:
            header = "# Long-term Memory\nThis file stores core information only (user info, preferences).\n"
            self.memory_file.write_text(header + "\n" + content.strip(), encoding="utf-8")

    def append_daily(self, content: str) -> None:
        """Append session notes and secondary facts to memory/YYYY-MM-DD.md."""
        self.append_today(content)

    # 整理时的分类顺序（所有条目保留，仅调整分类与顺序）
    SECTION_ORDER = (
        "用户信息 / User Information",
        "偏好设置 / Preferences",
        "项目上下文 / Project Context",
        "重要笔记 / Important Notes",
        "其他 / Other",
    )

    def _normalize_entry(self, content: str) -> str:
        """优化单条描述：统一空白、去掉多余空行，保持结构清晰。"""
        lines = [line.rstrip() for line in content.strip().split("\n")]
        out: list[str] = []
        prev_blank = False
        for line in lines:
            is_blank = not line.strip()
            if is_blank and prev_blank:
                continue
            prev_blank = is_blank
            out.append(line)
        return "\n".join(out).strip()

    def organize_long_term(self) -> str:
        """
        整理 MEMORY.md：保留所有要求与内容，仅按分类重新排列顺序，并优化描述格式。
        不移动、不删除任何条目；不写入日期文件。
        """
        import re

        if not self.memory_file.exists():
            return "MEMORY.md 不存在，无需整理。"

        raw = self.memory_file.read_text(encoding="utf-8")

        categories = [
            ("用户信息 / User Information", ["用户", "姓名", "名字", "我是", "邮箱", "电话", "user", "name", "i am", "email", "phone", "我的"]),
            ("偏好设置 / Preferences", ["偏好", "喜欢", "不喜欢", "习惯", "希望", "prefer", "like", "dislike", "habit", "want", "常用", "习惯用", "问候", "语音"]),
            ("项目上下文 / Project Context", ["项目", "工作", "代码", "开发", "project", "work", "code", "develop", "仓库", "repo", "路径", "目录"]),
            ("重要笔记 / Important Notes", ["重要", "注意", "提醒", "记住", "important", "note", "remember", "务必", "必须"]),
        ]
        other_title = "其他 / Other"

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
                if re.match(r"^## \d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}$", stripped):
                    continue
                if stripped.lower() in placeholders:
                    continue
                if stripped in ("## User Information", "## Preferences", "## Project Context", "## Important Notes"):
                    continue
                content_lines.append(line)
            content = "\n".join(content_lines).strip()
            if not content or len(content) < 2:
                continue
            skip_phrases = ("# long-term memory", "automatically updated", "this file stores", "core information only")
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
            return "MEMORY.md 无有效条目可整理（可能为空或仅含模板）。"

        # 按分类分组，并去重（同一分类内内容完全一致只保留一条）
        by_section: dict[str, list[str]] = {s: [] for s in self.SECTION_ORDER}
        seen_norm: set[str] = set()
        for content, section in entries:
            norm = " ".join(content.split()).strip()
            if norm and norm not in seen_norm:
                seen_norm.add(norm)
                by_section.setdefault(section, []).append(content)

        # 按固定顺序写出，每条做描述优化
        out_parts = [
            "# Long-term Memory\n",
            "This file stores core information only (user info, preferences).\n",
        ]
        total = 0
        for section in self.SECTION_ORDER:
            items = by_section.get(section, [])
            if not items:
                continue
            out_parts.append(f"## {section}\n\n")
            for item in items:
                out_parts.append(self._normalize_entry(item) + "\n\n")
                total += 1
        out_parts.append("---\n\n*This file is automatically updated by nanobot.*")

        self.memory_file.write_text("".join(out_parts).strip() + "\n", encoding="utf-8")
        return f"已整理 MEMORY.md：保留全部 {total} 条内容，按分类调整顺序并优化描述格式。"
    
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
