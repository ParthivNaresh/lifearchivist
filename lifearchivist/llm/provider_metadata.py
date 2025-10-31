"""
Provider metadata and admin capabilities.

Extensible system for fetching provider-specific metadata like workspaces,
usage tracking, and cost reporting. Each provider implements only what they support.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol


class MetadataCapability(Enum):
    WORKSPACES = "workspaces"
    USAGE_TRACKING = "usage_tracking"
    COST_TRACKING = "cost_tracking"
    RATE_LIMITS = "rate_limits"
    ORGANIZATION_INFO = "organization_info"


@dataclass
class Workspace:
    id: str
    name: str
    is_default: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RateLimitInfo:
    requests_limit: Optional[int] = None
    requests_remaining: Optional[int] = None
    requests_reset: Optional[datetime] = None
    tokens_limit: Optional[int] = None
    tokens_remaining: Optional[int] = None
    tokens_reset: Optional[datetime] = None


@dataclass
class UsageReport:
    start_time: datetime
    end_time: datetime
    total_tokens: int
    input_tokens: int
    output_tokens: int
    cached_tokens: int = 0
    requests_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CostReport:
    start_time: datetime
    end_time: datetime
    total_cost_usd: float
    breakdown: Dict[str, float]
    currency: str = "USD"
    metadata: Dict[str, Any] = field(default_factory=dict)


class ProviderMetadataProtocol(Protocol):
    """Protocol defining provider metadata capabilities."""

    def supports_capability(self, capability: MetadataCapability) -> bool:
        """Check if provider supports a specific capability."""
        ...

    async def get_workspaces(self) -> List[Workspace]:
        """Get list of workspaces/organizations."""
        ...

    async def get_usage(
        self,
        start_time: datetime,
        end_time: datetime,
        **filters,
    ) -> UsageReport:
        """Get usage report for time period."""
        ...

    async def get_costs(
        self,
        start_time: datetime,
        end_time: datetime,
        **filters,
    ) -> CostReport:
        """Get cost report for time period."""
        ...

    def get_rate_limits(self) -> Optional[RateLimitInfo]:
        """Get current rate limit status."""
        ...


class BaseProviderMetadata(ABC):
    """
    Base implementation for provider metadata.

    Providers inherit and override only what they support.
    """

    def __init__(self, provider_id: str, api_key: str):
        self.provider_id = provider_id
        self.api_key = api_key
        self._rate_limits: Optional[RateLimitInfo] = None
        self._capabilities: set[MetadataCapability] = set()

    def supports_capability(self, capability: MetadataCapability) -> bool:
        """Check if this provider supports a capability."""
        return capability in self._capabilities

    def _register_capability(self, capability: MetadataCapability) -> None:
        """Register a supported capability."""
        self._capabilities.add(capability)

    async def get_workspaces(self) -> List[Workspace]:
        """Default: no workspace support."""
        if not self.supports_capability(MetadataCapability.WORKSPACES):
            raise NotImplementedError(
                f"{self.__class__.__name__} does not support workspaces"
            )
        return []

    async def get_usage(
        self,
        start_time: datetime,
        end_time: datetime,
        **filters,
    ) -> UsageReport:
        """Default: no usage tracking."""
        if not self.supports_capability(MetadataCapability.USAGE_TRACKING):
            raise NotImplementedError(
                f"{self.__class__.__name__} does not support usage tracking"
            )
        return UsageReport(
            start_time=start_time,
            end_time=end_time,
            total_tokens=0,
            input_tokens=0,
            output_tokens=0,
        )

    async def get_costs(
        self,
        start_time: datetime,
        end_time: datetime,
        **filters,
    ) -> CostReport:
        """Default: no cost tracking."""
        if not self.supports_capability(MetadataCapability.COST_TRACKING):
            raise NotImplementedError(
                f"{self.__class__.__name__} does not support cost tracking"
            )
        return CostReport(
            start_time=start_time,
            end_time=end_time,
            total_cost_usd=0.0,
            breakdown={},
        )

    def get_rate_limits(self) -> Optional[RateLimitInfo]:
        """Get cached rate limit info."""
        return self._rate_limits

    def update_rate_limits(self, rate_limits: RateLimitInfo) -> None:
        """Update cached rate limit info."""
        self._rate_limits = rate_limits
        if not self.supports_capability(MetadataCapability.RATE_LIMITS):
            self._register_capability(MetadataCapability.RATE_LIMITS)

    @abstractmethod
    def detect_capabilities(self) -> None:
        """Detect what capabilities this provider/key supports."""
        pass
