"""Feishu channel implementation.

This channel handles:
  - Outbound messaging to Feishu chats using the HTTP OpenAPI (text, file, image).
  - Inbound Feishu events via Feishu Python SDK WebSocket client
    (    im.message.receive_v1): text, file, and image messages are forwarded into
    the nanobot bus; files and images are downloaded to nanobot's media dir.

The WebSocket client is implemented using the official `lark-oapi` SDK:
https://open.feishu.cn/document/server-side-sdk/python--sdk/handle-events
"""

from __future__ import annotations

import asyncio
import json
import mimetypes
import re
from pathlib import Path
from typing import Any, TYPE_CHECKING

import httpx
from loguru import logger

from nanobot.bus.events import OutboundMessage
from nanobot.bus.queue import MessageBus
from nanobot.channels.base import BaseChannel
from nanobot.utils.helpers import get_media_path

if TYPE_CHECKING:  # only for type checkers; avoids runtime import issues
    from nanobot.config.schema import ChannelsConfig

def _shorten(text: str, limit: int = 500) -> str:
    text = (text or "").replace("\r\n", "\n").replace("\r", "\n")
    if len(text) <= limit:
        return text
    return text[:limit] + "…"

def _safe_file_key(key: str, default_ext: str = "") -> str:
    """Turn Feishu file_key/image_key into a safe local filename."""
    safe = re.sub(r"[^\w\-.]", "_", (key or "")[:64])
    return (safe or "file") + default_ext

try:
    import lark_oapi as lark
    from lark_oapi.api.im.v1.model.p2_im_message_receive_v1 import (
        P2ImMessageReceiveV1,
    )
except Exception as _e:  # pragma: no cover - optional dependency
    lark = None  # type: ignore[assignment]
    P2ImMessageReceiveV1 = Any  # type: ignore[assignment]
    _lark_import_error = _e
else:
    _lark_import_error = None


class FeishuChannel(BaseChannel):
    """Feishu channel using Feishu OpenAPI for outbound messages."""

    name = "feishu"

    def __init__(self, config: Any, bus: MessageBus):
        super().__init__(config, bus)
        # At runtime we treat config as a generic object with the attributes
        # defined in ChannelsConfig.FeishuConfig (tenant_access_token, app_id, etc.)
        self.config = config
        self._client: httpx.AsyncClient | None = None
        self._tenant_access_token: str = ""
        # WebSocket client from lark-oapi for inbound events
        self._ws_client: Any | None = None
        self._ws_task: asyncio.Task | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        # Track "thinking" messages: chat_id -> (message_id, timer_task)
        self._thinking_messages: dict[str, tuple[str, asyncio.Task]] = {}
        # Threshold: delay before showing "thinking..." (ms)
        self._thinking_threshold_ms = 1000  # 1 seconds

    async def _ensure_tenant_access_token(self) -> bool:
        """Ensure we have a tenant_access_token, fetching it if needed."""
        # 1) Explicit token in config
        if self.config.tenant_access_token:
            self._tenant_access_token = self.config.tenant_access_token
            return True

        # 2) App credentials -> fetch tenant access token
        if not self.config.app_id or not self.config.app_secret:
            logger.error(
                "Feishu not configured: need either tenant_access_token or app_id/app_secret"
            )
            return False

        url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
        payload = {
            "app_id": self.config.app_id,
            "app_secret": self.config.app_secret,
        }
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(url, json=payload)
            if resp.status_code != 200:
                logger.error(
                    f"Feishu auth failed: HTTP {resp.status_code} - {resp.text[:200]}"
                )
                return False
            data = resp.json()
            if data.get("code") != 0:
                logger.error(f"Feishu auth error: {data}")
                return False
            token = data.get("tenant_access_token")
            if not token:
                logger.error("Feishu auth response missing tenant_access_token")
                return False
            self._tenant_access_token = token
            logger.info("Feishu tenant_access_token acquired via app_id/app_secret")
            return True
        except Exception as e:  # pragma: no cover - network/runtime failures
            logger.error(f"Error fetching Feishu tenant_access_token: {e}")
            return False

    async def _download_feishu_file(self, file_key: str) -> str | None:
        """Download file from Feishu by file_key; save to nanobot media dir. Returns local path or None."""
        if not self._client or not self._tenant_access_token:
            return None
        media_dir = get_media_path()
        url = f"https://open.feishu.cn/open-apis/im/v1/files/{file_key}"
        headers = {"Authorization": f"Bearer {self._tenant_access_token}"}
        try:
            resp = await self._client.get(url, headers=headers)
            if resp.status_code != 200:
                logger.warning("Feishu file download failed: HTTP {} - {}", resp.status_code, resp.text[:200])
                return None
            # Response may be file bytes or redirect was followed
            ext = ""
            cd = resp.headers.get("content-disposition") or ""
            if "filename=" in cd:
                m = re.search(r"filename\*?=(?:UTF-8'')?([^;\s]+)", cd)
                if m:
                    ext = Path(m.group(1).strip('"')).suffix
            local_path = media_dir / _safe_file_key(file_key, ext or ".bin")
            local_path.write_bytes(resp.content)
            logger.info("Feishu file downloaded: file_key={} -> {}", file_key[:32], local_path)
            return str(local_path)
        except Exception as e:  # pragma: no cover
            logger.error("Feishu file download error: {}", e)
            return None

    async def _download_feishu_image(self, image_key: str) -> str | None:
        """Download image from Feishu by image_key; save to nanobot media dir. Returns local path or None."""
        if not self._client or not self._tenant_access_token:
            return None
        media_dir = get_media_path()
        url = f"https://open.feishu.cn/open-apis/im/v1/images/{image_key}"
        headers = {"Authorization": f"Bearer {self._tenant_access_token}"}
        try:
            resp = await self._client.get(url, headers=headers)
            if resp.status_code != 200:
                logger.warning("Feishu image download failed: HTTP {} - {}", resp.status_code, resp.text[:200])
                return None
            ext = ".jpg"
            ct = (resp.headers.get("content-type") or "").lower()
            if "png" in ct:
                ext = ".png"
            elif "gif" in ct:
                ext = ".gif"
            elif "webp" in ct:
                ext = ".webp"
            local_path = media_dir / _safe_file_key(image_key, ext)
            local_path.write_bytes(resp.content)
            logger.info("Feishu image downloaded: image_key={} -> {}", image_key[:32], local_path)
            return str(local_path)
        except Exception as e:  # pragma: no cover
            logger.error("Feishu image download error: {}", e)
            return None

    async def _handle_inbound_media(
        self,
        sender_id: str,
        chat_id: str,
        metadata: dict[str, Any],
        download_coro: Any,
        label: str,
    ) -> None:
        """Await download coroutine and forward result to bus (for file/image messages)."""
        path = await download_coro
        content = f"[{label}: {path}]" if path else f"[{label}: download failed]"
        await self._handle_message(
            sender_id=sender_id,
            chat_id=chat_id,
            content=content,
            media=[path] if path else [],
            metadata=metadata,
        )

    async def start(self) -> None:
        """Start Feishu channel.

        - Ensures we have a tenant access token for outbound HTTP messages.
        - Starts the Feishu WebSocket client (if `lark-oapi` is installed) to
          receive `im.message.receive_v1` events and forward them into the bus.
        """
        self._loop = asyncio.get_running_loop()

        ok = await self._ensure_tenant_access_token()
        if not ok:
            logger.error("Feishu channel disabled due to auth configuration error")
            return

        self._running = True
        self._client = httpx.AsyncClient(timeout=15)

        # Try to start inbound WebSocket client if lark-oapi is available
        self._start_ws_client()

        logger.info(
            "Feishu channel started (HTTP outbound%s).",
            " + WebSocket inbound" if self._ws_client else " only",
        )

        # Keep the task alive until stop() is called.
        try:
            while self._running:
                await asyncio.sleep(1)
        finally:
            if self._client:
                await self._client.aclose()
                self._client = None
            logger.info("Feishu channel stopped.")

    async def stop(self) -> None:
        """Stop Feishu channel."""
        self._running = False
        if self._ws_task:
            self._ws_task.cancel()
            try:
                await self._ws_task
            except asyncio.CancelledError:
                pass

    async def _upload_feishu_image(self, path: str) -> str | None:
        """Upload image to Feishu; returns image_key or None."""
        if not self._client or not self._tenant_access_token:
            return None
        p = Path(path)
        if not p.is_file():
            return None
        url = "https://open.feishu.cn/open-apis/im/v1/images"
        headers = {"Authorization": f"Bearer {self._tenant_access_token}"}
        try:
            with p.open("rb") as f:
                files = {"image": (p.name, f, mimetypes.guess_type(path)[0] or "image/jpeg")}
                data = {"image_type": "message"}
                resp = await self._client.post(url, headers=headers, data=data, files=files)
            if resp.status_code != 200:
                logger.warning("Feishu image upload failed: HTTP {} - {}", resp.status_code, resp.text[:200])
                return None
            body = resp.json()
            if body.get("code") != 0:
                logger.warning("Feishu image upload error: {}", body)
                return None
            key = (body.get("data") or {}).get("image_key")
            if key:
                logger.info("Feishu image uploaded: {} -> {}", path, _shorten(key, 40))
            return key
        except Exception as e:  # pragma: no cover
            logger.error("Feishu image upload error: {}", e)
            return None

    async def _schedule_thinking_message(self, chat_id: str) -> None:
        """Schedule a 'thinking' message to be sent after threshold delay.
        
        If reply arrives before threshold, the timer is cancelled.
        """
        # Cancel existing timer if any
        existing = self._thinking_messages.pop(chat_id, None)
        if existing:
            _, timer_task = existing
            timer_task.cancel()
            try:
                await timer_task
            except asyncio.CancelledError:
                pass
        
        async def _send_thinking():
            await asyncio.sleep(self._thinking_threshold_ms / 1000.0)
            if not self._client or not self._tenant_access_token:
                return
            url = "https://open.feishu.cn/open-apis/im/v1/messages"
            params = {"receive_id_type": "chat_id"}
            headers = {
                "Authorization": f"Bearer {self._tenant_access_token}",
                "Content-Type": "application/json; charset=utf-8",
            }
            payload = {
                "receive_id": chat_id,
                "msg_type": "text",
                "content": json.dumps({"text": "正在思考..."}, ensure_ascii=False),
            }
            try:
                resp = await self._client.post(url, params=params, headers=headers, json=payload)
                if resp.status_code != 200:
                    logger.warning("Feishu thinking message failed: HTTP {} - {}", resp.status_code, resp.text[:200])
                    return
                body = resp.json()
                if body.get("code") != 0:
                    logger.warning("Feishu thinking message error: {}", body)
                    return
                message_id = (body.get("data") or {}).get("message_id")
                if message_id:
                    logger.debug("Feishu thinking message sent: chat_id={} message_id={}", chat_id, message_id)
                    # Update the entry with message_id
                    self._thinking_messages[chat_id] = (message_id, timer_task)
            except asyncio.CancelledError:
                # Timer cancelled, reply arrived quickly
                pass
            except Exception as e:
                logger.error("Error sending Feishu thinking message: {}", e)
        
        timer_task = asyncio.create_task(_send_thinking())
        # Store placeholder entry (will be updated with message_id when sent)
        self._thinking_messages[chat_id] = ("", timer_task)

    async def _cancel_thinking_message(self, chat_id: str) -> None:
        """Cancel scheduled thinking message for a chat_id."""
        existing = self._thinking_messages.pop(chat_id, None)
        if existing:
            _, timer_task = existing
            timer_task.cancel()
            try:
                await timer_task
            except asyncio.CancelledError:
                pass

    async def _update_message(self, message_id: str, content: str) -> bool:
        """Update a Feishu message's content. Returns True if successful."""
        if not self._client or not self._tenant_access_token:
            return False
        url = f"https://open.feishu.cn/open-apis/im/v1/messages/{message_id}"
        headers = {
            "Authorization": f"Bearer {self._tenant_access_token}",
            "Content-Type": "application/json; charset=utf-8",
        }
        payload = {
            "msg_type": "text",
            "content": json.dumps({"text": content}, ensure_ascii=False),
        }
        try:
            resp = await self._client.put(url, headers=headers, json=payload)
            if resp.status_code != 200:
                logger.warning("Feishu update message failed: HTTP {} - {}", resp.status_code, resp.text[:200])
                return False
            body = resp.json()
            if body.get("code") != 0:
                logger.warning("Feishu update message error: {}", body)
                return False
            logger.debug("Feishu message updated: message_id={}", message_id)
            return True
        except Exception as e:
            logger.error("Error updating Feishu message: {}", e)
            return False

    async def _delete_message(self, message_id: str) -> None:
        """Delete a Feishu message by message_id."""
        if not self._client or not self._tenant_access_token:
            return
        url = f"https://open.feishu.cn/open-apis/im/v1/messages/{message_id}"
        headers = {"Authorization": f"Bearer {self._tenant_access_token}"}
        try:
            resp = await self._client.delete(url, headers=headers)
            if resp.status_code != 200:
                logger.warning("Feishu delete message failed: HTTP {} - {}", resp.status_code, resp.text[:200])
                return
            body = resp.json()
            if body.get("code") != 0:
                logger.warning("Feishu delete message error: {}", body)
                return
            logger.debug("Feishu message deleted: message_id={}", message_id)
        except Exception as e:
            logger.error("Error deleting Feishu message: {}", e)

    async def _upload_feishu_file(self, path: str) -> str | None:
        """Upload file to Feishu; returns file_key or None."""
        if not self._client or not self._tenant_access_token:
            return None
        p = Path(path)
        if not p.is_file():
            return None
        url = "https://open.feishu.cn/open-apis/im/v1/files"
        headers = {"Authorization": f"Bearer {self._tenant_access_token}"}
        try:
            with p.open("rb") as f:
                files = {"file": (p.name, f)}
                data = {"file_type": "stream", "file_name": p.name}
                resp = await self._client.post(url, headers=headers, data=data, files=files)
            if resp.status_code != 200:
                logger.warning("Feishu file upload failed: HTTP {} - {}", resp.status_code, resp.text[:200])
                return None
            body = resp.json()
            if body.get("code") != 0:
                logger.warning("Feishu file upload error: {}", body)
                return None
            key = (body.get("data") or {}).get("file_key")
            if key:
                logger.info("Feishu file uploaded: {} -> {}", path, _shorten(key, 40))
            return key
        except Exception as e:  # pragma: no cover
            logger.error("Feishu file upload error: {}", e)
            return None

    async def send(self, msg: OutboundMessage) -> None:
        """Send a message to Feishu via OpenAPI.

        Supports text and, when msg.media is set, file/image attachments.
        Expects msg.chat_id to be a Feishu chat_id and a valid tenant access token.
        """
        if not self._client:
            logger.warning("Feishu HTTP client not initialized; message dropped")
            return

        if not self._tenant_access_token:
            logger.error("Feishu tenant_access_token missing; cannot send message")
            return

        url = "https://open.feishu.cn/open-apis/im/v1/messages"
        params = {"receive_id_type": "chat_id"}
        headers = {
            "Authorization": f"Bearer {self._tenant_access_token}",
            "Content-Type": "application/json; charset=utf-8",
        }

        try:
            # 0) Cancel "thinking" timer and get message_id if "thinking" was already sent
            thinking_entry = self._thinking_messages.pop(msg.chat_id, None)
            thinking_message_id = None
            if thinking_entry:
                thinking_message_id, timer_task = thinking_entry
                timer_task.cancel()
                try:
                    await timer_task
                except asyncio.CancelledError:
                    pass

            # 1) Handle text content
            has_text = bool(msg.content and msg.content.strip())
            has_media = bool(msg.media)
            
            # If no text and no media, delete thinking message if exists
            if not has_text and not has_media:
                if thinking_message_id:
                    await self._delete_message(thinking_message_id)
                return
            
            if has_text:
                content = msg.content.strip()
                # If "thinking" message exists, update it; otherwise send new message
                if thinking_message_id:
                    updated = await self._update_message(thinking_message_id, content)
                    if updated:
                        logger.info(
                            "Feishu outbound -> chat_id={} (updated thinking message) text={}",
                            msg.chat_id,
                            _shorten(content),
                        )
                        # Continue to send media if any
                    else:
                        # Update failed, send new message
                        thinking_message_id = None
                
                if not thinking_message_id:
                    logger.info(
                        "Feishu outbound -> chat_id={} reply_to={} text={}",
                        msg.chat_id,
                        msg.reply_to,
                        _shorten(content),
                    )
                    payload = {
                        "receive_id": msg.chat_id,
                        "msg_type": "text",
                        "content": json.dumps({"text": content}, ensure_ascii=False),
                    }
                    resp = await self._client.post(url, params=params, headers=headers, json=payload)
                    if resp.status_code != 200:
                        logger.error("Feishu send failed: HTTP {} - {}", resp.status_code, resp.text[:200])
                        return
                    body = resp.json()
                    if body.get("code") != 0:
                        logger.error("Feishu send error: {}", body)
                        return
                    logger.info(
                        "Feishu message sent successfully (message_id={})",
                        (body.get("data") or {}).get("message_id") or "",
                    )

            # 2) Send each media (image or file)
            for path in msg.media or []:
                p = Path(path)
                if not p.is_file():
                    logger.warning("Feishu outbound media not a file: {}", path)
                    continue
                mime, _ = mimetypes.guess_type(path)
                is_image = bool(mime and mime.startswith("image/"))
                if is_image:
                    key = await self._upload_feishu_image(path)
                    if not key:
                        continue
                    payload = {
                        "receive_id": msg.chat_id,
                        "msg_type": "image",
                        "content": json.dumps({"image_key": key}, ensure_ascii=False),
                    }
                else:
                    key = await self._upload_feishu_file(path)
                    if not key:
                        continue
                    payload = {
                        "receive_id": msg.chat_id,
                        "msg_type": "file",
                        "content": json.dumps({"file_key": key}, ensure_ascii=False),
                    }
                resp = await self._client.post(url, params=params, headers=headers, json=payload)
                if resp.status_code != 200:
                    logger.error("Feishu send media failed: HTTP {} - {}", resp.status_code, resp.text[:200])
                    continue
                body = resp.json()
                if body.get("code") != 0:
                    logger.error("Feishu send media error: {}", body)
                    continue
                logger.info(
                    "Feishu {} sent successfully (message_id={})",
                    "image" if is_image else "file",
                    (body.get("data") or {}).get("message_id") or "",
                )

            # If no text and no media were sent, do nothing (no-op)
        except Exception as e:  # pragma: no cover - network/runtime failures
            logger.error("Error sending Feishu message: {}", e)

    # ------------------------------------------------------------------
    # Inbound WebSocket handling (using lark-oapi)
    # ------------------------------------------------------------------

    def _start_ws_client(self) -> None:
        """Start Feishu WebSocket client for inbound events, if available."""
        if lark is None:
            if _lark_import_error is not None:
                logger.warning(
                    "lark-oapi import failed: {}; Feishu inbound WebSocket events disabled",
                    _lark_import_error,
                )
            else:
                logger.warning(
                    "lark-oapi not installed; Feishu inbound WebSocket events are disabled"
                )
            return

        if not getattr(self.config, "app_id", None) or not getattr(
            self.config, "app_secret", None
        ):
            logger.warning(
                "Feishu app_id/app_secret not configured; inbound WebSocket events disabled"
            )
            return

        # Build event handler that forwards text / file / image messages into the nanobot bus
        def _on_message(data: P2ImMessageReceiveV1) -> None:  # type: ignore[valid-type]
            try:
                event = data.event
                msg = event.message
                sender = event.sender.sender_id
                chat_id = msg.chat_id
                sender_id = (
                    getattr(sender, "open_id", None)
                    or getattr(sender, "user_id", None)
                    or ""
                )
                if not sender_id:
                    return
                metadata: dict[str, Any] = {
                    "chat_type": msg.chat_type,
                    "message_id": msg.message_id,
                }
                if not self._loop:
                    logger.warning("FeishuChannel loop not set; dropping inbound message")
                    return

                msg_type = getattr(msg, "message_type", None) or "text"
                if not msg.content:
                    return
                try:
                    body = json.loads(msg.content)
                except json.JSONDecodeError:
                    logger.warning("Feishu message content is not valid JSON")
                    return

                if msg_type == "text":
                    text = (body.get("text") or "").strip()
                    if not text:
                        return
                    logger.info(
                        "Feishu inbound <- chat_id={} sender_id={} message_id={} text={}",
                        chat_id,
                        sender_id,
                        msg.message_id,
                        _shorten(text),
                    )
                    # Schedule "thinking" message (delayed)
                    async def _handle_with_thinking():
                        await self._schedule_thinking_message(str(chat_id))
                        await self._handle_message(
                            sender_id=str(sender_id),
                            chat_id=str(chat_id),
                            content=text,
                            media=None,
                            metadata=metadata,
                        )
                    fut = asyncio.run_coroutine_threadsafe(
                        _handle_with_thinking(),
                        self._loop,
                    )
                    fut.add_done_callback(lambda _: None)
                    return

                if msg_type == "file":
                    file_key = body.get("file_key")
                    if not file_key:
                        return
                    logger.info(
                        "Feishu inbound <- chat_id={} sender_id={} message_id={} file_key={}",
                        chat_id,
                        sender_id,
                        msg.message_id,
                        _shorten(file_key, 80),
                    )
                    async def _handle_file_with_thinking():
                        await self._schedule_thinking_message(str(chat_id))
                        await self._handle_inbound_media(
                            sender_id=str(sender_id),
                            chat_id=str(chat_id),
                            metadata=metadata,
                            download_coro=self._download_feishu_file(file_key),
                            label="file",
                        )
                    fut = asyncio.run_coroutine_threadsafe(
                        _handle_file_with_thinking(),
                        self._loop,
                    )
                    fut.add_done_callback(lambda _: None)
                    return

                if msg_type == "image":
                    image_key = body.get("image_key")
                    if not image_key:
                        return
                    logger.info(
                        "Feishu inbound <- chat_id={} sender_id={} message_id={} image_key={}",
                        chat_id,
                        sender_id,
                        msg.message_id,
                        _shorten(image_key, 80),
                    )
                    async def _handle_image_with_thinking():
                        await self._schedule_thinking_message(str(chat_id))
                        await self._handle_inbound_media(
                            sender_id=str(sender_id),
                            chat_id=str(chat_id),
                            metadata=metadata,
                            download_coro=self._download_feishu_image(image_key),
                            label="image",
                        )
                    fut = asyncio.run_coroutine_threadsafe(
                        _handle_image_with_thinking(),
                        self._loop,
                    )
                    fut.add_done_callback(lambda _: None)
                    return
            except Exception as e:  # pragma: no cover - defensive
                logger.error(f"Error handling Feishu inbound message: {e}")

        # Some Feishu events are not used by nanobot but are still pushed over the
        # same WebSocket. Without a handler the SDK logs "processor not found".
        # Register no-op handlers to keep logs clean.

        def _on_message_read(*_: Any, **__: Any) -> None:
            return

        def _on_bot_p2p_chat_entered(*_: Any, **__: Any) -> None:
            # User opened a P2P chat with the bot; no action needed
            return

        try:
            dispatcher = (
                lark.EventDispatcherHandler.builder("", "")
                .register_p2_im_message_receive_v1(_on_message)
                .register_p2_im_message_message_read_v1(_on_message_read)
                .register_p2_im_chat_access_event_bot_p2p_chat_entered_v1(_on_bot_p2p_chat_entered)
                .build()
            )

            self._ws_client = lark.ws.Client(  # type: ignore[attr-defined]
                self.config.app_id,
                self.config.app_secret,
                event_handler=dispatcher,
                log_level=lark.LogLevel.INFO,
            )

            async def _run_ws() -> None:
                def _start() -> None:
                    try:
                        self._ws_client.start()
                    except Exception as e:  # pragma: no cover - network/runtime
                        logger.error(f"Feishu WebSocket client stopped with error: {e}")

                await asyncio.to_thread(_start)

            self._ws_task = asyncio.create_task(_run_ws())
            logger.info("Feishu WebSocket client started for inbound events")
        except Exception as e:  # pragma: no cover - defensive
            logger.error(f"Failed to start Feishu WebSocket client: {e}")

