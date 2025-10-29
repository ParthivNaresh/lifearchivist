"""
Cost Tracker - Tracks and enforces LLM usage costs.

Responsible for:
- Recording cost per request
- Aggregating costs by provider, user, time period
- Enforcing budget limits
- Cost analytics and reporting
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, Optional

from redis.asyncio import Redis

from ..utils.logging import log_event, track
from ..utils.result import Failure, Result, Success

logger = logging.getLogger(__name__)

# Redis key prefixes
COST_KEY_PREFIX = "llm:cost:"
COST_DAILY_PREFIX = "llm:cost:daily:"
COST_MONTHLY_PREFIX = "llm:cost:monthly:"
COST_USER_PREFIX = "llm:cost:user:"
BUDGET_KEY_PREFIX = "llm:budget:"


@dataclass
class CostRecord:
    """
    Record of a single LLM request cost.

    Attributes:
        provider_id: Provider identifier
        provider_type: Provider type
        model: Model used
        prompt_tokens: Input tokens
        completion_tokens: Output tokens
        cost_usd: Cost in USD
        timestamp: When the request occurred
        user_id: User who made the request
        request_id: Unique request identifier
        metadata: Additional context
    """

    provider_id: str
    provider_type: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    cost_usd: float
    timestamp: datetime
    user_id: str = "default"
    request_id: Optional[str] = None
    metadata: Dict = field(default_factory=dict)


@dataclass
class CostSummary:
    """
    Aggregated cost summary.

    Attributes:
        total_cost: Total cost in USD
        total_requests: Number of requests
        total_tokens: Total tokens used
        by_provider: Cost breakdown by provider
        by_model: Cost breakdown by model
        period_start: Start of period
        period_end: End of period
    """

    total_cost: float
    total_requests: int
    total_tokens: int
    by_provider: Dict[str, float]
    by_model: Dict[str, float]
    period_start: datetime
    period_end: datetime


@dataclass
class Budget:
    """
    Budget configuration.

    Attributes:
        limit_usd: Budget limit in USD
        period: Budget period ('daily', 'monthly', 'total')
        user_id: User this budget applies to
        alert_threshold: Alert when this percentage is reached (0.0-1.0)
    """

    limit_usd: float
    period: str
    user_id: str = "default"
    alert_threshold: float = 0.8


class CostTracker:
    """
    Tracks and enforces LLM usage costs.

    Persists cost data to Redis for durability and aggregation.
    Enforces budget limits to prevent overspending.
    """

    def __init__(self, redis_client: Redis):
        """
        Initialize cost tracker.

        Args:
            redis_client: Async Redis client for persistence
        """
        self.redis = redis_client
        self._budgets: Dict[str, Budget] = {}

    @track(
        operation="cost_tracker_record",
        include_args=["provider_id", "model", "cost_usd"],
        track_performance=True,
        frequency="high_frequency",
    )
    async def record_cost(self, record: CostRecord) -> Result[None, str]:
        """
        Record cost for an LLM request.

        Args:
            record: Cost record to persist

        Returns:
            Result indicating success or failure
        """
        try:
            # Generate timestamp key for time-series data
            timestamp_key = record.timestamp.strftime("%Y%m%d%H%M%S")
            record_key = (
                f"{COST_KEY_PREFIX}{record.user_id}:{timestamp_key}:{record.request_id}"
            )

            # Store detailed record
            record_data = {
                "provider_id": record.provider_id,
                "provider_type": record.provider_type,
                "model": record.model,
                "prompt_tokens": record.prompt_tokens,
                "completion_tokens": record.completion_tokens,
                "cost_usd": record.cost_usd,
                "timestamp": record.timestamp.isoformat(),
                "user_id": record.user_id,
                "request_id": record.request_id or "",
            }

            await self.redis.hset(record_key, mapping=record_data)
            await self.redis.expire(record_key, 90 * 24 * 3600)  # 90 days retention

            # Update aggregated counters
            await self._update_aggregates(record)

            log_event(
                "cost_recorded",
                {
                    "provider_id": record.provider_id,
                    "model": record.model,
                    "cost_usd": record.cost_usd,
                    "tokens": record.prompt_tokens + record.completion_tokens,
                },
            )

            return Success(None)

        except Exception as e:
            log_event(
                "cost_record_failed",
                {
                    "error": str(e),
                    "provider_id": record.provider_id,
                },
                level=logging.ERROR,
            )
            return Failure(
                error=f"Failed to record cost: {e}",
                error_type=type(e).__name__,
                status_code=500,
            )

    async def _update_aggregates(self, record: CostRecord) -> None:
        """
        Update aggregated cost counters.

        Args:
            record: Cost record to aggregate
        """
        # Daily aggregate
        daily_key = (
            f"{COST_DAILY_PREFIX}{record.user_id}:{record.timestamp.strftime('%Y%m%d')}"
        )
        await self.redis.hincrbyfloat(daily_key, "total_cost", record.cost_usd)
        await self.redis.hincrby(daily_key, "total_requests", 1)
        await self.redis.hincrby(
            daily_key, "total_tokens", record.prompt_tokens + record.completion_tokens
        )
        await self.redis.hincrbyfloat(
            daily_key, f"provider:{record.provider_id}", record.cost_usd
        )
        await self.redis.hincrbyfloat(
            daily_key, f"model:{record.model}", record.cost_usd
        )
        await self.redis.expire(daily_key, 90 * 24 * 3600)  # 90 days

        # Monthly aggregate
        monthly_key = (
            f"{COST_MONTHLY_PREFIX}{record.user_id}:{record.timestamp.strftime('%Y%m')}"
        )
        await self.redis.hincrbyfloat(monthly_key, "total_cost", record.cost_usd)
        await self.redis.hincrby(monthly_key, "total_requests", 1)
        await self.redis.hincrby(
            monthly_key, "total_tokens", record.prompt_tokens + record.completion_tokens
        )
        await self.redis.expire(monthly_key, 365 * 24 * 3600)  # 1 year

        # User total
        user_key = f"{COST_USER_PREFIX}{record.user_id}"
        await self.redis.hincrbyfloat(user_key, "total_cost", record.cost_usd)
        await self.redis.hincrby(user_key, "total_requests", 1)

    @track(
        operation="cost_tracker_check_budget",
        include_args=["user_id"],
        track_performance=True,
        frequency="high_frequency",
    )
    async def check_budget(
        self,
        user_id: str,
        estimated_cost: float,
    ) -> Result[bool, str]:
        """
        Check if request would exceed budget.

        Args:
            user_id: User identifier
            estimated_cost: Estimated cost of request

        Returns:
            Result with True if within budget, False if would exceed
        """
        budget = self._budgets.get(user_id)

        if budget is None:
            # No budget configured, allow request
            return Success(True)

        try:
            # Get current spending for budget period
            current_spending = await self._get_period_spending(user_id, budget.period)

            # Check if request would exceed budget
            projected_spending = current_spending + estimated_cost

            if projected_spending > budget.limit_usd:
                log_event(
                    "budget_exceeded",
                    {
                        "user_id": user_id,
                        "budget_limit": budget.limit_usd,
                        "current_spending": current_spending,
                        "estimated_cost": estimated_cost,
                        "projected_spending": projected_spending,
                    },
                    level=logging.WARNING,
                )

                return Failure(
                    error=f"Budget exceeded: ${projected_spending:.4f} > ${budget.limit_usd:.2f}",
                    error_type="BudgetExceeded",
                    status_code=429,
                    context={
                        "budget_limit": budget.limit_usd,
                        "current_spending": current_spending,
                        "estimated_cost": estimated_cost,
                    },
                )

            # Check if approaching threshold
            if projected_spending >= budget.limit_usd * budget.alert_threshold:
                log_event(
                    "budget_threshold_reached",
                    {
                        "user_id": user_id,
                        "budget_limit": budget.limit_usd,
                        "current_spending": current_spending,
                        "threshold": budget.alert_threshold,
                    },
                    level=logging.WARNING,
                )

            return Success(True)

        except Exception as e:
            log_event(
                "budget_check_failed",
                {"error": str(e), "user_id": user_id},
                level=logging.ERROR,
            )
            # On error, allow request (fail open)
            return Success(True)

    async def _get_period_spending(self, user_id: str, period: str) -> float:
        """
        Get spending for a budget period.

        Args:
            user_id: User identifier
            period: Budget period ('daily', 'monthly', 'total')

        Returns:
            Current spending in USD
        """
        if period == "daily":
            key = f"{COST_DAILY_PREFIX}{user_id}:{datetime.now().strftime('%Y%m%d')}"
        elif period == "monthly":
            key = f"{COST_MONTHLY_PREFIX}{user_id}:{datetime.now().strftime('%Y%m')}"
        elif period == "total":
            key = f"{COST_USER_PREFIX}{user_id}"
        else:
            raise ValueError(f"Invalid budget period: {period}")

        cost_str = await self.redis.hget(key, "total_cost")
        return float(cost_str) if cost_str else 0.0

    async def get_summary(
        self,
        user_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Result[CostSummary, str]:
        """
        Get cost summary for a time period.

        Args:
            user_id: User identifier
            start_date: Start of period (defaults to 30 days ago)
            end_date: End of period (defaults to now)

        Returns:
            Result with cost summary or error
        """
        if end_date is None:
            end_date = datetime.now()

        if start_date is None:
            start_date = end_date - timedelta(days=30)

        try:
            # For now, return daily summary
            # In production, would aggregate across date range
            daily_key = f"{COST_DAILY_PREFIX}{user_id}:{end_date.strftime('%Y%m%d')}"
            data = await self.redis.hgetall(daily_key)

            if not data:
                return Success(
                    CostSummary(
                        total_cost=0.0,
                        total_requests=0,
                        total_tokens=0,
                        by_provider={},
                        by_model={},
                        period_start=start_date,
                        period_end=end_date,
                    )
                )

            # Parse aggregated data
            total_cost = float(data.get(b"total_cost", 0))
            total_requests = int(data.get(b"total_requests", 0))
            total_tokens = int(data.get(b"total_tokens", 0))

            # Extract provider and model breakdowns
            by_provider = {}
            by_model = {}

            for key, value in data.items():
                key_str = key.decode() if isinstance(key, bytes) else key
                value_float = float(value)

                if key_str.startswith("provider:"):
                    provider_id = key_str.split(":", 1)[1]
                    by_provider[provider_id] = value_float
                elif key_str.startswith("model:"):
                    model = key_str.split(":", 1)[1]
                    by_model[model] = value_float

            summary = CostSummary(
                total_cost=total_cost,
                total_requests=total_requests,
                total_tokens=total_tokens,
                by_provider=by_provider,
                by_model=by_model,
                period_start=start_date,
                period_end=end_date,
            )

            return Success(summary)

        except Exception as e:
            log_event(
                "cost_summary_failed",
                {"error": str(e), "user_id": user_id},
                level=logging.ERROR,
            )
            return Failure(
                error=f"Failed to get cost summary: {e}",
                error_type=type(e).__name__,
                status_code=500,
            )

    def set_budget(self, budget: Budget) -> None:
        """
        Set budget for a user.

        Args:
            budget: Budget configuration
        """
        self._budgets[budget.user_id] = budget

        log_event(
            "budget_set",
            {
                "user_id": budget.user_id,
                "limit_usd": budget.limit_usd,
                "period": budget.period,
            },
        )

    def get_budget(self, user_id: str) -> Optional[Budget]:
        """
        Get budget for a user.

        Args:
            user_id: User identifier

        Returns:
            Budget or None if not set
        """
        return self._budgets.get(user_id)

    def remove_budget(self, user_id: str) -> bool:
        """
        Remove budget for a user.

        Args:
            user_id: User identifier

        Returns:
            True if budget was removed
        """
        if user_id in self._budgets:
            del self._budgets[user_id]
            log_event("budget_removed", {"user_id": user_id})
            return True
        return False

    def __repr__(self) -> str:
        """String representation."""
        return f"CostTracker(budgets={len(self._budgets)})"
