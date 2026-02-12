"""LiteLLM provider implementation for multi-provider support."""

import asyncio
import json
import os
from typing import Any

import litellm
from litellm import acompletion
from loguru import logger

from nanobot.providers.base import LLMProvider, LLMResponse, ToolCallRequest

LOG_PREFIX = "[nanobot.llm]"

# 重试配置
MAX_RETRIES = 3
RETRY_BASE_DELAY = 1.0
RETRY_MAX_DELAY = 10.0

# 可重试的错误类型
RETRYABLE_ERRORS = (
    "rate_limit",
    "overloaded",
    "timeout",
    "connection",
    "503",
    "502",
    "429",
)


def _is_retryable_error(error: Exception) -> bool:
    """判断错误是否可重试。"""
    error_str = str(error).lower()
    return any(e in error_str for e in RETRYABLE_ERRORS)


def _get_user_friendly_error(error: Exception) -> str:
    """将技术错误转换为用户友好的提示。"""
    error_str = str(error).lower()
    
    if "rate_limit" in error_str or "429" in error_str:
        return "API 请求频率超限，请稍后重试"
    if "overloaded" in error_str or "503" in error_str:
        return "API 服务繁忙，请稍后重试"
    if "timeout" in error_str:
        return "API 请求超时，请稍后重试"
    if "connection" in error_str or "502" in error_str:
        return "网络连接问题，请检查网络后重试"
    if "invalid_api_key" in error_str or "401" in error_str:
        return "API Key 无效，请检查配置"
    if "insufficient_quota" in error_str or "402" in error_str:
        return "API 配额不足，请充值后重试"
    if "model_not_found" in error_str or "404" in error_str:
        return "模型不存在，请检查模型名称"
    
    return f"API 调用失败: {str(error)[:100]}"


class LiteLLMProvider(LLMProvider):
    """
    LLM provider using LiteLLM for multi-provider support.
    
    Supports OpenRouter, Anthropic, OpenAI, Gemini, and many other providers through
    a unified interface.
    """
    
    def __init__(
        self, 
        api_key: str | None = None, 
        api_base: str | None = None,
        default_model: str = "anthropic/claude-opus-4-5",
        provider_name: str | None = None,
    ):
        super().__init__(api_key, api_base)
        self.default_model = default_model
        self.provider_name = provider_name
        
        # Prefer explicit provider_name, fall back to heuristic detection for backward compatibility
        self.is_openrouter = (
            provider_name == "openrouter"
            or (api_key and api_key.startswith("sk-or-"))
            or (api_base and "openrouter" in api_base)
        )
        
        # Silicon Flow (硅基流动) - OpenAI-compatible, api.siliconflow.cn
        self.is_siliconflow = provider_name == "siliconflow" or (bool(api_base) and "siliconflow" in api_base)
        
        # Explicit provider routing (no model/port inference required)
        self.is_ollama = provider_name == "ollama"
        self.is_vllm = provider_name == "vllm" or (
            # Backward compatible: treat arbitrary api_base as vLLM/custom endpoint
            bool(api_base) and not self.is_openrouter and not self.is_siliconflow and not self.is_ollama
        )
        
        # Configure LiteLLM based on provider (Ollama 无需设置 API key)
        if api_key and not (self.is_ollama and api_key == "dummy"):
            if self.is_openrouter:
                # OpenRouter mode - set key
                os.environ["OPENROUTER_API_KEY"] = api_key
            elif self.is_vllm:
                # vLLM/custom endpoint - uses OpenAI-compatible API
                os.environ["OPENAI_API_KEY"] = api_key
            elif "deepseek" in default_model:
                os.environ.setdefault("DEEPSEEK_API_KEY", api_key)
            elif "anthropic" in default_model:
                os.environ.setdefault("ANTHROPIC_API_KEY", api_key)
            elif "openai" in default_model or "gpt" in default_model:
                os.environ.setdefault("OPENAI_API_KEY", api_key)
            elif "gemini" in default_model.lower():
                os.environ.setdefault("GEMINI_API_KEY", api_key)
            elif "zhipu" in default_model or "glm" in default_model or "zai" in default_model:
                os.environ.setdefault("ZHIPUAI_API_KEY", api_key)
            elif "groq" in default_model:
                os.environ.setdefault("GROQ_API_KEY", api_key)
            elif self.is_siliconflow:
                os.environ["OPENAI_API_KEY"] = api_key
        
        if api_base:
            litellm.api_base = api_base
        
        # Disable LiteLLM logging noise
        litellm.suppress_debug_info = True
        # Fix: thinking models (o1, o3, Claude thinking) require reasoning_content/thinking_blocks
        # in assistant tool-call messages. When missing, LiteLLM drops the thinking param to avoid 400.
        litellm.modify_params = True
    
    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        model: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> LLMResponse:
        """
        Send a chat completion request via LiteLLM.
        
        Args:
            messages: List of message dicts with 'role' and 'content'.
            tools: Optional list of tool definitions in OpenAI format.
            model: Model identifier (e.g., 'anthropic/claude-sonnet-4-5').
            max_tokens: Maximum tokens in response.
            temperature: Sampling temperature.
        
        Returns:
            LLMResponse with content and/or tool calls.
        """
        model = model or self.default_model
        
        # Provider-specific model rewriting based on explicit provider_name.
        # Keep this minimal: LiteLLM expects some providers to be prefixed.
        if self.provider_name == "ollama":
            # Ollama expects ollama/ or ollama_chat/ prefix.
            # If user configured bare model name like "qwen3:4b", default to ollama_chat/ for best chat quality.
            if not (model.startswith("ollama/") or model.startswith("ollama_chat/")):
                model = f"ollama_chat/{model}"
        elif self.provider_name == "openrouter":
            # Prefer explicit openrouter/ prefix; LiteLLM strips first "openrouter/" when sending.
            if not model.startswith("openrouter/"):
                model = f"openrouter/{model}"
        elif self.provider_name == "vllm":
            # vLLM uses hosted_vllm/ prefix per LiteLLM docs (handled below).
            pass
        elif self.provider_name == "siliconflow":
            # SiliconFlow uses openai/ prefix (handled below).
            pass

        # For OpenRouter, prefix model name if not already prefixed.
        # LiteLLM strips the first "openrouter/" when sending to the API, so OpenRouter
        # native models (e.g. pony-alpha, polaris-alpha) must be passed as
        # "openrouter/openrouter/<id>" so that the API receives "openrouter/<id>".
        if self.is_openrouter:
            if not model.startswith("openrouter/"):
                model = f"openrouter/{model}"
            # If model is "openrouter/<single>" (no second slash), it's OpenRouter-native:
            # use double prefix so LiteLLM sends "openrouter/<single>" to the API.
            after_prefix = model[len("openrouter/"):].strip()
            if after_prefix and "/" not in after_prefix:
                model = f"openrouter/openrouter/{after_prefix}"
        
        # For Zhipu/Z.ai, ensure prefix is present
        # Handle cases like "glm-4.7-flash" -> "zai/glm-4.7-flash"
        if ("glm" in model.lower() or "zhipu" in model.lower()) and not (
            model.startswith("zhipu/") or 
            model.startswith("zai/") or 
            model.startswith("openrouter/")
        ):
            model = f"zai/{model}"
        
        # For vLLM, use hosted_vllm/ prefix per LiteLLM docs (Ollama uses ollama/ or ollama_chat/)
        if self.is_vllm and not (model.startswith("ollama/") or model.startswith("ollama_chat/")):
            model = f"hosted_vllm/{model}"
        
        # Silicon Flow: OpenAI-compatible API, must use openai/ prefix（不覆盖 Ollama 模型）
        if (
            self.is_siliconflow
            and not model.startswith("openai/")
            and not model.startswith("ollama/")
            and not model.startswith("ollama_chat/")
        ):
            model = f"openai/{model}"
        
        # For Gemini, ensure gemini/ prefix if not already present
        if "gemini" in model.lower() and not model.startswith("gemini/"):
            model = f"gemini/{model}"
        
        kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        
        # Pass api_base directly for custom endpoints (vLLM, etc.)
        if self.api_base:
            kwargs["api_base"] = self.api_base
        
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"
        
        self._log_request(model=kwargs["model"], messages=messages, tools=tools)
        
        last_error: Exception | None = None
        for attempt in range(MAX_RETRIES):
            try:
                response = await acompletion(**kwargs)
                parsed = self._parse_response(response)
                self._log_response(parsed)
                return parsed
            except Exception as e:
                last_error = e
                if _is_retryable_error(e) and attempt < MAX_RETRIES - 1:
                    delay = min(RETRY_BASE_DELAY * (2 ** attempt), RETRY_MAX_DELAY)
                    logger.warning(
                        f"{LOG_PREFIX} retryable error on attempt {attempt + 1}/{MAX_RETRIES}: {e}. "
                        f"Retrying in {delay:.1f}s..."
                    )
                    await asyncio.sleep(delay)
                else:
                    break
        
        # 所有重试失败后，返回友好错误
        user_error = _get_user_friendly_error(last_error) if last_error else "Unknown error"
        logger.error(f"{LOG_PREFIX} all retries failed: {last_error}")
        return LLMResponse(
            content=user_error,
            finish_reason="error",
        )
    
    def _parse_response(self, response: Any) -> LLMResponse:
        """Parse LiteLLM response into our standard format."""
        choice = response.choices[0]
        message = choice.message
        
        tool_calls = []
        if hasattr(message, "tool_calls") and message.tool_calls:
            for tc in message.tool_calls:
                # Parse arguments from JSON string if needed
                args = tc.function.arguments
                if isinstance(args, str):
                    import json
                    try:
                        args = json.loads(args)
                    except json.JSONDecodeError:
                        args = {"raw": args}
                
                tool_calls.append(ToolCallRequest(
                    id=tc.id,
                    name=tc.function.name,
                    arguments=args,
                ))
        
        usage = {}
        if hasattr(response, "usage") and response.usage:
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }
        reasoning_content = getattr(message, "reasoning_content", None) or None
        thinking_blocks = getattr(message, "thinking_blocks", None) or None
        # Normalize content: can be None, str, or list of parts (e.g. OpenAI content array)
        raw_content = getattr(message, "content", None)
        if raw_content is None:
            content_str = None
        elif isinstance(raw_content, str):
            content_str = raw_content
        elif isinstance(raw_content, list):
            parts = []
            for part in raw_content:
                if isinstance(part, dict) and part.get("type") == "text":
                    parts.append(part.get("text") or "")
                elif isinstance(part, str):
                    parts.append(part)
            content_str = "\n".join(parts) if parts else None
        else:
            content_str = str(raw_content) if raw_content else None
        return LLMResponse(
            content=content_str,
            tool_calls=tool_calls,
            finish_reason=choice.finish_reason or "stop",
            usage=usage,
            reasoning_content=reasoning_content,
            thinking_blocks=thinking_blocks,
        )
    
    def _log_request(self, model: str, messages: list[dict[str, Any]], tools: list[dict[str, Any]] | None) -> None:
        """在日志中完整打印发给大模型的请求（单条 JSON）."""
        payload = {"model": model, "messages": messages}
        if tools is not None:
            payload["tools"] = tools
        logger.info(f"{LOG_PREFIX} request:\n{json.dumps(payload, ensure_ascii=False, indent=2)}")
    
    def _log_response(self, resp: LLMResponse) -> None:
        """在日志中完整打印大模型响应（单条 JSON）."""
        out = {
            "content": resp.content,
            "finish_reason": resp.finish_reason,
            "tool_calls": [{"id": tc.id, "name": tc.name, "arguments": tc.arguments} for tc in resp.tool_calls],
            "usage": resp.usage,
        }
        logger.info(f"{LOG_PREFIX} response:\n{json.dumps(out, ensure_ascii=False, indent=2)}")
    
    def get_default_model(self) -> str:
        """Get the default model."""
        return self.default_model
