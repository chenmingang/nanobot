"""Short-term memory compaction: summarize older conversation to stay within context limits."""

from typing import Any

from loguru import logger


COMPACTION_SYSTEM = (
    "Summarize conversation concisely. Keep: decisions, TODOs, questions, constraints, facts. "
    "Output only summary."
)

NO_REPLY_TOKEN = "NO_REPLY"

MEMORY_FLUSH_SYSTEM = (
    "Pre-compaction memory flush. Store durable memories: core facts → MEMORY.md, "
    f"notes → daily file. Reply {NO_REPLY_TOKEN} if nothing to store."
)

MEMORY_FLUSH_PROMPT = (
    f"Store memories now (remember_core for core facts, append_daily for notes). "
    f"If nothing, reply {NO_REPLY_TOKEN}."
)

KEY_MESSAGE_PATTERNS = [
    "error", "fail", "exception", "错误", "失败",
    "todo", "task", "待办", "任务",
    "decide", "decision", "决定",
    "important", "关键", "重要",
    "confirm", "确认",
]


def _is_key_message(msg: dict[str, Any]) -> bool:
    """判断消息是否为关键消息（应保留）。"""
    content = msg.get("content", "")
    if not isinstance(content, str):
        return False
    lower = content.lower()
    return any(p in lower for p in KEY_MESSAGE_PATTERNS)


def _estimate_tokens(messages: list[dict[str, Any]]) -> int:
    """估算消息列表的 token 数（粗略：4 字符 ≈ 1 token）。"""
    total = 0
    for m in messages:
        content = m.get("content", "")
        if isinstance(content, str):
            total += len(content) // 4
        elif isinstance(content, list):
            for part in content:
                if isinstance(part, dict) and part.get("type") == "text":
                    total += len(part.get("text", "")) // 4
    return total


def select_messages_for_compaction(
    messages: list[dict[str, Any]],
    keep_recent: int = 20,
    keep_key_messages: bool = True,
    max_tokens: int = 8000,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """
    智能选择要压缩的消息。
    
    Args:
        messages: 所有消息
        keep_recent: 保留最近 N 条
        keep_key_messages: 是否保留关键消息
        max_tokens: 历史消息最大 token 数
    
    Returns:
        (要压缩的消息, 保留的消息)
    """
    n = len(messages)
    if n <= keep_recent:
        return [], messages
    
    recent = messages[-keep_recent:]
    old = messages[:-keep_recent]
    
    if not keep_key_messages:
        return old, recent
    
    key_indices = set()
    for i, msg in enumerate(old):
        if _is_key_message(msg):
            key_indices.add(i)
    
    to_compact = []
    to_keep = []
    
    for i, msg in enumerate(old):
        if i in key_indices:
            to_keep.append(msg)
        else:
            to_compact.append(msg)
    
    to_keep.extend(recent)
    
    current_tokens = _estimate_tokens(to_keep)
    if current_tokens > max_tokens:
        while len(to_keep) > keep_recent and current_tokens > max_tokens:
            removed = to_keep.pop(0)
            if removed not in recent:
                current_tokens -= len(removed.get("content", "")) // 4
    
    return to_compact, to_keep


def format_messages_for_summary(messages: list[dict[str, Any]], max_chars: int = 8000) -> str:
    """Format messages as text for summarization."""
    parts = []
    total_chars = 0
    
    for m in messages:
        role = m.get("role", "unknown")
        content = m.get("content", "")
        if isinstance(content, str):
            chunk = f"[{role}]: {content[:1000]}{'...' if len(content) > 1000 else ''}"
        else:
            chunk = f"[{role}]: (non-text content)"
        
        if total_chars + len(chunk) > max_chars:
            break
        parts.append(chunk)
        total_chars += len(chunk)
    
    return "\n\n".join(parts)


async def summarize_messages(
    provider: Any,
    messages: list[dict[str, Any]],
    model: str | None = None,
    max_tokens: int = 1500,
) -> str:
    """
    Summarize a list of messages using the LLM.

    Args:
        provider: LLMProvider instance.
        messages: Messages to summarize.
        model: Model to use.
        max_tokens: Max tokens for summary.

    Returns:
        Summary string, or fallback if summarization fails.
    """
    if not messages:
        return "No prior history."

    text = format_messages_for_summary(messages)
    summary_messages = [
        {"role": "system", "content": COMPACTION_SYSTEM},
        {"role": "user", "content": f"Summarize this conversation:\n\n{text}"},
    ]

    try:
        response = await provider.chat(
            messages=summary_messages,
            tools=None,
            model=model,
            max_tokens=max_tokens,
            temperature=0.3,
        )
        summary = (response.content or "").strip()
        if summary:
            return summary
    except Exception as e:
        logger.warning(f"Compaction summarization failed: {e}")

    return f"Context contained {len(messages)} messages. Summary unavailable."
