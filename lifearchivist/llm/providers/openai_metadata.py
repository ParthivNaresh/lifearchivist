"""
OpenAI-specific metadata implementation.

Supports Admin API features when admin keys are provided.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional

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


class OpenAIMetadata(BaseProviderMetadata):
    """
    OpenAI metadata provider.

    Supports:
    - Organization info (admin keys only)
    - Rate limits (all keys)
    """

    def __init__(
        self,
        provider_id: str,
        api_key: str,
        base_url: str = "https://api.openai.com/v1",
    ):
        super().__init__(provider_id, api_key)
        self.base_url = base_url
        self.is_admin_key = api_key.startswith("sk-admin-")
        self.detect_capabilities()

    def detect_capabilities(self) -> None:
        """Detect capabilities based on key type."""
        self._register_capability(MetadataCapability.RATE_LIMITS)

        if self.is_admin_key:
            self._register_capability(MetadataCapability.USAGE_TRACKING)
            self._register_capability(MetadataCapability.ORGANIZATION_INFO)

    def _build_headers(self) -> Dict[str, str]:
        """Build request headers."""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def get_workspaces(self) -> List[Workspace]:
        """OpenAI doesn't have workspaces concept."""
        return []

    async def get_usage(
        self,
        start_time: datetime,
        end_time: datetime,
        **filters,
    ) -> UsageReport:
        """Fetch usage report from OpenAI Admin API."""
        if not self.supports_capability(MetadataCapability.USAGE_TRACKING):
            return await super().get_usage(start_time, end_time, **filters)

        try:
            start_unix = int(start_time.timestamp())

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/organization/usage/completions",
                    headers=self._build_headers(),
                    params={"start_time": start_unix, "limit": 100},
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
                        bucket_end = bucket.get("end_time", 0)
                        if bucket_end > end_time.timestamp():
                            break

                        for result in bucket.get("results", []):
                            total_input += result.get("input_tokens", 0)
                            total_output += result.get("output_tokens", 0)
                            total_cached += result.get("input_cached_tokens", 0)
                            total_requests += result.get("num_model_requests", 0)

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
        """OpenAI doesn't provide cost API."""
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
                requests_limit=int(headers.get("x-ratelimit-limit-requests", 0))
                or None,
                requests_remaining=int(headers.get("x-ratelimit-remaining-requests", 0))
                or None,
                tokens_limit=int(headers.get("x-ratelimit-limit-tokens", 0)) or None,
                tokens_remaining=int(headers.get("x-ratelimit-remaining-tokens", 0))
                or None,
            )

            reset_requests = headers.get("x-ratelimit-reset-requests")
            if reset_requests:
                try:
                    rate_limits.requests_reset = datetime.fromisoformat(
                        reset_requests.replace("Z", "+00:00")
                    )
                except Exception:
                    pass

            reset_tokens = headers.get("x-ratelimit-reset-tokens")
            if reset_tokens:
                try:
                    rate_limits.tokens_reset = datetime.fromisoformat(
                        reset_tokens.replace("Z", "+00:00")
                    )
                except Exception:
                    pass

            self.update_rate_limits(rate_limits)
            return rate_limits

        except Exception as e:
            logger.warning(f"Failed to parse rate limits: {e}")
            return None
