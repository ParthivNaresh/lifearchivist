import {
  Check,
  Circle,
  Loader2,
  AlertCircle,
  Sparkles,
  Search,
  FileText,
  Database,
  Cog,
} from 'lucide-react';
import { cn } from '../../../utils/cn';
import type {
  AgentProgress,
  AgentPhase,
  AgentTask,
  AgentTaskStatus,
  AgentPhaseStatus,
} from '../types';

interface AgentProgressIndicatorProps {
  progress: AgentProgress;
}

interface PhaseItemProps {
  phase: AgentPhase;
  index: number;
  isActive: boolean;
  isCompleted: boolean;
}

interface TaskItemProps {
  task: AgentTask;
}

const getToolIcon = (tool: string | null): React.ReactNode => {
  switch (tool) {
    case 'document_search':
      return <Search className="h-3 w-3" />;
    case 'structured_extraction':
      return <Database className="h-3 w-3" />;
    case 'text_extraction':
      return <FileText className="h-3 w-3" />;
    default:
      return <Cog className="h-3 w-3" />;
  }
};

const getToolLabel = (tool: string | null): string => {
  switch (tool) {
    case 'document_search':
      return 'Searching documents...';
    case 'structured_extraction':
      return 'Extracting data...';
    case 'text_extraction':
      return 'Analyzing text...';
    default:
      return 'Processing...';
  }
};

const getStatusIcon = (status: AgentTaskStatus | AgentPhaseStatus): React.ReactNode => {
  switch (status) {
    case 'completed':
      return <Check className="h-3 w-3 text-green-500" />;
    case 'running':
      return <Loader2 className="h-3 w-3 animate-spin text-blue-500" />;
    case 'failed':
      return <AlertCircle className="h-3 w-3 text-red-500" />;
    default:
      return <Circle className="h-3 w-3 text-muted-foreground/40" />;
  }
};

const TaskItem: React.FC<TaskItemProps> = ({ task }) => {
  const isActive = task.status === 'running';
  const isCompleted = task.status === 'completed';
  const isFailed = task.status === 'failed';

  return (
    <div
      className={cn(
        'flex items-center gap-2 py-1.5 px-2 rounded text-xs transition-all duration-300',
        isActive && 'bg-blue-500/15 border border-blue-500/30',
        isCompleted && 'opacity-60',
        isFailed && 'bg-red-500/15 border border-red-500/30'
      )}
    >
      <span className="flex-shrink-0">{getStatusIcon(task.status)}</span>
      <span className={cn('flex-shrink-0', isActive && 'text-blue-400')}>
        {getToolIcon(task.tool)}
      </span>
      <span
        className={cn(
          'truncate flex-1',
          isActive && 'text-blue-300 font-medium',
          isFailed && 'text-red-400'
        )}
      >
        {isActive ? getToolLabel(task.tool) : task.description || getToolLabel(task.tool)}
      </span>
    </div>
  );
};

const PlanningTaskIndicator: React.FC = () => {
  return (
    <div className="flex items-center gap-2 py-1.5 px-2 rounded text-xs bg-blue-500/10 border border-blue-500/20">
      <Loader2 className="h-3 w-3 animate-spin text-blue-500" />
      <Cog className="h-3 w-3 text-blue-400" />
      <span className="text-blue-300">Planning tasks...</span>
    </div>
  );
};

const PhaseItem: React.FC<PhaseItemProps> = ({ phase, index, isActive, isCompleted }) => {
  const effectivelyActive = isActive && !isCompleted;
  const hasTasks = phase.tasks.length > 0;
  const showTasks = effectivelyActive;
  const isPlanning = effectivelyActive && !hasTasks;
  const isPending = !effectivelyActive && !isCompleted;

  return (
    <div className={cn('transition-all duration-300', isPending && 'opacity-40')}>
      <div
        className={cn(
          'flex items-center gap-2 py-2 px-2.5 rounded-md transition-all duration-300',
          effectivelyActive && 'bg-blue-500/10 border border-blue-500/20',
          isCompleted && 'bg-green-500/5'
        )}
      >
        <span
          className={cn(
            'flex-shrink-0 w-6 h-6 rounded-full flex items-center justify-center text-xs font-semibold transition-all duration-300',
            isCompleted && 'bg-green-500/20 text-green-400',
            effectivelyActive && 'bg-blue-500/20 text-blue-400 ring-2 ring-blue-500/30',
            isPending && 'bg-muted/50 text-muted-foreground'
          )}
        >
          {isCompleted ? <Check className="h-3.5 w-3.5" /> : index + 1}
        </span>
        <span
          className={cn(
            'text-sm truncate flex-1 transition-colors duration-300',
            effectivelyActive && 'font-medium text-blue-200',
            isCompleted && 'text-green-300/80',
            isPending && 'text-muted-foreground'
          )}
        >
          {formatPhaseDescription(phase.description)}
        </span>
        {effectivelyActive && (
          <Loader2 className="h-4 w-4 animate-spin text-blue-400 flex-shrink-0" />
        )}
        {isCompleted && <Check className="h-4 w-4 text-green-500 flex-shrink-0" />}
      </div>

      {showTasks && (
        <div className="ml-8 mt-1.5 space-y-1 border-l-2 border-blue-500/30 pl-3">
          {isPlanning && <PlanningTaskIndicator />}
          {phase.tasks.map((task) => (
            <TaskItem key={task.task_id} task={task} />
          ))}
        </div>
      )}
    </div>
  );
};

const formatPhaseDescription = (description: string): string => {
  if (description.length > 55) {
    return description.substring(0, 52) + '...';
  }
  return description;
};

const SynthesisIndicator: React.FC = () => {
  return (
    <div className="flex items-center gap-2 py-2 px-3 rounded-md bg-purple-500/15 border border-purple-500/30">
      <Sparkles className="h-4 w-4 text-purple-400 animate-pulse" />
      <span className="text-sm font-medium text-purple-300">Generating response</span>
      <span className="flex gap-1 ml-auto text-purple-400">
        <span className="animate-bounce text-xs" style={{ animationDelay: '0ms' }}>
          ●
        </span>
        <span className="animate-bounce text-xs" style={{ animationDelay: '150ms' }}>
          ●
        </span>
        <span className="animate-bounce text-xs" style={{ animationDelay: '300ms' }}>
          ●
        </span>
      </span>
    </div>
  );
};

const PlanningIndicator: React.FC = () => {
  return (
    <div className="flex items-center gap-3 text-sm text-muted-foreground p-4 bg-accent/50 rounded-lg border border-border/50">
      <div className="relative">
        <Loader2 className="h-5 w-5 animate-spin text-blue-500" />
        <div className="absolute inset-0 h-5 w-5 animate-ping opacity-20 rounded-full bg-blue-500" />
      </div>
      <div>
        <span className="font-medium text-foreground">Creating plan...</span>
        <p className="text-xs text-muted-foreground mt-0.5">Analyzing your request</p>
      </div>
    </div>
  );
};

const ErrorIndicator: React.FC<{ error: string }> = ({ error }) => {
  return (
    <div className="flex items-start gap-3 text-sm p-4 bg-red-500/10 rounded-lg border border-red-500/30">
      <AlertCircle className="h-5 w-5 text-red-400 flex-shrink-0 mt-0.5" />
      <div>
        <span className="font-medium text-red-300">Processing failed</span>
        <p className="text-xs text-red-400/80 mt-1 break-words">{error}</p>
      </div>
    </div>
  );
};

const determinePhaseState = (
  index: number,
  phase: AgentPhase,
  completedPhases: string[],
  isSynthesizing: boolean,
  totalPhases: number
): { isActive: boolean; isCompleted: boolean } => {
  const isCompleted = completedPhases.includes(phase.phase_id);

  if (isCompleted) {
    return { isActive: false, isCompleted: true };
  }

  if (isSynthesizing) {
    return { isActive: false, isCompleted: false };
  }

  if (phase.status === 'running') {
    return { isActive: true, isCompleted: false };
  }

  const isNextPhase = index === completedPhases.length;
  if (isNextPhase && completedPhases.length < totalPhases) {
    return { isActive: true, isCompleted: false };
  }

  return { isActive: false, isCompleted: false };
};

export const AgentProgressIndicator: React.FC<AgentProgressIndicatorProps> = ({ progress }) => {
  const { phases, completedPhases, isSynthesizing, error } = progress;

  if (error) {
    return <ErrorIndicator error={error} />;
  }

  if (phases.length === 0 && !isSynthesizing) {
    return <PlanningIndicator />;
  }

  const completedCount = completedPhases.length;
  const totalCount = phases.length;

  return (
    <div className="bg-accent/30 rounded-lg p-4 space-y-3 min-w-[320px] max-w-md border border-border/30">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-xs font-medium text-muted-foreground">
          <Sparkles className="h-3.5 w-3.5 text-blue-400" />
          <span>Agent Processing</span>
        </div>
        {totalCount > 0 && (
          <span className="text-xs text-muted-foreground">
            {completedCount}/{totalCount} phases
          </span>
        )}
      </div>

      <div className="space-y-1.5">
        {phases.map((phase, index) => {
          const { isActive, isCompleted } = determinePhaseState(
            index,
            phase,
            completedPhases,
            isSynthesizing,
            phases.length
          );
          return (
            <PhaseItem
              key={phase.phase_id}
              phase={phase}
              index={index}
              isActive={isActive}
              isCompleted={isCompleted}
            />
          );
        })}
      </div>

      {isSynthesizing && (
        <div className="pt-2 border-t border-border/30">
          <SynthesisIndicator />
        </div>
      )}
    </div>
  );
};
