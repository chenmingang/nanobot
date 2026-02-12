"""Tool registry for dynamic tool management."""

import asyncio
from typing import Any

from nanobot.agent.tools.base import Tool


DEFAULT_TOOL_TIMEOUT = 120


class ToolRegistry:
    """
    Registry for agent tools.
    
    Allows dynamic registration and execution of tools.
    """
    
    def __init__(self, default_timeout: float = DEFAULT_TOOL_TIMEOUT):
        self._tools: dict[str, Tool] = {}
        self.default_timeout = default_timeout
    
    def register(self, tool: Tool) -> None:
        """Register a tool."""
        self._tools[tool.name] = tool
    
    def unregister(self, name: str) -> None:
        """Unregister a tool by name."""
        self._tools.pop(name, None)
    
    def get(self, name: str) -> Tool | None:
        """Get a tool by name."""
        return self._tools.get(name)
    
    def has(self, name: str) -> bool:
        """Check if a tool is registered."""
        return name in self._tools
    
    def get_definitions(self) -> list[dict[str, Any]]:
        """Get all tool definitions in OpenAI format."""
        return [tool.to_schema() for tool in self._tools.values()]
    
    async def execute(
        self, 
        name: str, 
        params: dict[str, Any],
        timeout: float | None = None
    ) -> str:
        """
        Execute a tool by name with given parameters.
        
        Args:
            name: Tool name.
            params: Tool parameters.
            timeout: Optional timeout in seconds. Uses default_timeout if not specified.
        
        Returns:
            Tool execution result as string.
        
        Raises:
            KeyError: If tool not found.
        """
        tool = self._tools.get(name)
        if not tool:
            return f"Error: Tool '{name}' not found"

        try:
            errors = tool.validate_params(params)
            if errors:
                return f"Error: Invalid parameters for tool '{name}': " + "; ".join(errors)
            
            effective_timeout = timeout if timeout is not None else self.default_timeout
            
            try:
                return await asyncio.wait_for(
                    tool.execute(**params),
                    timeout=effective_timeout
                )
            except asyncio.TimeoutError:
                return f"Error: Tool '{name}' timed out after {effective_timeout}s"
                
        except Exception as e:
            return f"Error executing {name}: {str(e)}"
    
    @property
    def tool_names(self) -> list[str]:
        """Get list of registered tool names."""
        return list(self._tools.keys())
    
    def __len__(self) -> int:
        return len(self._tools)
    
    def __contains__(self, name: str) -> bool:
        return name in self._tools
