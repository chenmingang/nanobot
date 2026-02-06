"""Short-term memory compaction: summarize older conversation to stay within context limits."""

from typing import Any

from loguru import logger


COMPACTION_SYSTEM = (
    "You are a summarization assistant. Summarize the following conversation concisely. "
    "Preserve key decisions, TODO items, open questions, constraints, and important facts. "
    "Output only the summary, no preamble."
)

NO_REPLY_TOKEN = "NO_REPLY"

MEMORY_FLUSH_SYSTEM = (
    "Pre-compaction memory flush turn. The session is near auto-compaction; "
    "capture durable memories to disk. Core/user-requested facts → MEMORY.md (remember_core). "
    "Other notes (session summaries, TODO, discussion points) → memory/YYYY-MM-DD.md (append_daily). "
    f"You may reply, but usually {NO_REPLY_TOKEN} is correct if nothing to store."
)

MEMORY_FLUSH_PROMPT = (
    "Pre-compaction memory flush. Store durable memories now "
    "(use remember_core for core facts, append_daily for other notes). "
    f"If nothing to store, reply with {NO_REPLY_TOKEN}."
)


def format_messages_for_summary(messages: list[dict[str, Any]]) -> str:
    """Format messages as text for summarization."""
    parts = []
    for m in messages:
        role = m.get("role", "unknown")
        content = m.get("content", "")
        if isinstance(content, str):
            parts.append(f"[{role}]: {content[:2000]}{'...' if len(content) > 2000 else ''}")
        else:
            parts.append(f"[{role}]: (non-text content)")
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
