// Agent Performance Panel Component (v50.0)
// Displays per-agent statistics and success rates

import { useState } from 'react';
import { Users, TrendingUp, TrendingDown, AlertTriangle, DollarSign, Activity, RefreshCw, Loader2, ChevronDown, ChevronRight } from 'lucide-react';
import clsx from 'clsx';
import type { AgentStats } from '../../types';

interface AgentPerformancePanelProps {
  agentStats: AgentStats[];
  loading?: boolean;
  onRefresh?: () => void;
}

export function AgentPerformancePanel({ agentStats, loading = false, onRefresh }: AgentPerformancePanelProps) {
  const [expanded, setExpanded] = useState(true);
  const [sortBy, setSortBy] = useState<'success_rate' | 'total_actions' | 'avg_cost'>('success_rate');
  const [sortDesc, setSortDesc] = useState(true);

  // Sort agents
  const sortedAgents = [...agentStats].sort((a, b) => {
    let aVal: number, bVal: number;
    switch (sortBy) {
      case 'success_rate':
        aVal = a.success_rate;
        bVal = b.success_rate;
        break;
      case 'total_actions':
        aVal = a.total_actions;
        bVal = b.total_actions;
        break;
      case 'avg_cost':
        aVal = a.avg_cost_per_action;
        bVal = b.avg_cost_per_action;
        break;
      default:
        aVal = a.success_rate;
        bVal = b.success_rate;
    }
    return sortDesc ? bVal - aVal : aVal - bVal;
  });

  // Calculate summary stats
  const totalActions = agentStats.reduce((sum, a) => sum + a.total_actions, 0);
  const avgSuccessRate = agentStats.length > 0
    ? agentStats.reduce((sum, a) => sum + a.success_rate, 0) / agentStats.length
    : 0;
  const totalCost = agentStats.reduce((sum, a) => sum + (a.avg_cost_per_action * a.total_actions), 0);

  // Get status color based on success rate
  const getSuccessRateColor = (rate: number): string => {
    if (rate >= 0.9) return 'text-green-600';
    if (rate >= 0.7) return 'text-yellow-600';
    return 'text-red-600';
  };

  const getSuccessRateBg = (rate: number): string => {
    if (rate >= 0.9) return 'bg-green-100';
    if (rate >= 0.7) return 'bg-yellow-100';
    return 'bg-red-100';
  };

  // Format agent name for display
  const formatAgentName = (name: string): string => {
    return name
      .replace(/_/g, ' ')
      .replace(/([A-Z])/g, ' $1')
      .split(' ')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
      .join(' ')
      .trim();
  };

  if (loading && agentStats.length === 0) {
    return (
      <div className="bg-white/80 backdrop-blur rounded-2xl shadow-lg border border-zinc-200 p-6">
        <div className="flex items-center justify-center py-8">
          <Loader2 className="w-6 h-6 animate-spin text-zinc-400" />
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white/80 backdrop-blur rounded-2xl shadow-lg border border-zinc-200 p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <button
          onClick={() => setExpanded(!expanded)}
          className="flex items-center gap-3 hover:opacity-80 transition"
        >
          <div className="p-2 bg-purple-100 rounded-xl">
            <Users className="w-5 h-5 text-purple-600" />
          </div>
          <div className="text-left">
            <h2 className="text-lg font-bold text-zinc-900">Agent Performance</h2>
            <p className="text-sm text-zinc-600">
              {agentStats.length} agents tracked
            </p>
          </div>
          {expanded ? (
            <ChevronDown className="w-5 h-5 text-zinc-400" />
          ) : (
            <ChevronRight className="w-5 h-5 text-zinc-400" />
          )}
        </button>

        {onRefresh && (
          <button
            onClick={onRefresh}
            disabled={loading}
            className="p-2 hover:bg-zinc-100 rounded-xl transition disabled:opacity-50"
            title="Refresh"
          >
            <RefreshCw className={clsx("w-5 h-5 text-zinc-600", loading && "animate-spin")} />
          </button>
        )}
      </div>

      {expanded && (
        <>
          {/* Summary Cards */}
          <div className="grid grid-cols-3 gap-4 mb-6">
            <div className="p-4 bg-gradient-to-br from-blue-50 to-blue-100 rounded-xl border border-blue-200">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs text-blue-600 font-medium">Total Actions</p>
                  <p className="text-2xl font-bold text-blue-900">{totalActions.toLocaleString()}</p>
                </div>
                <Activity className="w-8 h-8 text-blue-400" />
              </div>
            </div>

            <div className="p-4 bg-gradient-to-br from-green-50 to-green-100 rounded-xl border border-green-200">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs text-green-600 font-medium">Avg Success Rate</p>
                  <p className="text-2xl font-bold text-green-900">{(avgSuccessRate * 100).toFixed(1)}%</p>
                </div>
                <TrendingUp className="w-8 h-8 text-green-400" />
              </div>
            </div>

            <div className="p-4 bg-gradient-to-br from-amber-50 to-amber-100 rounded-xl border border-amber-200">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs text-amber-600 font-medium">Est. Total Cost</p>
                  <p className="text-2xl font-bold text-amber-900">${totalCost.toFixed(4)}</p>
                </div>
                <DollarSign className="w-8 h-8 text-amber-400" />
              </div>
            </div>
          </div>

          {/* Sort Controls */}
          <div className="flex items-center gap-2 mb-4">
            <span className="text-xs text-zinc-600">Sort by:</span>
            {(['success_rate', 'total_actions', 'avg_cost'] as const).map((key) => (
              <button
                key={key}
                onClick={() => {
                  if (sortBy === key) {
                    setSortDesc(!sortDesc);
                  } else {
                    setSortBy(key);
                    setSortDesc(true);
                  }
                }}
                className={clsx(
                  "px-3 py-1 text-xs font-medium rounded-lg transition",
                  sortBy === key
                    ? "bg-purple-600 text-white"
                    : "bg-zinc-100 text-zinc-700 hover:bg-zinc-200"
                )}
              >
                {key === 'success_rate' ? 'Success Rate' :
                 key === 'total_actions' ? 'Actions' : 'Cost'}
                {sortBy === key && (sortDesc ? ' ↓' : ' ↑')}
              </button>
            ))}
          </div>

          {/* Agent List */}
          {agentStats.length === 0 ? (
            <div className="text-center py-8">
              <Users className="w-12 h-12 text-zinc-300 mx-auto mb-2" />
              <p className="text-zinc-500">No agent data available yet</p>
              <p className="text-xs text-zinc-400 mt-1">Run some tasks to see agent performance</p>
            </div>
          ) : (
            <div className="space-y-3 max-h-96 overflow-y-auto">
              {sortedAgents.map((agent, index) => (
                <div
                  key={agent.agent_name}
                  className="p-4 bg-zinc-50 rounded-xl hover:bg-zinc-100 transition"
                >
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-mono text-zinc-400">#{index + 1}</span>
                        <h3 className="font-bold text-zinc-900">{formatAgentName(agent.agent_name)}</h3>
                      </div>
                    </div>

                    {/* Success Rate Badge */}
                    <div className={clsx(
                      "flex items-center gap-1 px-3 py-1 rounded-full text-sm font-bold",
                      getSuccessRateBg(agent.success_rate),
                      getSuccessRateColor(agent.success_rate)
                    )}>
                      {agent.success_rate >= 0.9 ? (
                        <TrendingUp className="w-4 h-4" />
                      ) : agent.success_rate >= 0.7 ? (
                        <Activity className="w-4 h-4" />
                      ) : (
                        <TrendingDown className="w-4 h-4" />
                      )}
                      {(agent.success_rate * 100).toFixed(1)}%
                    </div>
                  </div>

                  {/* Stats Grid */}
                  <div className="grid grid-cols-3 gap-4 text-xs">
                    <div>
                      <p className="text-zinc-500">Total Actions</p>
                      <p className="font-bold text-zinc-900">{agent.total_actions.toLocaleString()}</p>
                    </div>
                    <div>
                      <p className="text-zinc-500">Success Count</p>
                      <p className="font-bold text-green-600">{agent.success_count.toLocaleString()}</p>
                    </div>
                    <div>
                      <p className="text-zinc-500">Cost/Action</p>
                      <p className="font-bold text-zinc-900">${agent.avg_cost_per_action.toFixed(6)}</p>
                    </div>
                  </div>

                  {/* Progress Bar */}
                  <div className="mt-3">
                    <div className="w-full bg-zinc-200 rounded-full h-2 overflow-hidden">
                      <div
                        className={clsx(
                          "h-2 rounded-full transition-all duration-500",
                          agent.success_rate >= 0.9 ? "bg-green-500" :
                          agent.success_rate >= 0.7 ? "bg-yellow-500" : "bg-red-500"
                        )}
                        style={{ width: `${agent.success_rate * 100}%` }}
                      />
                    </div>
                  </div>

                  {/* Common Failures */}
                  {agent.common_failures && agent.common_failures.length > 0 && (
                    <div className="mt-3 pt-3 border-t border-zinc-200">
                      <p className="text-xs text-zinc-500 mb-2 flex items-center gap-1">
                        <AlertTriangle className="w-3 h-3" />
                        Common Failures:
                      </p>
                      <div className="flex flex-wrap gap-1">
                        {agent.common_failures.slice(0, 3).map((failure, idx) => (
                          <span
                            key={idx}
                            className="px-2 py-0.5 bg-red-50 text-red-700 text-xs rounded-full border border-red-200"
                          >
                            {failure}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
