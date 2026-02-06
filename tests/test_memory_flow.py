"""Tests for memory flow: write -> reindex -> recall -> context injection."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from nanobot.agent.context import ContextBuilder
from nanobot.agent.memory import MemoryStore
from nanobot.agent.tools.memory_tools import MemorySearchTool
from nanobot.providers.base import LLMResponse
from nanobot.utils.helpers import today_date


# =============================================================================
# Memory write: append_daily creates daily file
# =============================================================================


def test_memory_store_append_daily_creates_daily_file(tmp_path: Path) -> None:
    """append_daily creates memory/YYYY-MM-DD.md with header when file is new."""
    store = MemoryStore(tmp_path)
    store.append_daily("Test session note")
    today_file = store.get_today_file()
    assert today_file.exists()
    content = today_file.read_text()
    assert today_date() in content
    assert "Test session note" in content


def test_memory_store_append_daily_appends_to_existing(tmp_path: Path) -> None:
    """append_daily appends to existing daily file."""
    store = MemoryStore(tmp_path)
    store.append_daily("First note")
    store.append_daily("Second note")
    content = store.get_today_file().read_text()
    assert "First note" in content
    assert "Second note" in content


# =============================================================================
# Context injection: memory_recall in build_messages
# =============================================================================


def test_context_builder_injects_memory_recall(tmp_path: Path) -> None:
    """build_messages with memory_recall includes it in system prompt."""
    ctx = ContextBuilder(tmp_path)
    recall = "[1] memory/MEMORY.md (line 1, score 0.9):\nUser prefers dark mode"
    messages = ctx.build_messages(
        history=[],
        current_message="hello",
        memory_recall=recall,
    )
    assert len(messages) >= 1
    system = messages[0]["content"]
    assert "Relevant memories" in system
    assert "User prefers dark mode" in system


def test_context_builder_skips_memory_recall_when_none(tmp_path: Path) -> None:
    """build_messages without memory_recall does not add recall section."""
    ctx = ContextBuilder(tmp_path)
    messages = ctx.build_messages(history=[], current_message="hello")
    system = messages[0]["content"]
    assert "Relevant memories" not in system


# =============================================================================
# Memory flush fallback: daily file created when LLM returns NO_REPLY
# =============================================================================


@pytest.fixture
def mock_provider_no_reply() -> MagicMock:
    """Provider that returns NO_REPLY (no tool calls) for memory flush."""
    p = MagicMock()
    resp = LLMResponse(content="NO_REPLY", tool_calls=[])
    p.chat = AsyncMock(return_value=resp)
    p.get_default_model = MagicMock(return_value="test-model")
    return p


@pytest.fixture
def agent_loop_minimal(tmp_path: Path, mock_provider_no_reply: MagicMock):
    """Minimal AgentLoop with temp workspace and mock provider."""
    from nanobot.bus.queue import MessageBus
    from nanobot.agent.loop import AgentLoop

    bus = MessageBus()
    loop = AgentLoop(
        bus=bus,
        provider=mock_provider_no_reply,
        workspace=tmp_path,
        model="test-model",
        compaction_threshold=2,
        compaction_keep_recent=1,
        compaction_memory_flush_enabled=True,
        memory_search_local_model="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        memory_search_store_path=str(tmp_path / "chroma"),
    )
    # Use tmp_path for sessions to avoid polluting ~/.nanobot
    loop.sessions.sessions_dir = tmp_path / "sessions"
    loop.sessions.sessions_dir.mkdir(parents=True, exist_ok=True)
    return loop


@pytest.mark.asyncio
async def test_memory_flush_fallback_creates_daily_file(
    tmp_path: Path, agent_loop_minimal
) -> None:
    """When memory flush runs and LLM returns NO_REPLY, fallback creates daily file."""
    from nanobot.session.manager import Session

    session = Session(key="test:123", compaction_count=0)
    for i in range(3):
        session.add_message("user", f"Message {i}")
        session.add_message("assistant", f"Reply {i}")
    session.compaction_count = 1  # Simulate compaction about to run

    await agent_loop_minimal._run_memory_flush_turn(session)

    store = MemoryStore(tmp_path)
    today_file = store.get_today_file()
    assert today_file.exists(), "Daily file should be created by fallback"
    content = today_file.read_text()
    assert "Session notes" in content
    assert "compaction threshold" in content


# =============================================================================
# Recall: _recall_memory formats results
# =============================================================================


@pytest.fixture
def mock_memory_search_tool(tmp_path: Path) -> MemorySearchTool:
    """MemorySearchTool with mocked index.search returning sample results."""
    tool = MemorySearchTool(
        workspace=tmp_path,
        store_path=str(tmp_path / "chroma"),
    )
    # Replace index.search with a mock that returns sample results
    tool.index.search = MagicMock(
        return_value=[
            {"path": "memory/MEMORY.md", "start_line": 1, "score": 0.9, "content": "User likes Python"},
            {"path": "memory/2026-02-06.md", "start_line": 5, "score": 0.8, "content": "Session note"},
        ]
    )
    return tool


@pytest.mark.asyncio
async def test_recall_memory_returns_formatted_results(
    agent_loop_minimal, mock_memory_search_tool: MemorySearchTool
) -> None:
    """_recall_memory returns formatted string from vector search."""
    agent_loop_minimal.tools.register(mock_memory_search_tool)

    result = await agent_loop_minimal._recall_memory("user preferences", top_k=5)

    assert result is not None
    assert "memory/MEMORY.md" in result
    assert "User likes Python" in result
    assert "memory/2026-02-06.md" in result
    assert "Session note" in result
    assert "[1]" in result and "[2]" in result


@pytest.mark.asyncio
async def test_recall_memory_returns_none_for_empty_query(agent_loop_minimal) -> None:
    """_recall_memory returns None for empty query."""
    result = await agent_loop_minimal._recall_memory("")
    assert result is None

    result = await agent_loop_minimal._recall_memory("   ")
    assert result is None


# =============================================================================
# Full flow: write -> recall -> context (integration)
# =============================================================================


@pytest.mark.asyncio
async def test_full_flow_write_then_recall(tmp_path: Path) -> None:
    """
    Full flow: write to memory -> (reindex) -> recall -> inject into context.
    Uses real MemoryStore; recall uses mock (chromadb/sentence-transformers optional).
    """
    # 1. Write to memory
    store = MemoryStore(tmp_path)
    store.append_core("User prefers Python and dark mode")
    store.append_daily("Discussed project X today")

    assert (tmp_path / "memory" / "MEMORY.md").exists()
    assert store.get_today_file().exists()

    # 2. Context with recall (simulate what agent does)
    ctx = ContextBuilder(tmp_path)
    mock_recall = "[1] memory/MEMORY.md: User prefers Python"
    messages = ctx.build_messages(
        history=[{"role": "user", "content": "hi"}, {"role": "assistant", "content": "hello"}],
        current_message="What do I prefer?",
        memory_recall=mock_recall,
    )

    # 3. Verify recall is in system prompt
    system = messages[0]["content"]
    assert "Relevant memories" in system
    assert "User prefers Python" in system
    assert "What do I prefer?" in messages[-1]["content"] or str(messages[-1])


# =============================================================================
# Memory write tools trigger reindex
# =============================================================================


@pytest.mark.asyncio
async def test_memory_write_tool_triggers_reindex(tmp_path: Path) -> None:
    """When remember_core is called, _reindex_memory_search is invoked."""
    from nanobot.bus.queue import MessageBus
    from nanobot.agent.loop import AgentLoop
    from nanobot.agent.tools.memory_tools import MemorySearchTool

    from nanobot.providers.base import ToolCallRequest

    mock_provider = MagicMock()
    resp_with_tool = LLMResponse(
        content="",
        tool_calls=[
            ToolCallRequest(
                id="tc1",
                name="remember_core",
                arguments={"content": "User likes tea"},
            )
        ],
    )
    # First call: tool call. Second call: no more tools (done)
    resp_done = LLMResponse(content="Done", tool_calls=[])
    mock_provider.chat = AsyncMock(side_effect=[resp_with_tool, resp_done])
    mock_provider.get_default_model = MagicMock(return_value="test")

    bus = MessageBus()
    loop = AgentLoop(
        bus=bus,
        provider=mock_provider,
        workspace=tmp_path,
        model="test",
        memory_search_local_model="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        memory_search_store_path=str(tmp_path / "chroma"),
    )
    loop.sessions.sessions_dir = tmp_path / "sessions"
    loop.sessions.sessions_dir.mkdir(parents=True, exist_ok=True)

    # Mock _reindex_memory_search to verify it's called
    reindex_called = []

    async def track_reindex():
        reindex_called.append(True)

    loop._reindex_memory_search = AsyncMock(side_effect=track_reindex)

    from nanobot.bus.events import InboundMessage

    msg = InboundMessage(
        channel="cli", sender_id="user", chat_id="test", content="Remember I like tea"
    )

    await loop._process_message(msg)

    assert len(reindex_called) >= 1, "_reindex_memory_search should be called after remember_core"
