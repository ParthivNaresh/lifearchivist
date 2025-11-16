class AgentError(Exception):
    pass


class PlanningError(AgentError):
    pass


class ExecutionError(AgentError):
    pass


class TaskExecutionError(AgentError):
    pass


class ToolExecutionError(AgentError):
    pass


class ExtractionError(ToolExecutionError):
    pass


class TimeoutError(AgentError):
    pass


class ResourceLimitError(AgentError):
    pass


class InvalidTaskError(AgentError):
    pass


class CircularDependencyError(ExecutionError):
    pass
