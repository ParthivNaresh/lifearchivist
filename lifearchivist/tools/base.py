"""
Base tool class for MCP tools.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict

from pydantic import BaseModel


class ToolMetadata(BaseModel):
    """Tool metadata schema."""

    name: str
    description: str
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    async_tool: bool = True
    idempotent: bool = True


class BaseTool(ABC):
    """Base class for all MCP tools."""

    def __init__(self):
        self.metadata = self._get_metadata()

    @abstractmethod
    def _get_metadata(self) -> ToolMetadata:
        """Get tool metadata."""
        pass

    @abstractmethod
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute the tool with given parameters."""
        pass

    async def validate_input(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Validate input parameters against schema."""
        # TODO: Implement JSON schema validation
        return params

    async def validate_output(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Validate output against schema."""
        # TODO: Implement JSON schema validation
        return result
