"""Shell execution tool."""

import asyncio
import os
import re
from pathlib import Path
from typing import Any

from nanobot.agent.tools.base import Tool


class ExecTool(Tool):
    """Tool to execute shell commands."""
    
    def __init__(
        self,
        timeout: int = 60,
        working_dir: str | None = None,
        deny_patterns: list[str] | None = None,
        allow_patterns: list[str] | None = None,
        restrict_to_workspace: bool = False,
        max_output_chars: int = 8000,
    ):
        self.timeout = timeout
        self.working_dir = working_dir
        self.deny_patterns = deny_patterns or [
            r"\brm\s+-[rf]{1,2}\b",
            r"\bdel\s+/[fq]\b",
            r"\brmdir\s+/s\b",
            r"\b(format|mkfs|diskpart)\b",
            r"\bdd\s+if=",
            r">\s*/dev/sd",
            r"\b(shutdown|reboot|poweroff)\b",
            r":\(\)\s*\{.*\};\s*:",
        ]
        self.allow_patterns = allow_patterns or []
        self.restrict_to_workspace = restrict_to_workspace
        self.max_output_chars = max_output_chars
    
    @property
    def name(self) -> str:
        return "exec"
    
    @property
    def description(self) -> str:
        return "Execute shell command. Returns output."
    
    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "Shell command to execute"
                },
                "working_dir": {
                    "type": "string",
                    "description": "Optional working directory"
                },
                "confirm": {
                    "type": "boolean",
                    "description": "Set true to confirm dangerous commands",
                    "default": False,
                }
            },
            "required": ["command"]
        }
    
    def _smart_truncate(self, text: str, max_chars: int) -> str:
        """智能截断：保留开头、结尾和关键行（错误、警告）。"""
        if len(text) <= max_chars:
            return text
        
        lines = text.split("\n")
        if len(lines) <= 20:
            return text[:max_chars] + f"\n... (truncated, {len(text) - max_chars} chars)"
        
        key_patterns = ["error", "warning", "fail", "exception", "错误", "警告", "失败"]
        key_lines = []
        other_lines = []
        
        for i, line in enumerate(lines):
            lower = line.lower()
            if any(p in lower for p in key_patterns):
                key_lines.append((i, line))
            else:
                other_lines.append((i, line))
        
        head_count = 5
        tail_count = 5
        head_lines = lines[:head_count]
        tail_lines = lines[-tail_count:] if len(lines) > head_count + tail_count else []
        
        result_parts = ["## Output (head)\n"]
        result_parts.extend(head_lines)
        
        if key_lines:
            result_parts.append("\n## Key lines\n")
            for i, line in key_lines[:10]:
                result_parts.append(f"L{i+1}: {line}")
        
        if tail_lines and tail_lines != head_lines:
            result_parts.append(f"\n## Output (tail, {len(lines) - tail_count} lines omitted)\n")
            result_parts.extend(tail_lines)
        
        result = "\n".join(result_parts)
        if len(result) > max_chars:
            result = result[:max_chars] + f"\n... (truncated)"
        
        return result
    
    async def execute(self, command: str, working_dir: str | None = None, confirm: bool = False, **kwargs: Any) -> str:
        cwd = working_dir or self.working_dir or os.getcwd()
        guard_error = self._guard_command(command, cwd, confirm)
        if guard_error:
            return guard_error
        
        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=self.timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                return f"Error: Command timed out after {self.timeout} seconds"
            
            output_parts = []
            
            if stdout:
                output_parts.append(stdout.decode("utf-8", errors="replace"))
            
            if stderr:
                stderr_text = stderr.decode("utf-8", errors="replace")
                if stderr_text.strip():
                    output_parts.append(f"STDERR:\n{stderr_text}")
            
            if process.returncode != 0:
                output_parts.append(f"\nExit code: {process.returncode}")
            
            result = "\n".join(output_parts) if output_parts else "(no output)"
            
            return self._smart_truncate(result, self.max_output_chars)
            
        except Exception as e:
            return f"Error executing command: {str(e)}"

    def _guard_command(self, command: str, cwd: str, confirm: bool = False) -> str | None:
        """Best-effort safety guard for potentially destructive commands. Requires confirm=true to execute dangerous commands."""
        cmd = command.strip()
        lower = cmd.lower()

        for pattern in self.deny_patterns:
            if re.search(pattern, lower):
                if confirm:
                    break  # User confirmed, allow execution
                return (
                    "This command matches potentially dangerous patterns (e.g. rm -rf, format, dd, shutdown). "
                    "If the user confirms they want to run it, call exec again with confirm=true."
                )

        if self.allow_patterns:
            if not any(re.search(p, lower) for p in self.allow_patterns):
                return "Error: Command blocked by safety guard (not in allowlist)"

        if self.restrict_to_workspace:
            if "..\\" in cmd or "../" in cmd:
                return "Error: Command blocked by safety guard (path traversal detected)"

            cwd_path = Path(cwd).resolve()

            win_paths = re.findall(r"[A-Za-z]:\\[^\\\"']+", cmd)
            posix_paths = re.findall(r"/[^\s\"']+", cmd)

            for raw in win_paths + posix_paths:
                try:
                    p = Path(raw).resolve()
                except Exception:
                    continue
                if cwd_path not in p.parents and p != cwd_path:
                    return "Error: Command blocked by safety guard (path outside working dir)"

        return None
