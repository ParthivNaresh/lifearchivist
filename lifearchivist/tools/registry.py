"""
Tool registry for managing MCP tools.
"""

import logging
from typing import Dict, Optional

from lifearchivist.tools.date_extract.date_extraction_tool import (
    ContentDateExtractionTool,
)
from lifearchivist.tools.extract.extract_tools import ExtractTextTool
from lifearchivist.tools.file_import.file_import_tool import FileImportTool
from lifearchivist.tools.llamaindex.llamaindex_query_tool import LlamaIndexQueryTool
from lifearchivist.tools.ollama.ollama_tool import OllamaTool
from lifearchivist.tools.search.search_tool import IndexSearchTool
from lifearchivist.utils.logging import log_context, log_event, log_method
from lifearchivist.utils.logging.structured import MetricsCollector

from .base import BaseTool

logger = logging.getLogger(__name__)


class ToolRegistry:
    """Registry for managing MCP tools."""

    def __init__(self, vault=None, llamaindex_service=None, progress_manager=None):
        self.tools: Dict[str, BaseTool] = {}
        self.vault = vault
        self.llamaindex_service = llamaindex_service
        self.progress_manager = progress_manager

        log_event(
            "tool_registry_initialized",
            {
                "has_vault": vault is not None,
                "has_llamaindex_service": llamaindex_service is not None,
                "has_progress_manager": progress_manager is not None,
                "vault_type": type(vault).__name__ if vault else None,
                "llamaindex_service_type": (
                    type(llamaindex_service).__name__ if llamaindex_service else None
                ),
                "progress_manager_type": (
                    type(progress_manager).__name__ if progress_manager else None
                ),
            },
        )

    @log_method(
        operation_name="tool_registration_batch", include_args=True, include_result=True
    )
    async def register_all(self):
        """Register all available tools."""
        with log_context(operation="tool_registration_batch"):
            metrics = MetricsCollector("tool_registration_batch")
            metrics.start()

            log_event("tool_registration_started", {})

            # LlamaIndex service should already be initialized by MCP server
            if not self.llamaindex_service:
                metrics.set_error(ValueError("LlamaIndex service is required"))
                metrics.report("tool_registration_failed")

                log_event(
                    "tool_registration_dependency_missing",
                    {"missing_dependency": "llamaindex_service"},
                )
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

            metrics.add_metric("tools_to_register", len(tool_definitions))

            log_event(
                "tool_definitions_prepared",
                {
                    "tool_count": len(tool_definitions),
                    "tool_names": [td["name"] for td in tool_definitions],
                },
            )

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
                        log_event(
                            "tool_registration_dependency_check_failed",
                            {
                                "tool_name": tool_def["name"],
                                "error": f"Missing dependencies: {missing_deps} for {tool_def['name']}",
                            },
                        )
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

                    log_event(
                        "tool_registered_successfully",
                        {
                            "tool_name": tool_def["name"],
                            "tool_metadata_name": tool_instance.metadata.name,
                            "dependencies_provided": tool_def["dependencies"],
                        },
                    )
                except Exception as e:
                    failed_registrations += 1
                    log_event(
                        "tool_registration_failed",
                        {
                            "tool_name": tool_def["name"],
                            "error_type": type(e).__name__,
                            "error_message": str(e),
                        },
                    )

            metrics.add_metric("successful_registrations", successful_registrations)
            metrics.add_metric("failed_registrations", failed_registrations)
            metrics.add_metric("total_registered_tools", len(self.tools))

            if failed_registrations > 0:
                metrics.set_error(
                    RuntimeError(f"{failed_registrations} tool registrations failed")
                )
                metrics.report("tool_registration_completed_with_errors")
            else:
                metrics.set_success(True)
                metrics.report("tool_registration_completed")

            log_event(
                "tool_registration_finished",
                {
                    "total_tools_registered": len(self.tools),
                    "successful_registrations": successful_registrations,
                    "failed_registrations": failed_registrations,
                    "registered_tool_names": list(self.tools.keys()),
                },
            )

    def register_tool(self, tool: BaseTool):
        """Register a single tool."""
        tool_name = tool.metadata.name

        # Check if tool already exists
        already_existed = tool_name in self.tools

        if already_existed:
            log_event(
                "tool_registration_overwrite",
                {
                    "tool_name": tool_name,
                    "previous_tool_type": type(self.tools[tool_name]).__name__,
                    "new_tool_type": type(tool).__name__,
                },
            )

        self.tools[tool_name] = tool

        log_event(
            "individual_tool_registered",
            {
                "tool_name": tool_name,
                "tool_type": type(tool).__name__,
                "tool_description": tool.metadata.description,
                "is_async": tool.metadata.async_tool,
                "is_idempotent": tool.metadata.idempotent,
                "was_overwrite": already_existed,
                "total_tools_now": len(self.tools),
            },
        )

    def get_tool(self, name: str) -> Optional[BaseTool]:
        """Get a tool by name."""
        tool = self.tools.get(name)

        log_event(
            "tool_retrieval_attempt",
            {
                "requested_tool_name": name,
                "tool_found": tool is not None,
                "available_tools": list(self.tools.keys()),
                "total_available_tools": len(self.tools),
            },
        )

        if tool is None:
            log_event(
                "tool_not_found",
                {
                    "requested_tool_name": name,
                    "available_tools": list(self.tools.keys()),
                    "suggestion": self._suggest_similar_tool(name),
                },
            )

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

        log_event(
            "tool_list_accessed",
            {
                "total_tools": len(self.tools),
                "tool_names": list(self.tools.keys()),
                "async_tools_count": sum(
                    1 for tool in self.tools.values() if tool.metadata.async_tool
                ),
                "idempotent_tools_count": sum(
                    1 for tool in self.tools.values() if tool.metadata.idempotent
                ),
            },
        )

        return tool_list

    def get_tool_schema(self, name: str) -> Optional[Dict[str, str]]:
        """Get input/output schema for a tool."""
        tool = self.get_tool(name)

        if not tool:
            log_event(
                "tool_schema_request_failed",
                {
                    "requested_tool_name": name,
                    "reason": "tool_not_found",
                    "available_tools": list(self.tools.keys()),
                },
            )
            return None

        log_event(
            "tool_schema_retrieved",
            {
                "tool_name": name,
                "has_input_schema": bool(tool.metadata.input_schema),
                "has_output_schema": bool(tool.metadata.output_schema),
                "input_schema_properties_count": (
                    len(tool.metadata.input_schema.get("properties", {}))
                    if tool.metadata.input_schema
                    else 0
                ),
                "output_schema_properties_count": (
                    len(tool.metadata.output_schema.get("properties", {}))
                    if tool.metadata.output_schema
                    else 0
                ),
            },
        )

        return {
            "input_schema": str(tool.metadata.input_schema),
            "output_schema": str(tool.metadata.output_schema),
        }
