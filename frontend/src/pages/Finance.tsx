import { useState, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from 'recharts';
import {
  DollarSign,
  TrendingUp,
  CreditCard,
  Wallet,
  ArrowUpRight,
  ArrowDownRight,
  Calendar,
  Plus,
  Target,
  X,
  Star,
} from 'lucide-react';
import * as api from '../api/client';
import type {
  FinancialDashboard,
  FinancialRecordCreate,
  FinancialGoalCreate,
  FinancialRecordType,
  GoalProgress,
} from '../types';

const EXPENSE_CATEGORIES = [
  'API Costs',
  'Tools & Software',
  'Marketing',
  'Infrastructure',
  'Freelancers',
  'Other',
];

const INCOME_SOURCES = [
  'Upwork',
  'Direct Client',
  'Referral',
  'Contract',
  'Other',
];

const COLORS = ['#22d3ee', '#a855f7', '#f97316', '#22c55e', '#3b82f6', '#64748b'];

interface MetricCardProps {
  title: string;
  value: string;
  subtitle?: string;
  trend?: 'up' | 'down' | 'neutral';
  trendValue?: string;
  icon: React.ReactNode;
  color: string;
}

function MetricCard({ title, value, subtitle, trend, trendValue, icon, color }: MetricCardProps) {
  return (
    <div className="bg-gray-800/50 border border-gray-700/50 rounded-xl p-5">
      <div className="flex items-start justify-between mb-3">
        <div className={`p-2 rounded-lg ${color}`}>
          {icon}
        </div>
        {trend && trendValue && (
          <div className={`flex items-center gap-1 text-xs font-medium ${
            trend === 'up' ? 'text-green-400' : trend === 'down' ? 'text-red-400' : 'text-gray-400'
          }`}>
            {trend === 'up' ? <ArrowUpRight className="w-3 h-3" /> : <ArrowDownRight className="w-3 h-3" />}
            {trendValue}
          </div>
        )}
      </div>
      <p className="text-xs text-gray-400 mb-1">{title}</p>
      <p className="text-2xl font-bold text-white">{value}</p>
      {subtitle && <p className="text-xs text-gray-500 mt-1">{subtitle}</p>}
    </div>
  );
}

function NorthStarProgress({ goal }: { goal: GoalProgress }) {
  const progressWidth = Math.min(goal.progress_percent, 100);

  return (
    <div className="bg-gradient-to-r from-purple-900/30 to-cyan-900/30 border border-purple-500/30 rounded-xl p-5">
      <div className="flex items-center gap-2 mb-3">
        <Star className="w-5 h-5 text-yellow-400" />
        <h3 className="text-sm font-semibold text-white">North Star Goal</h3>
      </div>
      <p className="text-lg font-bold text-white mb-2">{goal.name}</p>
      <div className="flex items-center justify-between text-sm mb-2">
        <span className="text-gray-400">
          {goal.currency} {goal.current_amount.toLocaleString()} / {goal.currency} {goal.target_amount.toLocaleString()}
        </span>
        <span className="text-cyan-400 font-medium">{goal.progress_percent.toFixed(1)}%</span>
      </div>
      <div className="h-3 bg-gray-700 rounded-full overflow-hidden">
        <div
          className="h-full bg-gradient-to-r from-purple-500 to-cyan-500 rounded-full transition-all duration-500"
          style={{ width: `${progressWidth}%` }}
        />
      </div>
      {goal.days_remaining !== null && (
        <p className="text-xs text-gray-500 mt-2">
          {goal.days_remaining} days remaining
        </p>
      )}
    </div>
  );
}

interface AddRecordModalProps {
  isOpen: boolean;
  onClose: () => void;
  type: FinancialRecordType;
  onSubmit: (data: FinancialRecordCreate) => void;
  isLoading: boolean;
}

function AddRecordModal({ isOpen, onClose, type, onSubmit, isLoading }: AddRecordModalProps) {
  const [amount, setAmount] = useState('');
  const [category, setCategory] = useState('');
  const [source, setSource] = useState('');
  const [description, setDescription] = useState('');
  const [recordDate, setRecordDate] = useState(new Date().toISOString().split('T')[0]);

  const categories = type === 'income' ? INCOME_SOURCES : EXPENSE_CATEGORIES;
  const title = type === 'income' ? 'Add Income' : 'Add Expense';

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit({
      record_type: type,
      amount: parseFloat(amount),
      category,
      source: type === 'income' ? source : category,
      description: description || undefined,
      record_date: new Date(recordDate).toISOString(),
    });
    // Reset form
    setAmount('');
    setCategory('');
    setSource('');
    setDescription('');
    setRecordDate(new Date().toISOString().split('T')[0]);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-gray-800 border border-gray-700 rounded-xl p-6 w-full max-w-md">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-white">{title}</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-white">
            <X className="w-5 h-5" />
          </button>
        </div>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm text-gray-400 mb-1">Amount (EUR)</label>
            <input
              type="number"
              step="0.01"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-white"
              required
            />
          </div>
          <div>
            <label className="block text-sm text-gray-400 mb-1">Category</label>
            <select
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-white"
              required
            >
              <option value="">Select category</option>
              {categories.map((cat) => (
                <option key={cat} value={cat}>{cat}</option>
              ))}
            </select>
          </div>
          {type === 'income' && (
            <div>
              <label className="block text-sm text-gray-400 mb-1">Source</label>
              <input
                type="text"
                value={source}
                onChange={(e) => setSource(e.target.value)}
                placeholder="Client name or project"
                className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-white"
                required
              />
            </div>
          )}
          <div>
            <label className="block text-sm text-gray-400 mb-1">Date</label>
            <input
              type="date"
              value={recordDate}
              onChange={(e) => setRecordDate(e.target.value)}
              className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-white"
              required
            />
          </div>
          <div>
            <label className="block text-sm text-gray-400 mb-1">Description (optional)</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-white"
              rows={2}
            />
          </div>
          <button
            type="submit"
            disabled={isLoading}
            className="w-full bg-cyan-600 hover:bg-cyan-500 text-white font-medium py-2 rounded-lg transition-colors disabled:opacity-50"
          >
            {isLoading ? 'Adding...' : `Add ${type === 'income' ? 'Income' : 'Expense'}`}
          </button>
        </form>
      </div>
    </div>
  );
}

interface AddGoalModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (data: FinancialGoalCreate) => void;
  isLoading: boolean;
}

function AddGoalModal({ isOpen, onClose, onSubmit, isLoading }: AddGoalModalProps) {
  const [name, setName] = useState('');
  const [targetAmount, setTargetAmount] = useState('');
  const [currentAmount, setCurrentAmount] = useState('0');
  const [deadline, setDeadline] = useState('');
  const [isNorthStar, setIsNorthStar] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit({
      name,
      target_amount: parseFloat(targetAmount),
      current_amount: parseFloat(currentAmount),
      deadline: deadline ? new Date(deadline).toISOString() : undefined,
      is_north_star: isNorthStar,
    });
    // Reset form
    setName('');
    setTargetAmount('');
    setCurrentAmount('0');
    setDeadline('');
    setIsNorthStar(false);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-gray-800 border border-gray-700 rounded-xl p-6 w-full max-w-md">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-white">Add Financial Goal</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-white">
            <X className="w-5 h-5" />
          </button>
        </div>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm text-gray-400 mb-1">Goal Name</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g., Q1 Revenue Target"
              className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-white"
              required
            />
          </div>
          <div>
            <label className="block text-sm text-gray-400 mb-1">Target Amount (EUR)</label>
            <input
              type="number"
              step="0.01"
              value={targetAmount}
              onChange={(e) => setTargetAmount(e.target.value)}
              className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-white"
              required
            />
          </div>
          <div>
            <label className="block text-sm text-gray-400 mb-1">Current Progress (EUR)</label>
            <input
              type="number"
              step="0.01"
              value={currentAmount}
              onChange={(e) => setCurrentAmount(e.target.value)}
              className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-white"
            />
          </div>
          <div>
            <label className="block text-sm text-gray-400 mb-1">Deadline (optional)</label>
            <input
              type="date"
              value={deadline}
              onChange={(e) => setDeadline(e.target.value)}
              className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-white"
            />
          </div>
          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="northStar"
              checked={isNorthStar}
              onChange={(e) => setIsNorthStar(e.target.checked)}
              className="w-4 h-4 rounded border-gray-600 bg-gray-700"
            />
            <label htmlFor="northStar" className="text-sm text-gray-400">
              Set as North Star Goal
            </label>
          </div>
          <button
            type="submit"
            disabled={isLoading}
            className="w-full bg-purple-600 hover:bg-purple-500 text-white font-medium py-2 rounded-lg transition-colors disabled:opacity-50"
          >
            {isLoading ? 'Creating...' : 'Create Goal'}
          </button>
        </form>
      </div>
    </div>
  );
}

export default function Finance() {
  const queryClient = useQueryClient();
  const [incomeModalOpen, setIncomeModalOpen] = useState(false);
  const [expenseModalOpen, setExpenseModalOpen] = useState(false);
  const [goalModalOpen, setGoalModalOpen] = useState(false);

  const { data: dashboard, isLoading } = useQuery<FinancialDashboard>({
    queryKey: ['financeDashboard'],
    queryFn: api.getFinanceDashboard,
    retry: 1,
  });

  const createRecordMutation = useMutation({
    mutationFn: api.createFinancialRecord,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['financeDashboard'] });
      setIncomeModalOpen(false);
      setExpenseModalOpen(false);
    },
  });

  const createGoalMutation = useMutation({
    mutationFn: api.createFinancialGoal,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['financeDashboard'] });
      setGoalModalOpen(false);
    },
  });

  // Transform data for charts
  const incomeBySourceData = useMemo(() => {
    if (!dashboard?.income_by_source) return [];
    return Object.entries(dashboard.income_by_source).map(([name, value], index) => ({
      name,
      value,
      color: COLORS[index % COLORS.length],
    }));
  }, [dashboard?.income_by_source]);

  const expensesByCategoryData = useMemo(() => {
    if (!dashboard?.expenses_by_category) return [];
    return Object.entries(dashboard.expenses_by_category).map(([name, value], index) => ({
      name,
      value,
      color: COLORS[index % COLORS.length],
    }));
  }, [dashboard?.expenses_by_category]);

  const stats = dashboard?.quick_stats;
  const northStar = dashboard?.north_star;

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 to-slate-950 p-6">
        <div className="animate-pulse space-y-6">
          <div className="h-20 bg-gray-800/50 rounded-xl" />
          <div className="grid grid-cols-4 gap-4">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="h-32 bg-gray-800/50 rounded-xl" />
            ))}
          </div>
          <div className="h-64 bg-gray-800/50 rounded-xl" />
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 to-slate-950">
      {/* Header */}
      <header className="bg-slate-900/80 border-b border-slate-700/50 backdrop-blur-sm sticky top-0 z-40">
        <div className="max-w-full mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="bg-gradient-to-br from-green-500 to-emerald-600 p-2 rounded-lg">
                <DollarSign className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className="text-xl font-bold text-white">Financial Command</h1>
                <p className="text-sm text-gray-400">
                  {new Date().toLocaleDateString('en-US', { month: 'long', year: 'numeric' })}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setIncomeModalOpen(true)}
                className="flex items-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-500 text-white rounded-lg text-sm transition-colors"
              >
                <Plus className="w-4 h-4" />
                Income
              </button>
              <button
                onClick={() => setExpenseModalOpen(true)}
                className="flex items-center gap-2 px-4 py-2 bg-orange-600 hover:bg-orange-500 text-white rounded-lg text-sm transition-colors"
              >
                <Plus className="w-4 h-4" />
                Expense
              </button>
              <button
                onClick={() => setGoalModalOpen(true)}
                className="flex items-center gap-2 px-4 py-2 bg-purple-600 hover:bg-purple-500 text-white rounded-lg text-sm transition-colors"
              >
                <Target className="w-4 h-4" />
                Goal
              </button>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-full mx-auto px-6 py-6">
        {/* North Star Goal */}
        {northStar && (
          <div className="mb-6">
            <NorthStarProgress goal={northStar} />
          </div>
        )}

        {/* Top Metrics */}
        <div className="grid grid-cols-4 gap-4 mb-6">
          <MetricCard
            title="MTD Income"
            value={`€${(stats?.mtd_income ?? 0).toLocaleString()}`}
            trend={stats?.income_change_percent && stats.income_change_percent > 0 ? 'up' : stats?.income_change_percent && stats.income_change_percent < 0 ? 'down' : undefined}
            trendValue={stats?.income_change_percent ? `${stats.income_change_percent > 0 ? '+' : ''}${stats.income_change_percent.toFixed(1)}%` : undefined}
            icon={<TrendingUp className="w-5 h-5 text-white" />}
            color="bg-green-500/20"
          />
          <MetricCard
            title="MTD Net"
            value={`€${(stats?.mtd_net ?? 0).toLocaleString()}`}
            subtitle={stats?.mtd_income ? `${((stats.mtd_net / stats.mtd_income) * 100).toFixed(0)}% margin` : undefined}
            icon={<Wallet className="w-5 h-5 text-white" />}
            color="bg-cyan-500/20"
          />
          <MetricCard
            title="MTD Expenses"
            value={`€${(stats?.mtd_expenses ?? 0).toLocaleString()}`}
            trend={stats?.expense_change_percent && stats.expense_change_percent < 0 ? 'up' : stats?.expense_change_percent && stats.expense_change_percent > 0 ? 'down' : undefined}
            trendValue={stats?.expense_change_percent ? `${stats.expense_change_percent > 0 ? '+' : ''}${stats.expense_change_percent.toFixed(1)}%` : undefined}
            icon={<CreditCard className="w-5 h-5 text-white" />}
            color="bg-orange-500/20"
          />
          <MetricCard
            title="YTD Net"
            value={`€${(stats?.ytd_net ?? 0).toLocaleString()}`}
            subtitle={`Income: €${(stats?.ytd_income ?? 0).toLocaleString()}`}
            icon={<Calendar className="w-5 h-5 text-white" />}
            color="bg-purple-500/20"
          />
        </div>

        {/* Charts Row */}
        <div className="grid grid-cols-3 gap-6 mb-6">
          {/* Income by Source */}
          <div className="bg-gray-800/50 border border-gray-700/50 rounded-xl p-5">
            <h3 className="text-sm font-semibold text-white mb-4">Income by Source</h3>
            {incomeBySourceData.length > 0 ? (
              <>
                <div className="h-48">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={incomeBySourceData}
                        cx="50%"
                        cy="50%"
                        innerRadius={40}
                        outerRadius={70}
                        paddingAngle={2}
                        dataKey="value"
                      >
                        {incomeBySourceData.map((entry, index) => (
                          <Cell key={index} fill={entry.color} />
                        ))}
                      </Pie>
                      <Tooltip
                        contentStyle={{
                          backgroundColor: '#1f2937',
                          border: '1px solid #374151',
                          borderRadius: '8px',
                        }}
                        formatter={(value) => [`€${value ?? 0}`, '']}
                      />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
                <div className="space-y-2 mt-4">
                  {incomeBySourceData.map((item) => (
                    <div key={item.name} className="flex items-center justify-between text-xs">
                      <div className="flex items-center gap-2">
                        <div className="w-2 h-2 rounded-full" style={{ backgroundColor: item.color }} />
                        <span className="text-gray-400">{item.name}</span>
                      </div>
                      <span className="text-white font-medium">€{item.value.toLocaleString()}</span>
                    </div>
                  ))}
                </div>
              </>
            ) : (
              <div className="h-48 flex items-center justify-center text-gray-500">
                No income data yet
              </div>
            )}
          </div>

          {/* Expenses by Category */}
          <div className="bg-gray-800/50 border border-gray-700/50 rounded-xl p-5">
            <h3 className="text-sm font-semibold text-white mb-4">Expenses by Category</h3>
            {expensesByCategoryData.length > 0 ? (
              <>
                <div className="space-y-3">
                  {expensesByCategoryData.map((expense) => {
                    const total = expensesByCategoryData.reduce((sum, e) => sum + e.value, 0);
                    const percentage = total > 0 ? Math.round((expense.value / total) * 100) : 0;
                    return (
                      <div key={expense.name}>
                        <div className="flex items-center justify-between text-xs mb-1">
                          <span className="text-gray-400">{expense.name}</span>
                          <span className="text-white">€{expense.value} ({percentage}%)</span>
                        </div>
                        <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
                          <div
                            className="h-full rounded-full transition-all duration-500"
                            style={{
                              width: `${percentage}%`,
                              backgroundColor: expense.color,
                            }}
                          />
                        </div>
                      </div>
                    );
                  })}
                </div>
                <div className="mt-4 pt-4 border-t border-gray-700/50">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-gray-400">Total Expenses</span>
                    <span className="text-white font-bold">€{(stats?.mtd_expenses ?? 0).toLocaleString()}</span>
                  </div>
                </div>
              </>
            ) : (
              <div className="h-48 flex items-center justify-center text-gray-500">
                No expense data yet
              </div>
            )}
          </div>

          {/* Goals Progress */}
          <div className="bg-gray-800/50 border border-gray-700/50 rounded-xl p-5">
            <h3 className="text-sm font-semibold text-white mb-4">Goals</h3>
            {dashboard?.goals && dashboard.goals.length > 0 ? (
              <div className="space-y-4">
                {dashboard.goals.slice(0, 5).map((goal) => (
                  <div key={goal.goal_id} className="space-y-1">
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-gray-400 flex items-center gap-1">
                        {goal.is_north_star && <Star className="w-3 h-3 text-yellow-400" />}
                        {goal.name}
                      </span>
                      <span className="text-white">{goal.progress_percent.toFixed(0)}%</span>
                    </div>
                    <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all duration-500 ${
                          goal.is_north_star
                            ? 'bg-gradient-to-r from-purple-500 to-cyan-500'
                            : 'bg-cyan-500'
                        }`}
                        style={{ width: `${Math.min(goal.progress_percent, 100)}%` }}
                      />
                    </div>
                    <div className="flex items-center justify-between text-xs text-gray-500">
                      <span>€{goal.current_amount.toLocaleString()}</span>
                      <span>€{goal.target_amount.toLocaleString()}</span>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="h-48 flex flex-col items-center justify-center text-gray-500">
                <Target className="w-8 h-8 mb-2 opacity-50" />
                <p>No goals set</p>
                <button
                  onClick={() => setGoalModalOpen(true)}
                  className="mt-2 text-sm text-cyan-400 hover:text-cyan-300"
                >
                  Create your first goal
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Recent Transactions */}
        <div className="grid grid-cols-2 gap-6">
          {/* Recent Income */}
          <div className="bg-gray-800/50 border border-gray-700/50 rounded-xl p-5">
            <h3 className="text-sm font-semibold text-white mb-4">Recent Income</h3>
            {dashboard?.recent_income && dashboard.recent_income.length > 0 ? (
              <div className="space-y-3">
                {dashboard.recent_income.slice(0, 5).map((record) => (
                  <div key={record.id} className="flex items-center justify-between p-2 bg-green-500/10 border border-green-500/20 rounded-lg">
                    <div>
                      <p className="text-sm text-white">{record.source}</p>
                      <p className="text-xs text-gray-500">{record.category}</p>
                    </div>
                    <div className="text-right">
                      <p className="text-sm font-medium text-green-400">+€{record.amount.toLocaleString()}</p>
                      <p className="text-xs text-gray-500">
                        {new Date(record.record_date).toLocaleDateString()}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center text-gray-500 py-8">
                No income recorded yet
              </div>
            )}
          </div>

          {/* Recent Expenses */}
          <div className="bg-gray-800/50 border border-gray-700/50 rounded-xl p-5">
            <h3 className="text-sm font-semibold text-white mb-4">Recent Expenses</h3>
            {dashboard?.recent_expenses && dashboard.recent_expenses.length > 0 ? (
              <div className="space-y-3">
                {dashboard.recent_expenses.slice(0, 5).map((record) => (
                  <div key={record.id} className="flex items-center justify-between p-2 bg-orange-500/10 border border-orange-500/20 rounded-lg">
                    <div>
                      <p className="text-sm text-white">{record.category}</p>
                      <p className="text-xs text-gray-500">{record.description || 'No description'}</p>
                    </div>
                    <div className="text-right">
                      <p className="text-sm font-medium text-orange-400">-€{record.amount.toLocaleString()}</p>
                      <p className="text-xs text-gray-500">
                        {new Date(record.record_date).toLocaleDateString()}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center text-gray-500 py-8">
                No expenses recorded yet
              </div>
            )}
          </div>
        </div>
      </main>

      {/* Modals */}
      <AddRecordModal
        isOpen={incomeModalOpen}
        onClose={() => setIncomeModalOpen(false)}
        type="income"
        onSubmit={(data) => createRecordMutation.mutate(data)}
        isLoading={createRecordMutation.isPending}
      />
      <AddRecordModal
        isOpen={expenseModalOpen}
        onClose={() => setExpenseModalOpen(false)}
        type="expense"
        onSubmit={(data) => createRecordMutation.mutate(data)}
        isLoading={createRecordMutation.isPending}
      />
      <AddGoalModal
        isOpen={goalModalOpen}
        onClose={() => setGoalModalOpen(false)}
        onSubmit={(data) => createGoalMutation.mutate(data)}
        isLoading={createGoalMutation.isPending}
      />
    </div>
  );
}
