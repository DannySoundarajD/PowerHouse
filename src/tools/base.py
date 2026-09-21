"""
Base tool interface for Sentinel AI Workbench.
All tools must implement this interface.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from ..utils.logger import get_logger

logger = get_logger(__name__)


class Tool(ABC):
    """
    Abstract base class for all tools.
    Tools are functions the agent can call to interact with the system.
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Unique tool name (e.g., 'read_file', 'execute_code')."""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description of what the tool does."""
        pass
    
    @property
    @abstractmethod
    def parameters(self) -> Dict[str, Any]:
        """
        JSON schema for tool parameters.
        
        Returns:
            Dict with 'type', 'properties', 'required' fields following JSON Schema spec
        
        Example:
            {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path"},
                    "content": {"type": "string", "description": "File content"}
                },
                "required": ["path", "content"]
            }
        """
        pass
    
    @abstractmethod
    def execute(self, **kwargs) -> Dict[str, Any]:
        """
        Execute the tool with given parameters.
        
        Args:
            **kwargs: Parameters matching the schema from self.parameters
        
        Returns:
            Dict with keys:
                - status: "success" or "error"
                - output: Tool output (if successful)
                - error: Error message (if failed)
        """
        pass
    
    def to_openai_tool(self) -> Dict[str, Any]:
        """
        Convert tool to OpenAI function calling format.
        
        Returns:
            Dict in format: {"type": "function", "function": {...}}
        """
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            }
        }
    
    def validate_parameters(self, **kwargs) -> bool:
        """
        Validate parameters against schema (basic implementation).
        Override for custom validation.
        """
        required = self.parameters.get("required", [])
        
        for param in required:
            if param not in kwargs:
                raise ValueError(f"Missing required parameter: {param}")
        
        return True
    
    def safe_execute(self, **kwargs) -> Dict[str, Any]:
        """
        Execute tool with error handling and logging.
        """
        try:
            # Validate parameters
            self.validate_parameters(**kwargs)
            
            # Log execution
            logger.info(f"Executing tool: {self.name}")
            logger.debug(f"Parameters: {kwargs}")
            
            # Execute
            result = self.execute(**kwargs)
            
            # Log result
            logger.info(f"Tool {self.name} completed: status={result.get('status')}")
            
            return result
        
        except Exception as e:
            logger.error(f"Tool {self.name} failed: {e}", exc_info=True)
            return {
                "status": "error",
                "error": str(e),
            }


class ToolExecutionError(Exception):
    """Exception raised when tool execution fails."""
    pass


class ToolValidationError(Exception):
    """Exception raised when tool parameters are invalid."""
    pass
