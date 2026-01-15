// Cost Analytics Panel Component (v50.0)
// Displays cost tracking and trends

import { useState } from 'react';
import { DollarSign, TrendingUp, TrendingDown, Calendar, Clock, ChevronDown, ChevronRight, PieChart, BarChart3 } from 'lucide-react';
import clsx from 'clsx';

interface CostAnalyticsPanelProps {
  costToday: number;
  costThisWeek: number;
  costThisMonth: number;
  totalCost24h?: number;
}

export function CostAnalyticsPanel({
  costToday,
  costThisWeek,
  costThisMonth,
}: CostAnalyticsPanelProps) {
  const [expanded, setExpanded] = useState(true);

  // Calculate trends (mock - would normally come from API)
  const dailyAvg = costThisWeek > 0 ? costThisWeek / 7 : 0;
  const weeklyAvg = costThisMonth > 0 ? costThisMonth / 4 : 0;

  // Trend indicators
  const todayVsAvg = dailyAvg > 0 ? ((costToday - dailyAvg) / dailyAvg) * 100 : 0;
  const weekVsAvg = weeklyAvg > 0 ? ((costThisWeek - weeklyAvg) / weeklyAvg) * 100 : 0;

  // Format currency with proper precision
  const formatCurrency = (value: number): string => {
    if (value >= 1) {
      return `$${value.toFixed(2)}`;
    } else if (value >= 0.01) {
      return `$${value.toFixed(4)}`;
    } else {
      return `$${value.toFixed(6)}`;
    }
  };

  // Get trend color
  const getTrendColor = (trend: number): string => {
    if (Math.abs(trend) < 5) return 'text-zinc-600';
    return trend > 0 ? 'text-red-600' : 'text-green-600';
  };

  // Get trend icon
  const TrendIcon = ({ trend }: { trend: number }) => {
    if (Math.abs(trend) < 5) return null;
    return trend > 0
      ? <TrendingUp className="w-4 h-4" />
      : <TrendingDown className="w-4 h-4" />;
  };

  return (
    <div className="bg-white/80 backdrop-blur rounded-2xl shadow-lg border border-zinc-200 p-6">
      {/* Header */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between mb-4"
      >
        <div className="flex items-center gap-3">
          <div className="p-2 bg-emerald-100 rounded-xl">
            <DollarSign className="w-5 h-5 text-emerald-600" />
          </div>
          <div className="text-left">
            <h2 className="text-lg font-bold text-zinc-900">Cost Analytics</h2>
            <p className="text-sm text-zinc-600">
              API usage and cost tracking
            </p>
          </div>
        </div>
        {expanded ? (
          <ChevronDown className="w-5 h-5 text-zinc-400" />
        ) : (
          <ChevronRight className="w-5 h-5 text-zinc-400" />
        )}
      </button>

      {expanded && (
        <>
          {/* Main Cost Cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
            {/* Today */}
            <div className="p-5 bg-gradient-to-br from-emerald-50 to-teal-50 rounded-xl border border-emerald-200 relative overflow-hidden">
              <div className="absolute top-2 right-2">
                <Clock className="w-6 h-6 text-emerald-200" />
              </div>
              <p className="text-xs text-emerald-600 font-medium mb-1">Today</p>
              <p className="text-3xl font-bold text-emerald-900">{formatCurrency(costToday)}</p>
              {dailyAvg > 0 && Math.abs(todayVsAvg) >= 5 && (
                <div className={clsx("flex items-center gap-1 mt-2 text-xs font-medium", getTrendColor(todayVsAvg))}>
                  <TrendIcon trend={todayVsAvg} />
                  <span>{Math.abs(todayVsAvg).toFixed(0)}% vs daily avg</span>
                </div>
              )}
            </div>

            {/* This Week */}
            <div className="p-5 bg-gradient-to-br from-blue-50 to-indigo-50 rounded-xl border border-blue-200 relative overflow-hidden">
              <div className="absolute top-2 right-2">
                <Calendar className="w-6 h-6 text-blue-200" />
              </div>
              <p className="text-xs text-blue-600 font-medium mb-1">This Week</p>
              <p className="text-3xl font-bold text-blue-900">{formatCurrency(costThisWeek)}</p>
              {weeklyAvg > 0 && Math.abs(weekVsAvg) >= 5 && (
                <div className={clsx("flex items-center gap-1 mt-2 text-xs font-medium", getTrendColor(weekVsAvg))}>
                  <TrendIcon trend={weekVsAvg} />
                  <span>{Math.abs(weekVsAvg).toFixed(0)}% vs weekly avg</span>
                </div>
              )}
            </div>

            {/* This Month */}
            <div className="p-5 bg-gradient-to-br from-purple-50 to-violet-50 rounded-xl border border-purple-200 relative overflow-hidden">
              <div className="absolute top-2 right-2">
                <BarChart3 className="w-6 h-6 text-purple-200" />
              </div>
              <p className="text-xs text-purple-600 font-medium mb-1">This Month</p>
              <p className="text-3xl font-bold text-purple-900">{formatCurrency(costThisMonth)}</p>
              <p className="text-xs text-purple-600 mt-2">
                Avg/day: {formatCurrency(costThisMonth / 30)}
              </p>
            </div>
          </div>

          {/* Cost Breakdown Visual */}
          <div className="bg-zinc-50 rounded-xl p-4">
            <h3 className="text-sm font-bold text-zinc-900 mb-3 flex items-center gap-2">
              <PieChart className="w-4 h-4 text-zinc-600" />
              Period Breakdown
            </h3>

            {/* Visual Bar Comparison */}
            <div className="space-y-3">
              {/* Today */}
              <div className="flex items-center gap-3">
                <span className="text-xs text-zinc-600 w-20">Today</span>
                <div className="flex-1 bg-zinc-200 rounded-full h-4 overflow-hidden">
                  <div
                    className="h-4 bg-gradient-to-r from-emerald-400 to-emerald-600 rounded-full transition-all duration-500"
                    style={{ width: `${Math.min((costToday / (costThisMonth || 1)) * 100, 100)}%` }}
                  />
                </div>
                <span className="text-xs font-mono text-zinc-900 w-20 text-right">{formatCurrency(costToday)}</span>
              </div>

              {/* This Week */}
              <div className="flex items-center gap-3">
                <span className="text-xs text-zinc-600 w-20">This Week</span>
                <div className="flex-1 bg-zinc-200 rounded-full h-4 overflow-hidden">
                  <div
                    className="h-4 bg-gradient-to-r from-blue-400 to-blue-600 rounded-full transition-all duration-500"
                    style={{ width: `${Math.min((costThisWeek / (costThisMonth || 1)) * 100, 100)}%` }}
                  />
                </div>
                <span className="text-xs font-mono text-zinc-900 w-20 text-right">{formatCurrency(costThisWeek)}</span>
              </div>

              {/* This Month */}
              <div className="flex items-center gap-3">
                <span className="text-xs text-zinc-600 w-20">This Month</span>
                <div className="flex-1 bg-zinc-200 rounded-full h-4 overflow-hidden">
                  <div
                    className="h-4 bg-gradient-to-r from-purple-400 to-purple-600 rounded-full transition-all duration-500"
                    style={{ width: '100%' }}
                  />
                </div>
                <span className="text-xs font-mono text-zinc-900 w-20 text-right">{formatCurrency(costThisMonth)}</span>
              </div>
            </div>
          </div>

          {/* Quick Stats */}
          <div className="grid grid-cols-2 gap-4 mt-4">
            <div className="p-3 bg-zinc-50 rounded-lg">
              <p className="text-xs text-zinc-500">Daily Average (Week)</p>
              <p className="text-lg font-bold text-zinc-900">{formatCurrency(dailyAvg)}</p>
            </div>
            <div className="p-3 bg-zinc-50 rounded-lg">
              <p className="text-xs text-zinc-500">Weekly Average (Month)</p>
              <p className="text-lg font-bold text-zinc-900">{formatCurrency(weeklyAvg)}</p>
            </div>
          </div>

          {/* Cost Efficiency Tips */}
          <div className="mt-4 p-4 bg-amber-50 border border-amber-200 rounded-xl">
            <h4 className="text-sm font-bold text-amber-900 mb-2 flex items-center gap-2">
              <TrendingDown className="w-4 h-4" />
              Cost Optimization Tips
            </h4>
            <ul className="text-xs text-amber-800 space-y-1">
              <li className="flex items-start gap-2">
                <span className="text-amber-600">1.</span>
                Use loop detection to prevent wasted iterations
              </li>
              <li className="flex items-start gap-2">
                <span className="text-amber-600">2.</span>
                Enable smart test skipping for faster execution
              </li>
              <li className="flex items-start gap-2">
                <span className="text-amber-600">3.</span>
                Break large tasks into parallel subtasks
              </li>
            </ul>
          </div>
        </>
      )}
    </div>
  );
}
