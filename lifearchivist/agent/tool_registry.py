from typing import TYPE_CHECKING, Any, Dict, List, Optional

from .exceptions import ToolExecutionError
from .tools.base import BaseAgentTool
from .tools.extraction_tool import DataExtractionTool

if TYPE_CHECKING:
    from ..storage.document_service import LlamaIndexDocumentService


class AgentToolRegistry:

    def __init__(
        self,
        document_service: Optional["LlamaIndexDocumentService"] = None,
    ):
        self._tools: Dict[str, BaseAgentTool] = {}
        self._finalized: bool = False
        self.document_service = document_service

    def register(self, tool: BaseAgentTool) -> None:
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

    def register_all(self) -> None:
        if self._finalized:
            raise ToolExecutionError(
                "Cannot register tools after registry has been finalized"
            )

        tool_definitions: List[Dict[str, Any]] = []

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

        for tool_def in tool_definitions:
            try:
                missing_deps = []
                dependencies = tool_def.get("dependencies", [])

                for dep in dependencies:
                    if getattr(self, dep, None) is None:
                        missing_deps.append(dep)

                if missing_deps:
                    continue

                tool_class = tool_def["class"]
                kwargs = tool_def.get("kwargs", {})
                tool_instance = tool_class(**kwargs)
                self.register(tool_instance)

            except Exception:
                continue

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
