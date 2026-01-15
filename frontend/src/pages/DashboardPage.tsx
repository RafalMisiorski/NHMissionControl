/**
 * NH Mission Control - Dashboard Page
 * =====================================
 *
 * Main dashboard with pipeline stats and metrics.
 *
 * EPOCH 3 - Pipeline Module (ACTIVE)
 */

import {
  TrendingUp,
  TrendingDown,
  DollarSign,
  Target,
  Briefcase,
  ArrowRight,
  Loader2,
  AlertCircle,
} from 'lucide-react';
import { Link } from 'react-router-dom';
import { usePipelineStats, useOpportunities } from '../hooks/usePipeline';
import { useAuth } from '../providers/AuthProvider';
import type { OpportunityStatus } from '../types';

// ==========================================================================
// Metric Card Component
// ==========================================================================

interface MetricCardProps {
  title: string;
  value: string | number;
  change?: number;
  icon: React.ReactNode;
  loading?: boolean;
}

function MetricCard({ title, value, change, icon, loading }: MetricCardProps) {
  return (
    <div className="rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-6">
      <div className="flex items-center justify-between">
        <div className="p-2 rounded-lg bg-gray-100 dark:bg-gray-800">
          {icon}
        </div>
        {change !== undefined && (
          <div className={`flex items-center gap-1 text-sm ${
            change >= 0 ? 'text-green-600' : 'text-red-600'
          }`}>
            {change >= 0 ? <TrendingUp size={16} /> : <TrendingDown size={16} />}
            <span>{Math.abs(change)}%</span>
          </div>
        )}
      </div>
      <div className="mt-4">
        <p className="text-sm text-gray-500 dark:text-gray-400">{title}</p>
        {loading ? (
          <div className="h-8 mt-1 flex items-center">
            <Loader2 className="animate-spin text-gray-400" size={20} />
          </div>
        ) : (
          <p className="text-2xl font-semibold mt-1">{value}</p>
        )}
      </div>
    </div>
  );
}

// ==========================================================================
// Pipeline Stage Card
// ==========================================================================

interface StageCardProps {
  status: OpportunityStatus;
  label: string;
  count: number;
  value: number;
  color: string;
}

function StageCard({ status, label, count, value, color }: StageCardProps) {
  return (
    <Link
      to={`/pipeline?status=${status}`}
      className="flex items-center justify-between p-4 rounded-lg border border-gray-200 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors"
    >
      <div className="flex items-center gap-3">
        <div className={`w-3 h-3 rounded-full ${color}`} />
        <div>
          <p className="font-medium">{label}</p>
          <p className="text-sm text-gray-500">{count} opportunities</p>
        </div>
      </div>
      <div className="text-right">
        <p className="font-semibold">{value.toLocaleString()}</p>
        <ArrowRight size={16} className="text-gray-400 ml-auto mt-1" />
      </div>
    </Link>
  );
}

// ==========================================================================
// Recent Opportunities
// ==========================================================================

function RecentOpportunities() {
  const { data, isLoading, error } = useOpportunities({ page_size: 5 });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="animate-spin text-gray-400" size={24} />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center gap-2 text-red-500 py-4">
        <AlertCircle size={16} />
        <span>Failed to load opportunities</span>
      </div>
    );
  }

  if (!data?.items.length) {
    return (
      <div className="text-center py-8 text-gray-500">
        <Briefcase size={32} className="mx-auto mb-2 opacity-50" />
        <p>No opportunities yet</p>
        <Link to="/pipeline" className="text-blue-500 hover:underline text-sm">
          Add your first opportunity
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {data.items.map((opp) => (
        <Link
          key={opp.id}
          to={`/pipeline?id=${opp.id}`}
          className="block p-4 rounded-lg border border-gray-200 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors"
        >
          <div className="flex items-start justify-between">
            <div className="flex-1 min-w-0">
              <p className="font-medium truncate">{opp.title}</p>
              <p className="text-sm text-gray-500 mt-1">
                {opp.client_name || 'Unknown client'} - {opp.source}
              </p>
            </div>
            <div className="text-right ml-4">
              {opp.value && (
                <p className="font-semibold">{Number(opp.value).toLocaleString()}</p>
              )}
              <span className={`inline-block px-2 py-0.5 text-xs rounded-full mt-1 ${getStatusColor(opp.status)}`}>
                {opp.status}
              </span>
            </div>
          </div>
          {opp.nh_score !== null && (
            <div className="mt-2 flex items-center gap-2">
              <div className="flex-1 h-1.5 bg-gray-200 dark:bg-gray-700 rounded-full">
                <div
                  className={`h-full rounded-full ${getScoreColor(opp.nh_score)}`}
                  style={{ width: `${opp.nh_score}%` }}
                />
              </div>
              <span className="text-xs text-gray-500">NH: {opp.nh_score}</span>
            </div>
          )}
        </Link>
      ))}
    </div>
  );
}

// ==========================================================================
// Helpers
// ==========================================================================

function getStatusColor(status: OpportunityStatus): string {
  const colors: Record<OpportunityStatus, string> = {
    lead: 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300',
    qualified: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
    proposal: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400',
    negotiating: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400',
    won: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
    delivered: 'bg-teal-100 text-teal-700 dark:bg-teal-900/30 dark:text-teal-400',
    lost: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
  };
  return colors[status] || colors.lead;
}

function getScoreColor(score: number): string {
  if (score >= 80) return 'bg-green-500';
  if (score >= 60) return 'bg-yellow-500';
  if (score >= 40) return 'bg-orange-500';
  return 'bg-red-500';
}

const stageColors: Record<OpportunityStatus, string> = {
  lead: 'bg-gray-400',
  qualified: 'bg-blue-500',
  proposal: 'bg-yellow-500',
  negotiating: 'bg-purple-500',
  won: 'bg-green-500',
  delivered: 'bg-teal-500',
  lost: 'bg-red-500',
};

const stageLabels: Record<OpportunityStatus, string> = {
  lead: 'Leads',
  qualified: 'Qualified',
  proposal: 'Proposal Sent',
  negotiating: 'Negotiating',
  won: 'Won',
  delivered: 'Delivered',
  lost: 'Lost',
};

// ==========================================================================
// Main Component
// ==========================================================================

export default function DashboardPage() {
  const { user } = useAuth();
  const { data: stats, isLoading: statsLoading } = usePipelineStats();

  // Calculate metrics
  const totalPipeline = stats?.weighted_pipeline_value || 0;
  const conversionRate = stats?.conversion_rate ? (Number(stats.conversion_rate) * 100).toFixed(1) : '0';
  const avgDealSize = stats?.avg_deal_size || 0;
  const totalOpportunities = stats?.total_opportunities || 0;

  return (
    <div className="space-y-6" data-testid="dashboard-page">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold">
          Welcome back{user?.name ? `, ${user.name.split(' ')[0]}` : ''}
        </h1>
        <p className="text-gray-500 mt-1">
          Here's what's happening with your pipeline
        </p>
      </div>

      {/* Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          title="Pipeline Value"
          value={`${Number(totalPipeline).toLocaleString()}`}
          icon={<DollarSign className="text-green-600" size={20} />}
          loading={statsLoading}
        />
        <MetricCard
          title="Conversion Rate"
          value={`${conversionRate}%`}
          icon={<Target className="text-blue-600" size={20} />}
          loading={statsLoading}
        />
        <MetricCard
          title="Avg. Deal Size"
          value={`${Number(avgDealSize).toLocaleString()}`}
          icon={<TrendingUp className="text-purple-600" size={20} />}
          loading={statsLoading}
        />
        <MetricCard
          title="Total Opportunities"
          value={totalOpportunities}
          icon={<Briefcase className="text-orange-600" size={20} />}
          loading={statsLoading}
        />
      </div>

      {/* Two Column Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Pipeline Stages */}
        <div className="rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold">Pipeline Stages</h2>
            <Link to="/pipeline" className="text-sm text-blue-500 hover:underline">
              View all
            </Link>
          </div>

          {statsLoading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="animate-spin text-gray-400" size={24} />
            </div>
          ) : (
            <div className="space-y-3">
              {stats?.stages
                .filter(s => s.status !== 'lost' && s.status !== 'delivered')
                .map((stage) => (
                  <StageCard
                    key={stage.status}
                    status={stage.status}
                    label={stageLabels[stage.status]}
                    count={stage.count}
                    value={Number(stage.total_value)}
                    color={stageColors[stage.status]}
                  />
                ))}
            </div>
          )}
        </div>

        {/* Recent Opportunities */}
        <div className="rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold">Recent Opportunities</h2>
            <Link to="/pipeline" className="text-sm text-blue-500 hover:underline">
              Add new
            </Link>
          </div>
          <RecentOpportunities />
        </div>
      </div>

      {/* North Star Progress */}
      <div className="rounded-xl border border-gray-200 dark:border-gray-800 bg-gradient-to-r from-blue-500/10 to-purple-500/10 p-6">
        <h2 className="text-lg font-semibold mb-2">North Star Progress</h2>
        <p className="text-gray-600 dark:text-gray-400 text-sm mb-4">
          Goal: Build sustainable freelance income with NH + SW automation
        </p>
        <div className="flex items-center gap-4">
          <div className="flex-1 h-3 bg-gray-200 dark:bg-gray-700 rounded-full">
            <div
              className="h-full rounded-full bg-gradient-to-r from-blue-500 to-purple-500"
              style={{ width: '15%' }}
            />
          </div>
          <span className="text-sm font-medium">15%</span>
        </div>
        <p className="text-xs text-gray-500 mt-2">
          Based on pipeline value and conversion rate. Update financial tracker for accurate progress.
        </p>
      </div>
    </div>
  );
}
