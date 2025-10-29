"""
Provider Health Monitor - Monitors provider health and availability.

Responsible for:
- Periodic health checks
- Provider status tracking
- Automatic provider disabling on failures
- Health metrics and alerting
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict, Optional

from ..utils.logging import log_event, track
from .base_provider import BaseLLMProvider
from .provider_registry import ProviderRegistry

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Provider health status."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class HealthCheck:
    """
    Result of a health check.

    Attributes:
        provider_id: Provider identifier
        status: Health status
        timestamp: When check was performed
        response_time_ms: Response time in milliseconds
        error: Error message if unhealthy
        consecutive_failures: Number of consecutive failures
    """

    provider_id: str
    status: HealthStatus
    timestamp: datetime
    response_time_ms: Optional[float] = None
    error: Optional[str] = None
    consecutive_failures: int = 0


class ProviderHealthMonitor:
    """
    Monitors health of LLM providers.

    Performs periodic health checks and tracks provider availability.
    Can automatically disable unhealthy providers.
    """

    def __init__(
        self,
        registry: ProviderRegistry,
        check_interval_seconds: int = 60,
        failure_threshold: int = 3,
        auto_disable: bool = True,
    ):
        """
        Initialize health monitor.

        Args:
            registry: Provider registry to monitor
            check_interval_seconds: Seconds between health checks
            failure_threshold: Consecutive failures before marking unhealthy
            auto_disable: Automatically disable unhealthy providers
        """
        self.registry = registry
        self.check_interval = check_interval_seconds
        self.failure_threshold = failure_threshold
        self.auto_disable = auto_disable

        self._health_status: Dict[str, HealthCheck] = {}
        self._monitoring_task: Optional[asyncio.Task] = None
        self._running = False

    async def start(self) -> None:
        """
        Start health monitoring.

        Begins periodic health checks in background task.
        """
        if self._running:
            log_event(
                "health_monitor_already_running",
                level=logging.WARNING,
            )
            return

        self._running = True
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())

        log_event(
            "health_monitor_started",
            {
                "check_interval": self.check_interval,
                "failure_threshold": self.failure_threshold,
                "auto_disable": self.auto_disable,
            },
        )

    async def stop(self) -> None:
        """
        Stop health monitoring.

        Cancels background monitoring task.
        """
        if not self._running:
            return

        self._running = False

        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass

        log_event("health_monitor_stopped")

    async def _monitoring_loop(self) -> None:
        """
        Main monitoring loop.

        Runs periodic health checks on all providers.
        """
        while self._running:
            try:
                await self._check_all_providers()
                await asyncio.sleep(self.check_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                log_event(
                    "health_monitor_error",
                    {"error": str(e), "error_type": type(e).__name__},
                    level=logging.ERROR,
                )
                # Continue monitoring despite errors
                await asyncio.sleep(self.check_interval)

    @track(
        operation="health_check_all_providers",
        track_performance=True,
        frequency="low_frequency",
    )
    async def _check_all_providers(self) -> None:
        """Check health of all registered providers."""
        providers = self.registry.list_all()

        if not providers:
            return

        # Check all providers concurrently
        tasks = [self._check_provider(provider) for provider in providers]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Log summary
        healthy = sum(
            1
            for r in results
            if isinstance(r, HealthCheck) and r.status == HealthStatus.HEALTHY
        )
        unhealthy = sum(
            1
            for r in results
            if isinstance(r, HealthCheck) and r.status == HealthStatus.UNHEALTHY
        )

        log_event(
            "health_check_completed",
            {
                "total_providers": len(providers),
                "healthy": healthy,
                "unhealthy": unhealthy,
            },
        )

    @track(
        operation="health_check_provider",
        include_args=["provider_id"],
        track_performance=True,
        frequency="medium_frequency",
    )
    async def _check_provider(self, provider: BaseLLMProvider) -> HealthCheck:
        """
        Check health of a single provider.

        Args:
            provider: Provider to check

        Returns:
            Health check result
        """
        provider_id = provider.provider_id
        start_time = datetime.now()

        try:
            # Validate credentials as health check
            is_valid = await asyncio.wait_for(
                provider.validate_credentials(),
                timeout=10.0,  # 10 second timeout
            )

            response_time = (datetime.now() - start_time).total_seconds() * 1000

            if is_valid:
                status = HealthStatus.HEALTHY
                error = None
                consecutive_failures = 0
            else:
                status = HealthStatus.UNHEALTHY
                error = "Credential validation failed"
                consecutive_failures = self._get_consecutive_failures(provider_id) + 1

            health_check = HealthCheck(
                provider_id=provider_id,
                status=status,
                timestamp=datetime.now(),
                response_time_ms=response_time,
                error=error,
                consecutive_failures=consecutive_failures,
            )

            self._health_status[provider_id] = health_check

            # Handle unhealthy provider
            if status == HealthStatus.UNHEALTHY:
                await self._handle_unhealthy_provider(provider, health_check)

            log_event(
                "provider_health_checked",
                {
                    "provider_id": provider_id,
                    "status": status.value,
                    "response_time_ms": response_time,
                    "consecutive_failures": consecutive_failures,
                },
            )

            return health_check

        except asyncio.TimeoutError:
            consecutive_failures = self._get_consecutive_failures(provider_id) + 1

            health_check = HealthCheck(
                provider_id=provider_id,
                status=HealthStatus.UNHEALTHY,
                timestamp=datetime.now(),
                error="Health check timeout",
                consecutive_failures=consecutive_failures,
            )

            self._health_status[provider_id] = health_check

            await self._handle_unhealthy_provider(provider, health_check)

            log_event(
                "provider_health_timeout",
                {
                    "provider_id": provider_id,
                    "consecutive_failures": consecutive_failures,
                },
                level=logging.WARNING,
            )

            return health_check

        except Exception as e:
            consecutive_failures = self._get_consecutive_failures(provider_id) + 1

            health_check = HealthCheck(
                provider_id=provider_id,
                status=HealthStatus.UNHEALTHY,
                timestamp=datetime.now(),
                error=str(e),
                consecutive_failures=consecutive_failures,
            )

            self._health_status[provider_id] = health_check

            await self._handle_unhealthy_provider(provider, health_check)

            log_event(
                "provider_health_check_failed",
                {
                    "provider_id": provider_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "consecutive_failures": consecutive_failures,
                },
                level=logging.ERROR,
            )

            return health_check

    async def _handle_unhealthy_provider(
        self,
        provider: BaseLLMProvider,
        health_check: HealthCheck,
    ) -> None:
        """
        Handle unhealthy provider.

        Args:
            provider: Unhealthy provider
            health_check: Health check result
        """
        # Check if threshold exceeded
        if health_check.consecutive_failures >= self.failure_threshold:
            log_event(
                "provider_failure_threshold_exceeded",
                {
                    "provider_id": provider.provider_id,
                    "consecutive_failures": health_check.consecutive_failures,
                    "threshold": self.failure_threshold,
                    "auto_disable": self.auto_disable,
                },
                level=logging.ERROR,
            )

            # Auto-disable if configured
            if self.auto_disable:
                # Note: We don't actually unregister, just mark as unhealthy
                # The router should check health status before routing
                log_event(
                    "provider_auto_disabled",
                    {"provider_id": provider.provider_id},
                    level=logging.WARNING,
                )

    def _get_consecutive_failures(self, provider_id: str) -> int:
        """
        Get consecutive failure count for provider.

        Args:
            provider_id: Provider identifier

        Returns:
            Number of consecutive failures
        """
        health_check = self._health_status.get(provider_id)
        if health_check is None:
            return 0

        if health_check.status == HealthStatus.HEALTHY:
            return 0

        return health_check.consecutive_failures

    def get_health(self, provider_id: str) -> Optional[HealthCheck]:
        """
        Get health status for a provider.

        Args:
            provider_id: Provider identifier

        Returns:
            Health check result or None if not checked yet
        """
        return self._health_status.get(provider_id)

    def is_healthy(self, provider_id: str) -> bool:
        """
        Check if provider is healthy.

        Args:
            provider_id: Provider identifier

        Returns:
            True if healthy, False otherwise
        """
        health_check = self._health_status.get(provider_id)

        if health_check is None:
            # Unknown status, assume healthy
            return True

        return health_check.status == HealthStatus.HEALTHY

    def get_all_health(self) -> Dict[str, HealthCheck]:
        """
        Get health status for all providers.

        Returns:
            Dictionary mapping provider ID to health check
        """
        return self._health_status.copy()

    async def force_check(self, provider_id: str) -> Optional[HealthCheck]:
        """
        Force immediate health check for a provider.

        Args:
            provider_id: Provider identifier

        Returns:
            Health check result or None if provider not found
        """
        provider = self.registry.get(provider_id)

        if provider is None:
            return None

        return await self._check_provider(provider)

    @property
    def is_running(self) -> bool:
        """Check if monitor is running."""
        return self._running

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"ProviderHealthMonitor(providers={len(self._health_status)}, "
            f"running={self._running})"
        )
