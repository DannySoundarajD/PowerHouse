"""
Tool registry for Sentinel AI Workbench.
Central registry for all available tools.
"""

from typing import Dict, List, Optional

from .base import Tool
from ..utils.logger import get_logger

logger = get_logger(__name__)


class ToolRegistry:
    """
    Central registry for tools.
    Tools are registered by name and can be called by the agent.
    """
    
    def __init__(self):
        """Initialize tool registry."""
        self.tools: Dict[str, Tool] = {}
        logger.info("ToolRegistry initialized")
    
    def register_tool(self, tool: Tool):
        """
        Register a tool.
        
        Args:
            tool: Tool instance to register
        """
        if tool.name in self.tools:
            logger.warning(f"Tool {tool.name} already registered, overwriting")
        
        self.tools[tool.name] = tool
        logger.info(f"Registered tool: {tool.name}")
    
    def get_tool(self, name: str) -> Optional[Tool]:
        """Get tool by name."""
        return self.tools.get(name)
    
    def list_tools(self) -> List[Tool]:
        """Get list of all registered tools."""
        return list(self.tools.values())
    
    def get_tool_schemas(self) -> List[Dict]:
        """
        Get OpenAI-format tool schemas for all registered tools.
        
        Returns:
            List of tool definitions in OpenAI format
        """
        return [tool.to_openai_tool() for tool in self.tools.values()]
    
    def execute_tool(self, name: str, **kwargs) -> Dict:
        """
        Execute a tool by name.
        
        Args:
            name: Tool name
            **kwargs: Tool parameters
        
        Returns:
            Tool execution result
        """
        tool = self.get_tool(name)
        
        if not tool:
            logger.error(f"Tool not found: {name}")
            return {
                "status": "error",
                "error": f"Tool '{name}' not found",
            }
        
        return tool.safe_execute(**kwargs)
    
    def tool_exists(self, name: str) -> bool:
        """Check if tool is registered."""
        return name in self.tools
    
    def get_summary(self) -> Dict:
        """Get summary of registry state."""
        return {
            "total_tools": len(self.tools),
            "tool_names": list(self.tools.keys()),
        }


# Global registry instance
_tool_registry: Optional[ToolRegistry] = None


def get_tool_registry() -> ToolRegistry:
    """Get or create global tool registry instance."""
    global _tool_registry
    if _tool_registry is None:
        _tool_registry = ToolRegistry()
    return _tool_registry
