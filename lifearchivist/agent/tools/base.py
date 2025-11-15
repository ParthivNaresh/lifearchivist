from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Dict, Optional

if TYPE_CHECKING:
    from ...llm import LLMProviderManager


class BaseAgentTool(ABC):

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        pass

    @property
    @abstractmethod
    def input_schema(self) -> Dict[str, Any]:
        pass

    @property
    def output_schema(self) -> Optional[Dict[str, Any]]:
        return None

    @property
    def requires_llm(self) -> bool:
        return False

    async def execute(self, **kwargs) -> Dict[str, Any]:
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement execute() or execute_with_llm()"
        )

    async def execute_with_llm(
        self,
        llm_provider: "LLMProviderManager",
        prompt: str,
        parameters: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        raise NotImplementedError(
            f"{self.__class__.__name__} does not support LLM execution"
        )
