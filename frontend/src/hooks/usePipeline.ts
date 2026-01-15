/**
 * NH Mission Control - Pipeline Hooks
 * =====================================
 *
 * React Query hooks for pipeline data management.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { pipelineApi, type ListOpportunitiesParams } from '../lib/pipeline-api';
import type {
  Opportunity,
  OpportunityCreate,
  OpportunityUpdate,
  OpportunityStatus
} from '../types';

// ==========================================================================
// Query Keys
// ==========================================================================

export const pipelineKeys = {
  all: ['pipeline'] as const,
  opportunities: () => [...pipelineKeys.all, 'opportunities'] as const,
  opportunityList: (params: ListOpportunitiesParams) =>
    [...pipelineKeys.opportunities(), 'list', params] as const,
  opportunity: (id: string) => [...pipelineKeys.opportunities(), id] as const,
  stats: () => [...pipelineKeys.all, 'stats'] as const,
  analysis: (id: string) => [...pipelineKeys.opportunities(), id, 'analysis'] as const,
  proposal: (id: string) => [...pipelineKeys.opportunities(), id, 'proposal'] as const,
  estimate: (id: string) => [...pipelineKeys.opportunities(), id, 'estimate'] as const,
  similar: (id: string) => [...pipelineKeys.opportunities(), id, 'similar'] as const,
};

// ==========================================================================
// List & Get Hooks
// ==========================================================================

/**
 * Hook to list opportunities with filters
 */
export function useOpportunities(params: ListOpportunitiesParams = {}) {
  return useQuery({
    queryKey: pipelineKeys.opportunityList(params),
    queryFn: () => pipelineApi.listOpportunities(params),
  });
}

/**
 * Hook to get single opportunity
 */
export function useOpportunity(id: string) {
  return useQuery({
    queryKey: pipelineKeys.opportunity(id),
    queryFn: () => pipelineApi.getOpportunity(id),
    enabled: !!id,
  });
}

/**
 * Hook to get pipeline statistics
 */
export function usePipelineStats() {
  return useQuery({
    queryKey: pipelineKeys.stats(),
    queryFn: () => pipelineApi.getStats(),
  });
}

// ==========================================================================
// Mutation Hooks
// ==========================================================================

/**
 * Hook to create opportunity
 */
export function useCreateOpportunity() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: OpportunityCreate) => pipelineApi.createOpportunity(data),
    onSuccess: () => {
      // Invalidate all opportunity lists
      queryClient.invalidateQueries({ queryKey: pipelineKeys.opportunities() });
      queryClient.invalidateQueries({ queryKey: pipelineKeys.stats() });
    },
  });
}

/**
 * Hook to update opportunity
 */
export function useUpdateOpportunity() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: OpportunityUpdate }) =>
      pipelineApi.updateOpportunity(id, data),
    onSuccess: (updatedOpportunity) => {
      // Update cache for this specific opportunity
      queryClient.setQueryData(
        pipelineKeys.opportunity(updatedOpportunity.id),
        updatedOpportunity
      );
      // Invalidate lists
      queryClient.invalidateQueries({ queryKey: pipelineKeys.opportunities() });
    },
  });
}

/**
 * Hook to delete opportunity
 */
export function useDeleteOpportunity() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => pipelineApi.deleteOpportunity(id),
    onSuccess: (_, id) => {
      // Remove from cache
      queryClient.removeQueries({ queryKey: pipelineKeys.opportunity(id) });
      // Invalidate lists
      queryClient.invalidateQueries({ queryKey: pipelineKeys.opportunities() });
      queryClient.invalidateQueries({ queryKey: pipelineKeys.stats() });
    },
  });
}

/**
 * Hook to move opportunity to new status
 */
export function useMoveOpportunity() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, status, notes }: { id: string; status: OpportunityStatus; notes?: string }) =>
      pipelineApi.moveOpportunity(id, status, notes),
    onSuccess: (updatedOpportunity) => {
      // Update cache
      queryClient.setQueryData(
        pipelineKeys.opportunity(updatedOpportunity.id),
        updatedOpportunity
      );
      // Invalidate lists and stats
      queryClient.invalidateQueries({ queryKey: pipelineKeys.opportunities() });
      queryClient.invalidateQueries({ queryKey: pipelineKeys.stats() });
    },
  });
}

// ==========================================================================
// Analysis Hooks
// ==========================================================================

/**
 * Hook to run NH analysis
 */
export function useAnalyzeOpportunity() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => pipelineApi.analyzeOpportunity(id),
    onSuccess: (analysis, id) => {
      // Cache analysis result
      queryClient.setQueryData(pipelineKeys.analysis(id), analysis);
      // Update opportunity with new score
      queryClient.invalidateQueries({ queryKey: pipelineKeys.opportunity(id) });
    },
  });
}

/**
 * Hook to generate proposal
 */
export function useGenerateProposal() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => pipelineApi.generateProposal(id),
    onSuccess: (proposal, id) => {
      queryClient.setQueryData(pipelineKeys.proposal(id), proposal);
    },
  });
}

/**
 * Hook to estimate effort
 */
export function useEstimateEffort() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => pipelineApi.estimateEffort(id),
    onSuccess: (estimate, id) => {
      queryClient.setQueryData(pipelineKeys.estimate(id), estimate);
    },
  });
}

/**
 * Hook to get similar opportunities
 */
export function useSimilarOpportunities(id: string, enabled = true) {
  return useQuery({
    queryKey: pipelineKeys.similar(id),
    queryFn: () => pipelineApi.getSimilarOpportunities(id),
    enabled: enabled && !!id,
  });
}

// ==========================================================================
// Optimistic Update Helpers
// ==========================================================================

/**
 * Hook with optimistic updates for drag-and-drop
 */
export function useMoveOpportunityOptimistic() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, status, notes }: { id: string; status: OpportunityStatus; notes?: string }) =>
      pipelineApi.moveOpportunity(id, status, notes),

    // Optimistic update
    onMutate: async ({ id, status }) => {
      // Cancel outgoing refetches
      await queryClient.cancelQueries({ queryKey: pipelineKeys.opportunities() });

      // Snapshot previous value
      const previousOpportunity = queryClient.getQueryData<Opportunity>(
        pipelineKeys.opportunity(id)
      );

      // Optimistically update
      if (previousOpportunity) {
        queryClient.setQueryData(pipelineKeys.opportunity(id), {
          ...previousOpportunity,
          status,
          probability: status === 'won' ? 100 : status === 'lost' ? 0 : previousOpportunity.probability,
        });
      }

      return { previousOpportunity };
    },

    // Rollback on error
    onError: (_err, { id }, context) => {
      if (context?.previousOpportunity) {
        queryClient.setQueryData(
          pipelineKeys.opportunity(id),
          context.previousOpportunity
        );
      }
    },

    // Always refetch after error or success
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: pipelineKeys.opportunities() });
      queryClient.invalidateQueries({ queryKey: pipelineKeys.stats() });
    },
  });
}
