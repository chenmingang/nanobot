"""Configuration schema using Pydantic."""

from pathlib import Path
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


class WhatsAppConfig(BaseModel):
    """WhatsApp channel configuration."""
    enabled: bool = False
    bridge_url: str = "ws://localhost:3001"
    allow_from: list[str] = Field(default_factory=list)  # Allowed phone numbers


class TelegramConfig(BaseModel):
    """Telegram channel configuration."""
    enabled: bool = False
    token: str = ""  # Bot token from @BotFather
    allow_from: list[str] = Field(default_factory=list)  # Allowed user IDs or usernames


class ChannelsConfig(BaseModel):
    """Configuration for chat channels."""
    whatsapp: WhatsAppConfig = Field(default_factory=WhatsAppConfig)
    telegram: TelegramConfig = Field(default_factory=TelegramConfig)
    # Feishu configuration (optional, outbound-only by default)
    # To fully support inbound events, you can add an HTTP endpoint or bridge
    # that calls the FeishuChannel._handle_message(...) helper.
    class FeishuConfig(BaseModel):
        """Feishu channel configuration."""

        enabled: bool = False
        # Option 1: direct tenant access token (if you manage it yourself)
        tenant_access_token: str = ""
        # Option 2: app credentials; if set and no tenant_access_token is
        # provided, FeishuChannel will automatically fetch one on startup.
        app_id: str = ""
        app_secret: str = ""
        allow_from: list[str] = Field(default_factory=list)

    feishu: FeishuConfig = Field(default_factory=FeishuConfig)


class MemoryFlushConfig(BaseModel):
    """Pre-compaction memory flush (store durable memories before compaction)."""

    enabled: bool = True
    trigger_messages_before: int = Field(
        default=0,
        description="Trigger flush N messages before compaction (0 = same as compaction)",
    )


class CompactionConfig(BaseModel):
    """Short-term memory compression config (summarize older conversation)."""

    enabled: bool = True
    threshold_messages: int = Field(
        default=60,
        description="Trigger compaction when messages exceed this count",
    )
    keep_recent: int = Field(
        default=20,
        description="Keep this many recent messages after compaction",
    )
    memory_flush: MemoryFlushConfig = Field(
        default_factory=MemoryFlushConfig,
        description="Pre-compaction memory flush",
    )


class MemorySearchConfig(BaseModel):
    """Vector memory search config (ChromaDB + local sentence-transformers embedding)."""

    enabled: bool = True
    local_model: str = Field(
        default="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        description="Local model for sentence-transformers embedding",
    )
    store_path: str = Field(
        default="~/.nanobot/memory/search",
        description="ChromaDB persistence path",
    )


class AgentDefaults(BaseModel):
    """Default agent configuration."""
    workspace: str = "~/.nanobot/workspace"
    model: str = "anthropic/claude-opus-4-5"
    max_tokens: int = 8192
    temperature: float = 0.7
    max_tool_iterations: int = 20
    max_history_messages: int = Field(
        default=50,
        description="Maximum number of conversation messages sent to the LLM (user+assistant pairs)",
    )
    compaction: CompactionConfig = Field(
        default_factory=CompactionConfig,
        description="Short-term memory compression (summarize older conversation)",
    )
    memory_search: MemorySearchConfig = Field(
        default_factory=MemorySearchConfig,
        description="Vector memory search (semantic search)",
    )


class AgentsConfig(BaseModel):
    """Agent configuration."""
    defaults: AgentDefaults = Field(default_factory=AgentDefaults)


class ProviderConfig(BaseModel):
    """LLM provider configuration."""
    enabled: bool = Field(
        default=True,
        description="Whether this provider is enabled. Only enabled providers are considered for API key/base.",
    )
    api_key: str = ""
    api_base: str | None = None


class ProvidersConfig(BaseModel):
    """Configuration for LLM providers."""
    anthropic: ProviderConfig = Field(default_factory=ProviderConfig)
    openai: ProviderConfig = Field(default_factory=ProviderConfig)
    openrouter: ProviderConfig = Field(default_factory=ProviderConfig)
    groq: ProviderConfig = Field(default_factory=ProviderConfig)
    zhipu: ProviderConfig = Field(default_factory=ProviderConfig)
    siliconflow: ProviderConfig = Field(default_factory=ProviderConfig)
    vllm: ProviderConfig = Field(default_factory=ProviderConfig)
    gemini: ProviderConfig = Field(default_factory=ProviderConfig)


class GatewayConfig(BaseModel):
    """Gateway/server configuration."""
    host: str = "0.0.0.0"
    port: int = 8000


class WebSearchConfig(BaseModel):
    """Web search tool configuration."""
    api_key: str = ""  # Brave Search API key
    max_results: int = 5


class WebToolsConfig(BaseModel):
    """Web tools configuration."""
    search: WebSearchConfig = Field(default_factory=WebSearchConfig)


class ToolsConfig(BaseModel):
    """Tools configuration."""
    web: WebToolsConfig = Field(default_factory=WebToolsConfig)


class Config(BaseSettings):
    """Root configuration for nanobot."""
    agents: AgentsConfig = Field(default_factory=AgentsConfig)
    channels: ChannelsConfig = Field(default_factory=ChannelsConfig)
    providers: ProvidersConfig = Field(default_factory=ProvidersConfig)
    gateway: GatewayConfig = Field(default_factory=GatewayConfig)
    tools: ToolsConfig = Field(default_factory=ToolsConfig)
    
    @property
    def workspace_path(self) -> Path:
        """Get expanded workspace path."""
        return Path(self.agents.defaults.workspace).expanduser()
    
    def get_api_key(self) -> str | None:
        """Get API key from first enabled provider with key (priority: OpenRouter > Anthropic > OpenAI > Gemini > Zhipu > SiliconFlow > Groq > vLLM)."""
        for p in (
            self.providers.openrouter,
            self.providers.anthropic,
            self.providers.openai,
            self.providers.gemini,
            self.providers.zhipu,
            self.providers.siliconflow,
            self.providers.groq,
            self.providers.vllm,
        ):
            if p.enabled and p.api_key:
                return p.api_key
        return None

    def get_api_base(self) -> str | None:
        """Get API base from first enabled provider that has base/key (OpenRouter, Zhipu, SiliconFlow, vLLM)."""
        if self.providers.openrouter.enabled and self.providers.openrouter.api_key:
            return self.providers.openrouter.api_base or "https://openrouter.ai/api/v1"
        if self.providers.zhipu.enabled and self.providers.zhipu.api_key:
            return self.providers.zhipu.api_base
        if self.providers.siliconflow.enabled and self.providers.siliconflow.api_key:
            return self.providers.siliconflow.api_base or "https://api.siliconflow.cn/v1"
        if self.providers.vllm.enabled and self.providers.vllm.api_base:
            return self.providers.vllm.api_base
        return None
    
    class Config:
        env_prefix = "NANOBOT_"
        env_nested_delimiter = "__"
