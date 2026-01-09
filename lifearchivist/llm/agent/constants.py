from dataclasses import dataclass
from typing import Final

MAX_JSON_CHARS: Final[int] = 200_000
QWEN_25_7B: Final[str] = "qwen2.5:7b"


class AgentModelDefaults:
    PLANNING_MODEL: Final[str] = QWEN_25_7B
    SYNTHESIS_MODEL: Final[str] = QWEN_25_7B
    CLASSIFICATION_MODEL: Final[str] = QWEN_25_7B
    TOOL_EXECUTION_MODEL: Final[str] = QWEN_25_7B

    PLANNING_TEMPERATURE: Final[float] = 0.2
    SYNTHESIS_TEMPERATURE: Final[float] = 0.7
    CLASSIFICATION_TEMPERATURE: Final[float] = 0.0
    TOOL_EXECUTION_TEMPERATURE: Final[float] = 0.0


class AgentExecutionDefaults:
    MAX_CONCURRENCY: Final[int] = 32
    MAX_TASKS: Final[int] = 20
    MAX_PHASES: Final[int] = 7
    MAX_COST_USD: Final[float] = 1.0
    MAX_TIME_SECONDS: Final[int] = 300

    PHASE_TIMEOUT_SECONDS: Final[float] = 120.0
    TASK_TIMEOUT_SECONDS: Final[float] = 60.0
    MAX_RETRIES: Final[int] = 2
    MAX_HISTORY_MESSAGES: Final[int] = 50
    MAX_DEPENDENT_BYTES: Final[int] = 256 * 1024

    BACKOFF_BASE_SECONDS: Final[float] = 0.5
    BACKOFF_MAX_SECONDS: Final[float] = 5.0


class AgentToolLimits:
    STRUCTURED_EXTRACTION_CONCURRENCY: Final[int] = 8

    @classmethod
    def get_per_tool_limits(cls) -> dict[str, int]:
        return {
            "structured_extraction": cls.STRUCTURED_EXTRACTION_CONCURRENCY,
        }


class AgentPromptLimits:
    MAX_PLAN_REASONING_CHARS: Final[int] = 2000
    MAX_PARAM_PREVIEW_CHARS: Final[int] = 256


@dataclass(frozen=True, slots=True)
class AgentModelConfig:
    planning_model: str = AgentModelDefaults.PLANNING_MODEL
    synthesis_model: str = AgentModelDefaults.SYNTHESIS_MODEL
    classification_model: str = AgentModelDefaults.CLASSIFICATION_MODEL
    tool_execution_model: str = AgentModelDefaults.TOOL_EXECUTION_MODEL

    planning_temperature: float = AgentModelDefaults.PLANNING_TEMPERATURE
    synthesis_temperature: float = AgentModelDefaults.SYNTHESIS_TEMPERATURE
    classification_temperature: float = AgentModelDefaults.CLASSIFICATION_TEMPERATURE
    tool_execution_temperature: float = AgentModelDefaults.TOOL_EXECUTION_TEMPERATURE


@dataclass(frozen=True, slots=True)
class AgentExecutionConfig:
    max_concurrency: int = AgentExecutionDefaults.MAX_CONCURRENCY
    max_tasks: int = AgentExecutionDefaults.MAX_TASKS
    max_phases: int = AgentExecutionDefaults.MAX_PHASES
    max_cost_usd: float = AgentExecutionDefaults.MAX_COST_USD
    max_time_seconds: int = AgentExecutionDefaults.MAX_TIME_SECONDS

    task_timeout_seconds: float = AgentExecutionDefaults.TASK_TIMEOUT_SECONDS
    max_retries: int = AgentExecutionDefaults.MAX_RETRIES
    max_history_messages: int = AgentExecutionDefaults.MAX_HISTORY_MESSAGES
    max_dependent_bytes: int = AgentExecutionDefaults.MAX_DEPENDENT_BYTES

    backoff_base_seconds: float = AgentExecutionDefaults.BACKOFF_BASE_SECONDS
    backoff_max_seconds: float = AgentExecutionDefaults.BACKOFF_MAX_SECONDS


@dataclass(frozen=True, slots=True)
class AgentConfig:
    model: AgentModelConfig
    execution: AgentExecutionConfig

    @classmethod
    def default(cls) -> "AgentConfig":
        return cls(
            model=AgentModelConfig(),
            execution=AgentExecutionConfig(),
        )

    @classmethod
    def with_model_overrides(
        cls,
        planning_model: str | None = None,
        synthesis_model: str | None = None,
        classification_model: str | None = None,
        tool_execution_model: str | None = None,
    ) -> "AgentConfig":
        return cls(
            model=AgentModelConfig(
                planning_model=planning_model or AgentModelDefaults.PLANNING_MODEL,
                synthesis_model=synthesis_model or AgentModelDefaults.SYNTHESIS_MODEL,
                classification_model=classification_model
                or AgentModelDefaults.CLASSIFICATION_MODEL,
                tool_execution_model=tool_execution_model
                or AgentModelDefaults.TOOL_EXECUTION_MODEL,
            ),
            execution=AgentExecutionConfig(),
        )


DEFAULT_AGENT_CONFIG: Final[AgentConfig] = AgentConfig.default()
