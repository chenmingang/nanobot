"""Agent loop: the core processing engine."""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from loguru import logger

from nanobot.bus.events import InboundMessage, OutboundMessage
from nanobot.bus.queue import MessageBus
from nanobot.providers.base import LLMProvider
from nanobot.agent.compaction import (
    MEMORY_FLUSH_PROMPT,
    MEMORY_FLUSH_SYSTEM,
    NO_REPLY_TOKEN,
    summarize_messages,
)
from nanobot.agent.context import ContextBuilder
from nanobot.agent.memory import MemoryStore
from nanobot.agent.tools.registry import ToolRegistry
from nanobot.agent.tools.filesystem import ReadFileTool, WriteFileTool, EditFileTool, ListDirTool
from nanobot.agent.tools.memory_tools import (
    AppendDailyTool,
    MemoryGetTool,
    MemorySearchTool,
    OrganizeMemoryTool,
    RememberCoreTool,
    RememberTool,
)
from nanobot.agent.tools.shell import ExecTool
from nanobot.agent.tools.web import WebSearchTool, WebFetchTool
from nanobot.agent.tools.message import MessageTool
from nanobot.agent.tools.spawn import SpawnTool
from nanobot.agent.subagent import SubagentManager
from nanobot.session.manager import SessionManager

if TYPE_CHECKING:
    from nanobot.session.manager import Session

MEMORY_WRITE_TOOLS = frozenset(("remember_core", "append_daily", "organize_memory", "remember"))
# Tools we invoke in code or do not expose to LLM; hide to avoid diluting useful tools.
# memory_search: we call _recall_memory() before each turn. web_*: hidden per config.
TOOLS_HIDDEN_FROM_LLM = frozenset(("memory_search", "web_search", "web_fetch"))

# 模型返回空 content 时的兜底回复（保证用户总有回应）
EMPTY_CONTENT_FALLBACK = "模型返回了空内容，请重试或换一种问法。"

# System instruction when processing cron/scheduled tasks: remind model to say "时间到了" not "X分钟后提醒"
CRON_SYSTEM_INSTRUCTION = """## Scheduled task (running now)
This turn is a scheduled task that is **executing now**. If the user message is a reminder to deliver, reply with 「⏰ 时间到了！」 then the reminder content; do NOT say you will remind later or in X minutes. If the user message is a task (e.g. run something, check something), use tools as needed and reply with the result."""


class AgentLoop:
    """
    The agent loop is the core processing engine.
    
    It:
    1. Receives messages from the bus
    2. Builds context with history, memory, skills
    3. Calls the LLM
    4. Executes tool calls
    5. Sends responses back
    """
    
    def __init__(
        self,
        bus: MessageBus,
        provider: LLMProvider,
        workspace: Path,
        model: str | None = None,
        max_iterations: int = 20,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        max_history_messages: int = 50,
        compaction_enabled: bool = True,
        compaction_threshold: int = 60,
        compaction_keep_recent: int = 20,
        compaction_memory_flush_enabled: bool = True,
        api_key: str | None = None,
        api_base: str | None = None,
        memory_search_local_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        memory_search_store_path: str | None = None,
        brave_api_key: str | None = None
    ):
        self.bus = bus
        self.provider = provider
        self.workspace = workspace
        self.model = model or provider.get_default_model()
        self.max_iterations = max_iterations
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.max_history_messages = max_history_messages
        self.compaction_enabled = compaction_enabled
        self.compaction_threshold = compaction_threshold
        self.compaction_keep_recent = compaction_keep_recent
        self.compaction_memory_flush_enabled = compaction_memory_flush_enabled
        self.api_key = api_key
        self.api_base = api_base
        self.memory_search_local_model = memory_search_local_model
        self.memory_search_store_path = memory_search_store_path
        self.brave_api_key = brave_api_key
        
        self.context = ContextBuilder(workspace)
        self.sessions = SessionManager(workspace)
        self.tools = ToolRegistry()
        self.subagents = SubagentManager(
            provider=provider,
            workspace=workspace,
            bus=bus,
            model=self.model,
            brave_api_key=brave_api_key,
            # Keep subagent usage cheaper than the main agent by default.
            max_tokens=self.max_tokens,
            temperature=self.temperature,
        )
        
        self._running = False
        self._register_default_tools()

    def _get_llm_tool_definitions(self) -> list[dict[str, Any]]:
        """Tool definitions for the LLM, excluding tools we call in code (e.g. memory_search)."""
        return [
            d for d in self.tools.get_definitions()
            if d.get("function", {}).get("name") not in TOOLS_HIDDEN_FROM_LLM
        ]
    
    def _register_default_tools(self) -> None:
        """Register the default set of tools."""
        # File tools
        self.tools.register(ReadFileTool())
        self.tools.register(WriteFileTool())
        self.tools.register(EditFileTool())
        self.tools.register(ListDirTool())

        # Memory tools
        self.tools.register(RememberTool(self.workspace))
        self.tools.register(RememberCoreTool(self.workspace))
        self.tools.register(AppendDailyTool(self.workspace))
        self.tools.register(OrganizeMemoryTool(self.workspace))
        self.tools.register(MemorySearchTool(
            self.workspace,
            local_model=self.memory_search_local_model,
            store_path=self.memory_search_store_path,
        ))
        self.tools.register(MemoryGetTool(self.workspace))

        # Shell tool
        self.tools.register(ExecTool(working_dir=str(self.workspace)))
        
        # Web tools
        self.tools.register(WebSearchTool(api_key=self.brave_api_key))
        self.tools.register(WebFetchTool())
        
        # Message tool
        message_tool = MessageTool(send_callback=self.bus.publish_outbound)
        self.tools.register(message_tool)
        
        # Spawn tool (for subagents)
        spawn_tool = SpawnTool(manager=self.subagents)
        self.tools.register(spawn_tool)

    async def _run_memory_flush_turn(self, session: "Session") -> None:
        """
        Pre-compaction memory flush: run a silent agent turn to store durable
        memories (remember_core, append_daily) before compaction.
        If the LLM does not call append_daily, we always append a minimal session
        note so that the daily file (memory/YYYY-MM-DD.md) is created.
        """
        history = session.get_history(max_messages=self.max_history_messages)
        messages = [
            {"role": "system", "content": MEMORY_FLUSH_SYSTEM},
            *[{"role": m["role"], "content": m["content"]} for m in history],
            {"role": "user", "content": MEMORY_FLUSH_PROMPT},
        ]

        append_daily_called = False
        max_flush_iterations = 5
        for _ in range(max_flush_iterations):
            response = await self.provider.chat(
                messages=messages,
                tools=self._get_llm_tool_definitions(),
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=0.3,
            )

            if response.has_tool_calls:
                tool_call_dicts = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {"name": tc.name, "arguments": json.dumps(tc.arguments)},
                    }
                    for tc in response.tool_calls
                ]
                messages = self.context.add_assistant_message(
                    messages,
                    response.content,
                    tool_call_dicts,
                    reasoning_content=getattr(response, "reasoning_content", None),
                    thinking_blocks=getattr(response, "thinking_blocks", None),
                )
                for tool_call in response.tool_calls:
                    if tool_call.name == "append_daily":
                        append_daily_called = True
                    result = await self.tools.execute(tool_call.name, tool_call.arguments)
                    messages = self.context.add_tool_result(
                        messages, tool_call.id, tool_call.name, result
                    )
            else:
                content = (response.content or "").strip()
                if content.upper().startswith(NO_REPLY_TOKEN):
                    logger.debug("Memory flush: NO_REPLY (nothing to store)")
                else:
                    logger.debug(f"Memory flush reply: {content[:100]}...")
                break

        # Fallback: always ensure today's daily file exists when compaction runs
        if not append_daily_called and history:
            try:
                store = MemoryStore(self.workspace)
                n = len(session.messages)
                note = (
                    f"Session notes: conversation reached compaction threshold ({n} messages). "
                    "Key points may be in prior compaction summary or MEMORY.md."
                )
                store.append_daily(note)
                logger.debug("Memory flush: auto-appended minimal daily note (LLM did not call append_daily)")
            except Exception as e:
                logger.warning("Memory flush: fallback append_daily failed: {}", e)

        session.memory_flush_compaction_count = session.compaction_count
        self.sessions.save(session)

        # Reindex vector memory after flush (engineering trigger, not model-dependent)
        await self._reindex_memory_search()

    async def _reindex_memory_search(self) -> None:
        """
        Trigger ChromaDB index update programmatically.
        Runs in thread pool to avoid blocking (embedding is CPU-bound).
        """
        tool = self.tools.get("memory_search")
        if not isinstance(tool, MemorySearchTool):
            return
        try:
            n = await asyncio.to_thread(tool.index.index_paths)
            if n > 0:
                logger.debug("Memory search index updated: {} chunks", n)
        except Exception as e:
            logger.warning("Memory search reindex failed: {}", e)

    async def _recall_memory(self, query: str, top_k: int = 5) -> str | None:
        """
        Engineering recall: run vector search on memory and return formatted results.
        Called automatically before each user message. Runs in thread pool.
        Returns None if no results or search unavailable.
        """
        tool = self.tools.get("memory_search")
        if not isinstance(tool, MemorySearchTool):
            return None
        if not query or not query.strip():
            return None
        try:
            results = await asyncio.to_thread(tool.index.search, query.strip(), top_k)
        except Exception as e:
            logger.warning("Memory recall failed: {}", e)
            return None
        if not results:
            logger.info("Memory recall: 0 results for query={}", query.strip()[:50])
            return None
        logger.info("Memory recall: {} results for query={}", len(results), query.strip()[:50])
        parts = []
        for i, r in enumerate(results, 1):
            parts.append(f"[{i}] {r['path']} (line {r['start_line']}, score {r['score']}):\n{r['content']}")
        return "\n\n".join(parts)

    async def _maybe_compact_session(self, session: "Session") -> None:
        """
        Short-term memory compression: when messages exceed threshold,
        run pre-compaction memory flush (if enabled), then summarize older
        messages and keep only recent ones.
        """
        if not self.compaction_enabled:
            return
        n = len(session.messages)
        if n <= self.compaction_threshold:
            return
        keep = self.compaction_keep_recent
        if keep >= n:
            return

        # Pre-compaction memory flush: once per compaction cycle
        if self.compaction_memory_flush_enabled:
            if session.memory_flush_compaction_count != session.compaction_count:
                try:
                    await self._run_memory_flush_turn(session)
                    logger.info("Pre-compaction memory flush completed for session {}", session.key)
                except Exception as e:
                    logger.warning("Pre-compaction memory flush failed: {}", e)

        old = session.messages[:-keep]
        recent = session.messages[-keep:]

        # Include prior summary as context for merged summarization
        prior = session.compaction_summary
        if prior:
            old = [{"role": "user", "content": f"Prior summary: {prior}"}] + old

        try:
            new_summary = await summarize_messages(
                self.provider, old, model=self.model, max_tokens=1500
            )
            if new_summary:
                session.compaction_summary = new_summary
        except Exception as e:
            logger.warning(f"Compaction summarization failed: {e}")

        session.messages = recent
        session.compaction_count = (session.compaction_count or 0) + 1
        session.updated_at = datetime.now()
        self.sessions.save(session)
        logger.info(f"Compacted session {session.key}: {n} -> {keep} messages")

    async def run(self) -> None:
        """Run the agent loop, processing messages from the bus."""
        self._running = True
        logger.info("Agent loop started")
        
        while self._running:
            try:
                # Wait for next message
                msg = await asyncio.wait_for(
                    self.bus.consume_inbound(),
                    timeout=1.0
                )
                
                # Process it
                try:
                    response = await self._process_message(msg)
                    if response:
                        await self.bus.publish_outbound(response)
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                    # Send error response
                    await self.bus.publish_outbound(OutboundMessage(
                        channel=msg.channel,
                        chat_id=msg.chat_id,
                        content=f"Sorry, I encountered an error: {str(e)}"
                    ))
            except asyncio.TimeoutError:
                continue
    
    def stop(self) -> None:
        """Stop the agent loop."""
        self._running = False
        logger.info("Agent loop stopping")
    
    async def _process_message(self, msg: InboundMessage) -> OutboundMessage | None:
        """
        Process a single inbound message.
        
        Args:
            msg: The inbound message to process.
        
        Returns:
            The response message, or None if no response needed.
        """
        # Handle system messages (subagent announces)
        # The chat_id contains the original "channel:chat_id" to route back to
        if msg.channel == "system":
            return await self._process_system_message(msg)
        
        logger.info(f"Processing message from {msg.channel}:{msg.sender_id}")
        
        # Get or create session
        session = self.sessions.get_or_create(msg.session_key)
        
        # Update tool contexts
        message_tool = self.tools.get("message")
        if isinstance(message_tool, MessageTool):
            message_tool.set_context(msg.channel, msg.chat_id)
        
        spawn_tool = self.tools.get("spawn")
        if isinstance(spawn_tool, SpawnTool):
            spawn_tool.set_context(msg.channel, msg.chat_id)

        # Short-term memory compression: summarize older messages if needed
        await self._maybe_compact_session(session)

        # Engineering recall: semantic search on memory, inject relevant chunks into context
        memory_recall = await self._recall_memory(msg.content, top_k=5)

        # Build initial messages (use get_history for LLM-formatted messages)
        messages = self.context.build_messages(
            history=session.get_history(max_messages=self.max_history_messages),
            current_message=msg.content,
            media=msg.media if msg.media else None,
            compaction_summary=session.compaction_summary,
            memory_recall=memory_recall,
            cron_instruction=CRON_SYSTEM_INSTRUCTION if msg.channel == "cron" else None,
        )
        
        # Agent loop
        iteration = 0
        final_content = None
        memory_tools_called: set[str] = set()
        all_tools_called: set[str] = set()

        while iteration < self.max_iterations:
            iteration += 1
            
            # Call LLM
            response = await self.provider.chat(
                messages=messages,
                tools=self._get_llm_tool_definitions(),
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature
            )
            
            # Handle tool calls
            if response.has_tool_calls:
                # 飞书：把助手带 tool_calls 时的 content（思考/说明）单独发一条
                thinking_text = (response.content or "").strip()
                if msg.channel == "feishu" and thinking_text:
                    await self.bus.publish_outbound(OutboundMessage(
                        channel=msg.channel,
                        chat_id=msg.chat_id,
                        content="━━ 💭 助手思考 ━━\n\n" + thinking_text,
                    ))
                elif msg.channel == "feishu" and not thinking_text:
                    logger.debug("Feishu: assistant had tool_calls but empty content, skip thinking message")
                # Add assistant message with tool calls
                tool_call_dicts = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.name,
                            "arguments": json.dumps(tc.arguments)  # Must be JSON string
                        }
                    }
                    for tc in response.tool_calls
                ]
                messages = self.context.add_assistant_message(
                    messages,
                    response.content,
                    tool_call_dicts,
                    reasoning_content=getattr(response, "reasoning_content", None),
                    thinking_blocks=getattr(response, "thinking_blocks", None),
                )
                
                # Execute tools
                for tool_call in response.tool_calls:
                    args_str = json.dumps(tool_call.arguments)
                    logger.debug(f"Executing tool: {tool_call.name} with arguments: {args_str}")
                    all_tools_called.add(tool_call.name)
                    result = await self.tools.execute(tool_call.name, tool_call.arguments)
                    if tool_call.name in MEMORY_WRITE_TOOLS:
                        memory_tools_called.add(tool_call.name)
                    messages = self.context.add_tool_result(
                        messages, tool_call.id, tool_call.name, result
                    )
            else:
                # No tool calls, we're done
                final_content = response.content
                break
        
        if final_content is None:
            final_content = "I've completed processing but have no response to give."
        elif not (final_content or "").strip():
            logger.info("Model returned empty content (finish_reason=stop, no tool_calls)")
            final_content = EMPTY_CONTENT_FALLBACK

        # Tool call notification via channel (e.g. Feishu): notify when tools called, remind when none
        if msg.channel == "feishu":
            if all_tools_called:
                tool_status = f"✓ 已调用工具: {', '.join(sorted(all_tools_called))}"
            else:
                tool_status = "⚠️ 提醒：本轮未调用任何工具，模型可能只是描述了操作"
            await self.bus.publish_outbound(OutboundMessage(
                channel=msg.channel,
                chat_id=msg.chat_id,
                content=tool_status,
            ))

        # Reindex vector memory after memory write tools (engineering trigger)
        if memory_tools_called:
            await self._reindex_memory_search()
        
        # Save to session
        session.add_message("user", msg.content)
        session.add_message("assistant", final_content)
        self.sessions.save(session)
        
        return OutboundMessage(
            channel=msg.channel,
            chat_id=msg.chat_id,
            content=final_content
        )
    
    async def _process_system_message(self, msg: InboundMessage) -> OutboundMessage | None:
        """
        Process a system message (e.g., subagent announce).
        
        The chat_id field contains "original_channel:original_chat_id" to route
        the response back to the correct destination.
        """
        logger.info(f"Processing system message from {msg.sender_id}")
        
        # Parse origin from chat_id (format: "channel:chat_id")
        if ":" in msg.chat_id:
            parts = msg.chat_id.split(":", 1)
            origin_channel = parts[0]
            origin_chat_id = parts[1]
        else:
            # Fallback
            origin_channel = "cli"
            origin_chat_id = msg.chat_id
        
        # Use the origin session for context
        session_key = f"{origin_channel}:{origin_chat_id}"
        session = self.sessions.get_or_create(session_key)
        
        # Update tool contexts
        message_tool = self.tools.get("message")
        if isinstance(message_tool, MessageTool):
            message_tool.set_context(origin_channel, origin_chat_id)
        
        spawn_tool = self.tools.get("spawn")
        if isinstance(spawn_tool, SpawnTool):
            spawn_tool.set_context(origin_channel, origin_chat_id)

        await self._maybe_compact_session(session)

        # Engineering recall: semantic search on memory
        memory_recall = await self._recall_memory(msg.content, top_k=5)

        # Build messages with the announce content
        messages = self.context.build_messages(
            history=session.get_history(max_messages=self.max_history_messages),
            current_message=msg.content,
            compaction_summary=session.compaction_summary,
            memory_recall=memory_recall,
        )
        
        # Agent loop (limited for announce handling)
        iteration = 0
        final_content = None
        memory_tools_called: set[str] = set()
        
        while iteration < self.max_iterations:
            iteration += 1
            
            response = await self.provider.chat(
                messages=messages,
                tools=self._get_llm_tool_definitions(),
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature
            )
            
            if response.has_tool_calls:
                thinking_text = (response.content or "").strip()
                if origin_channel == "feishu" and thinking_text:
                    await self.bus.publish_outbound(OutboundMessage(
                        channel=origin_channel,
                        chat_id=origin_chat_id,
                        content="━━ 💭 助手思考 ━━\n\n" + thinking_text,
                    ))
                tool_call_dicts = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.name,
                            "arguments": json.dumps(tc.arguments)
                        }
                    }
                    for tc in response.tool_calls
                ]
                messages = self.context.add_assistant_message(
                    messages,
                    response.content,
                    tool_call_dicts,
                    reasoning_content=getattr(response, "reasoning_content", None),
                    thinking_blocks=getattr(response, "thinking_blocks", None),
                )
                
                for tool_call in response.tool_calls:
                    args_str = json.dumps(tool_call.arguments)
                    logger.debug(f"Executing tool: {tool_call.name} with arguments: {args_str}")
                    result = await self.tools.execute(tool_call.name, tool_call.arguments)
                    if tool_call.name in MEMORY_WRITE_TOOLS:
                        memory_tools_called.add(tool_call.name)
                    messages = self.context.add_tool_result(
                        messages, tool_call.id, tool_call.name, result
                    )
            else:
                final_content = response.content
                break
        
        if final_content is None:
            final_content = "Background task completed."
        elif not (final_content or "").strip():
            logger.info("Model returned empty content (system message path)")
            final_content = EMPTY_CONTENT_FALLBACK

        if memory_tools_called:
            await self._reindex_memory_search()
        
        # Save to session (mark as system message in history)
        session.add_message("user", f"[System: {msg.sender_id}] {msg.content}")
        session.add_message("assistant", final_content)
        self.sessions.save(session)
        
        return OutboundMessage(
            channel=origin_channel,
            chat_id=origin_chat_id,
            content=final_content
        )
    
    async def process_direct(self, content: str, session_key: str = "cli:direct") -> str:
        """
        Process a message directly (for CLI usage).
        
        Args:
            content: The message content.
            session_key: Session identifier (e.g. "cli:direct", "cron:job_id").
                        Used as channel:chat_id so cron sessions get channel="cron".
        
        Returns:
            The agent's response.
        """
        if ":" in session_key:
            channel, chat_id = session_key.split(":", 1)
        else:
            channel, chat_id = "cli", session_key or "direct"
        msg = InboundMessage(
            channel=channel,
            sender_id="user",
            chat_id=chat_id,
            content=content
        )
        response = await self._process_message(msg)
        return response.content if response else ""
