"""
Base tool class for MCP tools.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict

import jsonschema
from jsonschema import ValidationError as JSONSchemaValidationError
from pydantic import BaseModel

from .exceptions import ValidationError


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
        try:
            # Use the input schema from metadata
            jsonschema.validate(params, self.metadata.input_schema)
            return params
        except JSONSchemaValidationError as e:
            raise ValidationError(f"Input validation failed: {e.message}") from e
        except Exception as e:
            raise ValidationError(
                f"Unexpected error during input validation: {str(e)}"
            ) from e

    async def validate_output(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Validate output against schema."""
        try:
            # Use the output schema from metadata
            jsonschema.validate(result, self.metadata.output_schema)
            return result
        except JSONSchemaValidationError as e:
            raise ValidationError(f"Output validation failed: {e.message}") from e
        except Exception as e:
            raise ValidationError(
                f"Unexpected error during output validation: {str(e)}"
            ) from e
