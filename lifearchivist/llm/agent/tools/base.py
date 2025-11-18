from abc import ABC
from typing import TYPE_CHECKING, Any, Dict, Optional

from pydantic import BaseModel

from ..types import ParamsModel

if TYPE_CHECKING:
    from llm import LLMProviderManager


class BaseAgentTool(ABC):
    """
    All tools must declare a Pydantic model for parameters via `input_model`.
    Prefer implementing `execute_typed` which receives a parsed Pydantic instance.
    """

    name: str
    description: Optional[str] = None
    requires_llm: bool = False
    input_model: Optional[ParamsModel] = None

    def descriptor(self) -> Dict[str, Any]:
        schema: Dict[str, Any] = {}
        if self.input_model is not None:
            schema = self.input_model.model_json_schema()
        return {
            "name": self.name,
            "requires_llm": self.requires_llm,
            "input_schema": schema,  # planner still expects "input_schema"
            "summary": self.description or "",
        }

    # --- Preferred typed API
    async def execute_typed(self, *, params: BaseModel, context: Dict[str, Any]) -> Any:
        """
        Override in tools. Receives a validated Pydantic instance of `input_model`.
        """
        raise NotImplementedError(f"{self.name}.execute_typed must be implemented")

    # --- Legacy/dict API (fallback for tools not yet migrated)
    async def execute(
        self, *, parameters: Dict[str, Any], context: Dict[str, Any]
    ) -> Any:
        """
        Fallback if a tool hasn't migrated to execute_typed yet.
        Default behavior: re-validate and forward to execute_typed.
        """
        if self.input_model is None:
            raise RuntimeError(
                f"{self.name}: input_model must be set for dict execution path"
            )
        instance = self.input_model.model_validate(parameters)
        return await self.execute_typed(params=instance, context=context)

    async def execute_with_llm(
        self,
        *,
        llm_provider: "LLMProviderManager",
        prompt: str,
        params: BaseModel,
        context: Dict[str, Any],
    ) -> Any:
        raise NotImplementedError(
            f"{self.name}: requires_llm=True but execute_with_llm not implemented"
        )
