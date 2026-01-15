export { useWebSocket } from './useWebSocket';
export type { WSEvent, WSEventType, Toast } from './useWebSocket';

export { usePipelineSocket } from './usePipelineSocket';
export type { PipelineEvent, PipelineEventType, PipelineToast } from './usePipelineSocket';

export {
  useOpportunities,
  useOpportunity,
  usePipelineStats,
  useCreateOpportunity,
  useUpdateOpportunity,
  useDeleteOpportunity,
  useMoveOpportunity,
  useAnalyzeOpportunity,
  useGenerateProposal,
  useEstimateEffort,
  useSimilarOpportunities,
  useMoveOpportunityOptimistic,
  pipelineKeys,
} from './usePipeline';
