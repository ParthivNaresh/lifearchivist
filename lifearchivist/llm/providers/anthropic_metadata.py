"""
Anthropic-specific metadata implementation.

Supports Admin API features when admin keys are provided.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Union

import aiohttp

from ..provider_metadata import (
    BaseProviderMetadata,
    CostReport,
    MetadataCapability,
    RateLimitInfo,
    UsageReport,
    Workspace,
)

logger = logging.getLogger(__name__)


class AnthropicMetadata(BaseProviderMetadata):
    """
    Anthropic metadata provider.

    Supports:
    - Workspaces (admin keys only)
    - Usage tracking (admin keys only)
    - Cost tracking (admin keys only)
    - Rate limits (all keys)
    """

    def __init__(
        self,
        provider_id: str,
        api_key: str,
        base_url: str = "https://api.anthropic.com/v1",
    ):
        super().__init__(provider_id, api_key)
        self.base_url = base_url
        self.is_admin_key = api_key.startswith("sk-ant-admin")
        self.detect_capabilities()

    def detect_capabilities(self) -> None:
        """Detect capabilities based on key type."""
        self._register_capability(MetadataCapability.RATE_LIMITS)

        if self.is_admin_key:
            self._register_capability(MetadataCapability.WORKSPACES)
            self._register_capability(MetadataCapability.USAGE_TRACKING)
            self._register_capability(MetadataCapability.COST_TRACKING)
            self._register_capability(MetadataCapability.ORGANIZATION_INFO)

    def _build_headers(self) -> Dict[str, str]:
        """Build request headers."""
        return {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }

    async def get_workspaces(self) -> List[Workspace]:
        """Fetch workspaces from Anthropic Admin API."""
        if not self.supports_capability(MetadataCapability.WORKSPACES):
            return []

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/organizations/workspaces",
                    headers=self._build_headers(),
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as response:
                    if response.status != 200:
                        logger.warning(
                            f"Failed to fetch workspaces: HTTP {response.status}"
                        )
                        return []

                    data = await response.json()
                    workspaces_data = data.get("data", [])

                    workspaces = []
                    for ws in workspaces_data:
                        workspaces.append(
                            Workspace(
                                id=ws.get("id", ""),
                                name=ws.get("name", "Unnamed Workspace"),
                                is_default=ws.get("is_default", False),
                                metadata={
                                    "created_at": ws.get("created_at"),
                                    "archived_at": ws.get("archived_at"),
                                },
                            )
                        )

                    logger.info(
                        f"Fetched {len(workspaces)} workspaces for {self.provider_id}"
                    )
                    return workspaces

        except Exception as e:
            logger.error(f"Error fetching workspaces: {e}")
            return []

    async def get_usage(
        self,
        start_time: datetime,
        end_time: datetime,
        **filters,
    ) -> UsageReport:
        """Fetch usage report from Anthropic Admin API."""
        if not self.supports_capability(MetadataCapability.USAGE_TRACKING):
            return await super().get_usage(start_time, end_time, **filters)

        try:
            params: Dict[str, Union[str, List[str]]] = {
                "starting_at": start_time.isoformat(),
                "ending_at": end_time.isoformat(),
                "bucket_width": "1d",
            }

            if "workspace_ids" in filters:
                workspace_list: List[str] = []
                for ws_id in filters["workspace_ids"]:
                    workspace_list.append(ws_id)
                params["workspace_ids[]"] = workspace_list

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/organizations/usage_report/messages",
                    headers=self._build_headers(),
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as response:
                    if response.status != 200:
                        logger.warning(f"Failed to fetch usage: HTTP {response.status}")
                        return UsageReport(
                            start_time=start_time,
                            end_time=end_time,
                            total_tokens=0,
                            input_tokens=0,
                            output_tokens=0,
                        )

                    data = await response.json()
                    buckets = data.get("data", [])

                    total_input = 0
                    total_output = 0
                    total_cached = 0
                    total_requests = 0

                    for bucket in buckets:
                        total_input += bucket.get("input_tokens", 0)
                        total_output += bucket.get("output_tokens", 0)
                        total_cached += bucket.get("cache_read_input_tokens", 0)
                        total_requests += bucket.get("request_count", 0)

                    return UsageReport(
                        start_time=start_time,
                        end_time=end_time,
                        total_tokens=total_input + total_output,
                        input_tokens=total_input,
                        output_tokens=total_output,
                        cached_tokens=total_cached,
                        requests_count=total_requests,
                        metadata={"buckets": len(buckets)},
                    )

        except Exception as e:
            logger.error(f"Error fetching usage: {e}")
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
        """Fetch cost report from Anthropic Admin API."""
        if not self.supports_capability(MetadataCapability.COST_TRACKING):
            return super().get_costs(start_time, end_time, **filters)

        try:
            params: Dict[str, Union[str, List[str]]] = {
                "starting_at": start_time.isoformat(),
                "ending_at": end_time.isoformat(),
            }

            if "workspace_ids" in filters:
                workspace_list: List[str] = []
                for ws_id in filters["workspace_ids"]:
                    workspace_list.append(ws_id)
                params["workspace_ids[]"] = workspace_list

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/organizations/cost_report",
                    headers=self._build_headers(),
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as response:
                    if response.status != 200:
                        logger.warning(f"Failed to fetch costs: HTTP {response.status}")
                        return CostReport(
                            start_time=start_time,
                            end_time=end_time,
                            total_cost_usd=0.0,
                            breakdown={},
                        )

                    data = await response.json()
                    buckets = data.get("data", [])

                    total_cost = 0.0
                    breakdown: Dict[str, float] = {}

                    for bucket in buckets:
                        cost_cents = float(bucket.get("amount", "0"))
                        cost_usd = cost_cents / 100
                        total_cost += cost_usd

                        description = bucket.get("description", "Unknown")
                        breakdown[description] = (
                            breakdown.get(description, 0.0) + cost_usd
                        )

                    return CostReport(
                        start_time=start_time,
                        end_time=end_time,
                        total_cost_usd=total_cost,
                        breakdown=breakdown,
                        metadata={"buckets": len(buckets)},
                    )

        except Exception as e:
            logger.error(f"Error fetching costs: {e}")
            return CostReport(
                start_time=start_time,
                end_time=end_time,
                total_cost_usd=0.0,
                breakdown={},
            )

    def parse_rate_limits_from_headers(
        self, headers: Dict[str, str]
    ) -> Optional[RateLimitInfo]:
        """Parse rate limit info from response headers."""
        try:
            rate_limits = RateLimitInfo(
                requests_limit=int(headers.get("x-ratelimit-requests-limit", 0))
                or None,
                requests_remaining=int(headers.get("x-ratelimit-requests-remaining", 0))
                or None,
                tokens_limit=int(headers.get("x-ratelimit-tokens-limit", 0)) or None,
                tokens_remaining=int(headers.get("x-ratelimit-tokens-remaining", 0))
                or None,
            )

            reset_time = headers.get("x-ratelimit-requests-reset")
            if reset_time:
                try:
                    rate_limits.requests_reset = datetime.fromisoformat(
                        reset_time.replace("Z", "+00:00")
                    )
                except Exception:
                    pass

            tokens_reset = headers.get("x-ratelimit-tokens-reset")
            if tokens_reset:
                try:
                    rate_limits.tokens_reset = datetime.fromisoformat(
                        tokens_reset.replace("Z", "+00:00")
                    )
                except Exception:
                    pass

            self.update_rate_limits(rate_limits)
            return rate_limits

        except Exception as e:
            logger.warning(f"Failed to parse rate limits: {e}")
            return None
