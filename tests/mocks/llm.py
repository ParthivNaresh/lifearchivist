from typing import Any, Dict, Optional
from unittest.mock import Mock


class MockLLMProviderManager:
    def list_providers(self) -> list[Dict[str, Any]]:
        return []

    async def list_models(self, provider_id: str) -> Mock:
        result = Mock()
        result.is_success.return_value = True
        result.unwrap.return_value = []
        return result


class MockLLMManager:
    def __init__(self):
        self.health_monitor = Mock()
        self.health_monitor.is_healthy.return_value = True

    def list_providers(self) -> list[Dict[str, Any]]:
        return [
            {
                "id": "test_provider",
                "type": "openai",
                "is_default": False,
                "is_healthy": True,
            }
        ]

    def get_provider(self, provider_id: Optional[str]) -> Optional[Mock]:
        if provider_id is None or provider_id == "test_provider":
            provider = Mock()
            provider.provider_id = "test_provider"
            provider.provider_type = Mock()
            provider.provider_type.value = "openai"
            provider.is_initialized = True
            provider.validate_credentials = self._mock_validate_credentials
            provider.metadata = Mock()
            return provider
        return None

    async def _mock_validate_credentials(self) -> bool:
        return True

    async def list_models(self, provider_id: str) -> Mock:
        result = Mock()
        result.is_failure.return_value = False
        result.is_success.return_value = True
        result.unwrap.return_value = []
        return result

    async def generate(
        self,
        messages: list,
        model: str,
        provider_id: Optional[str],
        temperature: float,
        max_tokens: int,
    ) -> Mock:
        result = Mock()
        result.is_failure.return_value = False
        result.unwrap.return_value = Mock(
            content="Test response",
            model=model,
            provider="openai",
            tokens_used=10,
            prompt_tokens=5,
            completion_tokens=5,
            cost_usd=0.001,
            finish_reason="stop",
            metadata={},
        )
        return result

    def set_default_provider(self, provider_id: str) -> Mock:
        result = Mock()
        result.is_failure.return_value = False
        return result

    async def remove_provider(self, provider_id: str) -> Mock:
        result = Mock()
        result.is_failure.return_value = False
        return result

    async def add_provider(self, provider: Mock, set_as_default: bool) -> Mock:
        result = Mock()
        result.is_failure.return_value = False
        return result

    def get_metadata_capabilities(self, provider_id: str) -> Mock:
        result = Mock()
        result.is_success.return_value = True
        result.unwrap.return_value = []
        return result

    async def get_workspaces(self, provider_id: str) -> Mock:
        result = Mock()
        result.is_success.return_value = True
        result.unwrap.return_value = []
        return result

    async def get_usage(self, provider_id: str, start_dt, end_dt) -> Mock:
        result = Mock()
        result.is_success.return_value = True
        result.unwrap.return_value = Mock(
            start_time=start_dt,
            end_time=end_dt,
            total_tokens=1000,
            input_tokens=500,
            output_tokens=500,
            cached_tokens=0,
            requests_count=10,
            metadata={},
        )
        return result

    async def get_costs(self, provider_id: str, start_dt, end_dt) -> Mock:
        result = Mock()
        result.is_success.return_value = True
        result.unwrap.return_value = Mock(
            start_time=start_dt,
            end_time=end_dt,
            total_cost_usd=0.05,
            currency="USD",
            breakdown={},
            metadata={},
        )
        return result


class MockCredentialService:
    async def add_provider(
        self,
        provider_id: str,
        provider_type: Any,
        config: Any,
        is_default: bool,
    ) -> Mock:
        result = Mock()
        result.is_failure.return_value = False
        return result

    async def delete_provider(self, provider_id: str) -> Mock:
        result = Mock()
        result.is_failure.return_value = False
        return result

    async def get_provider_metadata(self, provider_id: str) -> Mock:
        result = Mock()
        result.is_failure.return_value = False
        result.unwrap.return_value = {
            "provider_type": "openai",
            "is_default": False,
            "user_id": "default",
        }
        return result

    async def update_provider(
        self,
        provider_id: str,
        config: Optional[Any],
        is_default: Optional[bool],
    ) -> Mock:
        result = Mock()
        result.is_failure.return_value = False
        return result


class MockProviderLoader:
    async def load_provider(self, provider_id: str) -> Mock:
        result = Mock()
        result.is_failure.return_value = False
        provider = Mock()
        provider.provider_id = provider_id
        provider.provider_type = Mock()
        provider.provider_type.value = "openai"
        result.unwrap.return_value = provider
        return result
