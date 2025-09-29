"""
Tool registry for managing MCP tools.
"""

from typing import Dict, Optional

from lifearchivist.tools.date_extract.date_extraction_tool import (
    ContentDateExtractionTool,
)
from lifearchivist.tools.extract.extract_tool import ExtractTextTool
from lifearchivist.tools.file_import.file_import_tool import FileImportTool
from lifearchivist.tools.llamaindex.llamaindex_query_tool import LlamaIndexQueryTool
from lifearchivist.tools.ollama.ollama_tool import OllamaTool
from lifearchivist.tools.search.search_tool import IndexSearchTool

from ..utils.logging import track
from .base import BaseTool


class ToolRegistry:
    """Registry for managing MCP tools."""

    def __init__(
        self,
        vault=None,
        llamaindex_service=None,
        progress_manager=None,
        enrichment_queue=None,
    ):
        self.tools: Dict[str, BaseTool] = {}
        self.vault = vault
        self.llamaindex_service = llamaindex_service
        self.progress_manager = progress_manager
        self.enrichment_queue = enrichment_queue

    @track(operation="tool_registration_batch")
    async def register_all(self):
        """Register all available tools."""
        # LlamaIndex service should already be initialized by MCP server
        if not self.llamaindex_service:
            raise ValueError("LlamaIndex service is required")

        # Define tools to register with their dependencies
        tool_definitions = [
            {
                "name": "FileImportTool",
                "class": FileImportTool,
                "dependencies": ["vault", "llamaindex_service", "progress_manager"],
                "kwargs": {
                    "vault": self.vault,
                    "llamaindex_service": self.llamaindex_service,
                    "progress_manager": self.progress_manager,
                    "enrichment_queue": self.enrichment_queue,
                },
            },
            {
                "name": "ExtractTextTool",
                "class": ExtractTextTool,
                "dependencies": ["vault"],
                "kwargs": {"vault": self.vault},
            },
            {
                "name": "ContentDateExtractionTool",
                "class": ContentDateExtractionTool,
                "dependencies": ["llamaindex_service"],
                "kwargs": {"llamaindex_service": self.llamaindex_service},
            },
            {
                "name": "OllamaTool",
                "class": OllamaTool,
                "dependencies": [],
                "kwargs": {},
            },
            {
                "name": "IndexSearchTool",
                "class": IndexSearchTool,
                "dependencies": ["llamaindex_service"],
                "kwargs": {"llamaindex_service": self.llamaindex_service},
            },
            {
                "name": "LlamaIndexQueryTool",
                "class": LlamaIndexQueryTool,
                "dependencies": ["llamaindex_service"],
                "kwargs": {"llamaindex_service": self.llamaindex_service},
            },
        ]

        successful_registrations = 0
        failed_registrations = 0

        for tool_def in tool_definitions:
            try:
                # Validate dependencies
                missing_deps = []
                dependencies = tool_def.get("dependencies", [])
                if not hasattr(dependencies, "__iter__"):
                    dependencies = []
                for dep in dependencies:
                    if getattr(self, dep, None) is None:
                        missing_deps.append(dep)

                if missing_deps:
                    failed_registrations += 1
                    continue

                # Create and register tool
                tool_class = tool_def["class"]
                if not callable(tool_class):
                    raise ValueError(f"Tool class is not callable: {tool_class}")
                kwargs = tool_def.get("kwargs", {})
                if not isinstance(kwargs, dict):
                    kwargs = {}
                tool_instance = tool_class(**kwargs)
                self.register_tool(tool_instance)
                successful_registrations += 1
            except Exception as _:
                failed_registrations += 1

    def register_tool(self, tool: BaseTool):
        """Register a single tool."""
        tool_name = tool.metadata.name
        self.tools[tool_name] = tool

    def get_tool(self, name: str) -> Optional[BaseTool]:
        """Get a tool by name."""
        tool = self.tools.get(name)
        return tool

    def _suggest_similar_tool(self, requested_name: str) -> Optional[str]:
        """Suggest a similar tool name for debugging purposes."""
        if not requested_name or not self.tools:
            return None

        # Simple similarity check - look for partial matches
        requested_lower = requested_name.lower()
        for tool_name in self.tools.keys():
            if (
                requested_lower in tool_name.lower()
                or tool_name.lower() in requested_lower
            ):
                return tool_name

        return None

    def list_tools(self) -> Dict[str, Dict[str, str]]:
        """List all registered tools with their metadata."""
        tool_list = {
            name: {
                "description": str(tool.metadata.description),
                "async": str(tool.metadata.async_tool),
                "idempotent": str(tool.metadata.idempotent),
            }
            for name, tool in self.tools.items()
        }
        return tool_list

    def get_tool_schema(self, name: str) -> Optional[Dict[str, str]]:
        """Get input/output schema for a tool."""
        tool = self.get_tool(name)

        if not tool:
            return None

        return {
            "input_schema": str(tool.metadata.input_schema),
            "output_schema": str(tool.metadata.output_schema),
        }
