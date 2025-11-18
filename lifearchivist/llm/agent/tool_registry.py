import logging
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from ...utils.logx import log_event, track
from .exceptions import ToolExecutionError
from .tools.base import BaseAgentTool
from .tools.document_search_tool import DocumentSearchTool
from .tools.extraction_tool import DataExtractionTool

if TYPE_CHECKING:
    from storage.document_service import LlamaIndexDocumentService
    from storage.metadata_service import MetadataService
    from storage.search_service import SearchService


class AgentToolRegistry:

    def __init__(
        self,
        document_service: Optional["LlamaIndexDocumentService"] = None,
        search_service: Optional["SearchService"] = None,
        metadata_service: Optional["MetadataService"] = None,
    ):
        self._tools: Dict[str, BaseAgentTool] = {}
        self._finalized: bool = False
        self.document_service = document_service
        self.search_service = search_service
        self.metadata_service = metadata_service

    def register(self, tool: BaseAgentTool) -> None:
        if tool.input_model is None:
            raise ValueError(
                f"Tool '{tool.name}' must declare input_model (Pydantic BaseModel subclass)"
            )
        if self._finalized:
            raise ToolExecutionError(
                "Cannot register tools after registry has been finalized"
            )

        if not isinstance(tool, BaseAgentTool):
            raise TypeError(
                f"Tool must be instance of BaseAgentTool, got {type(tool).__name__}"
            )

        tool_name = tool.name

        if not tool_name:
            raise ValueError("Tool name cannot be empty")

        if tool_name in self._tools:
            raise ToolExecutionError(f"Tool '{tool_name}' is already registered")

        self._tools[tool_name] = tool

    def get_tool(self, name: str) -> Optional[BaseAgentTool]:
        return self._tools.get(name)

    def list_tools(self) -> List[BaseAgentTool]:
        return list(self._tools.values())

    def get_tool_names(self) -> List[str]:
        return list(self._tools.keys())

    def has_tool(self, name: str) -> bool:
        return name in self._tools

    def count(self) -> int:
        return len(self._tools)

    @track(operation="agent_register_all")
    def register_all(self) -> None:
        if self._finalized:
            raise ToolExecutionError(
                "Cannot register tools after registry has been finalized"
            )

        log_event(
            "registry_register_all_started",
            {
                "has_document_service": self.document_service is not None,
            },
        )

        tool_definitions: List[Dict[str, Any]] = []

        if self.search_service and self.metadata_service:
            tool_definitions.append(
                {
                    "name": "DocumentSearchTool",
                    "class": DocumentSearchTool,
                    "dependencies": ["search_service", "metadata_service"],
                    "kwargs": {
                        "search_service": self.search_service,
                        "metadata_service": self.metadata_service,
                    },
                }
            )

        if self.document_service:
            tool_definitions.append(
                {
                    "name": "DataExtractionTool",
                    "class": DataExtractionTool,
                    "dependencies": ["document_service"],
                    "kwargs": {
                        "document_service": self.document_service,
                    },
                }
            )

        registered_count = 0
        skipped_count = 0

        for tool_def in tool_definitions:
            tool_name = tool_def.get("name", "unknown")
            try:
                missing_deps = []
                dependencies = tool_def.get("dependencies", [])

                for dep in dependencies:
                    if getattr(self, dep, None) is None:
                        missing_deps.append(dep)

                if missing_deps:
                    log_event(
                        "registry_tool_skipped_missing_deps",
                        {
                            "tool_name": tool_name,
                            "missing_dependencies": missing_deps,
                        },
                        level=logging.WARNING,
                    )
                    skipped_count += 1
                    continue

                tool_class = tool_def["class"]
                kwargs = tool_def.get("kwargs", {})
                tool_instance = tool_class(**kwargs)
                self.register(tool_instance)
                log_event(
                    "registry_tool_registered",
                    {
                        "tool_name": tool_name,
                        "requires_llm": getattr(tool_instance, "requires_llm", False),
                    },
                )
                registered_count += 1

            except Exception as e:
                log_event(
                    "registry_tool_registration_failed",
                    {
                        "tool_name": tool_name,
                        "error": str(e),
                        "error_type": type(e).__name__,
                    },
                    level=logging.ERROR,
                )
                skipped_count += 1
                continue

        log_event(
            "registry_register_all_completed",
            {
                "registered_count": registered_count,
                "skipped_count": skipped_count,
                "total_tools": len(self._tools),
            },
        )

    def finalize(self) -> None:
        if self._finalized:
            return

        self._finalized = True
        self._tools = dict(self._tools)

    @property
    def is_finalized(self) -> bool:
        return self._finalized

    def __len__(self) -> int:
        return len(self._tools)

    def __contains__(self, name: str) -> bool:
        return name in self._tools

    def __repr__(self) -> str:
        status = "finalized" if self._finalized else "open"
        return f"AgentToolRegistry(tools={len(self._tools)}, status={status})"
