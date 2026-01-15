/**
 * NH Mission Control - Pipeline Page
 * ====================================
 *
 * Kanban-style pipeline management with drag and drop.
 *
 * EPOCH 3 - Pipeline Module (ACTIVE)
 */

import { useState } from 'react';
import {
  Plus,
  Search,
  Filter,
  Loader2,
  AlertCircle,
  ExternalLink,
  MoreVertical,
  Sparkles,
  FileText,
  Clock,
  Trash2,
  ChevronRight,
  X,
} from 'lucide-react';
import {
  useOpportunities,
  useCreateOpportunity,
  useMoveOpportunity,
  useDeleteOpportunity,
  useAnalyzeOpportunity,
} from '../hooks/usePipeline';
import type {
  Opportunity,
  OpportunityCreate,
  OpportunityStatus,
  OpportunitySource,
} from '../types';

// ==========================================================================
// Types & Constants
// ==========================================================================

const STATUSES: OpportunityStatus[] = [
  'lead',
  'qualified',
  'proposal',
  'negotiating',
  'won',
];

const STATUS_CONFIG: Record<OpportunityStatus, { label: string; color: string; bgColor: string }> = {
  lead: { label: 'Leads', color: 'text-gray-600', bgColor: 'bg-gray-100 dark:bg-gray-800' },
  qualified: { label: 'Qualified', color: 'text-blue-600', bgColor: 'bg-blue-50 dark:bg-blue-900/20' },
  proposal: { label: 'Proposal', color: 'text-yellow-600', bgColor: 'bg-yellow-50 dark:bg-yellow-900/20' },
  negotiating: { label: 'Negotiating', color: 'text-purple-600', bgColor: 'bg-purple-50 dark:bg-purple-900/20' },
  won: { label: 'Won', color: 'text-green-600', bgColor: 'bg-green-50 dark:bg-green-900/20' },
  delivered: { label: 'Delivered', color: 'text-teal-600', bgColor: 'bg-teal-50 dark:bg-teal-900/20' },
  lost: { label: 'Lost', color: 'text-red-600', bgColor: 'bg-red-50 dark:bg-red-900/20' },
};

// ==========================================================================
// Add Opportunity Modal
// ==========================================================================

interface AddModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (data: OpportunityCreate) => void;
  isLoading: boolean;
}

function AddOpportunityModal({ isOpen, onClose, onSubmit, isLoading }: AddModalProps) {
  const [formData, setFormData] = useState<OpportunityCreate>({
    title: '',
    description: '',
    source: 'upwork' as OpportunitySource,
    value: undefined,
    currency: 'EUR',
    client_name: '',
    external_url: '',
    tech_stack: [],
  });
  const [techInput, setTechInput] = useState('');

  if (!isOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit(formData);
  };

  const addTech = () => {
    if (techInput.trim()) {
      setFormData(prev => ({
        ...prev,
        tech_stack: [...(prev.tech_stack || []), techInput.trim()],
      }));
      setTechInput('');
    }
  };

  const removeTech = (index: number) => {
    setFormData(prev => ({
      ...prev,
      tech_stack: prev.tech_stack?.filter((_, i) => i !== index),
    }));
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white dark:bg-gray-900 rounded-xl w-full max-w-lg mx-4 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between p-4 border-b dark:border-gray-800">
          <h2 className="text-lg font-semibold">Add Opportunity</h2>
          <button onClick={onClose} className="p-1 hover:bg-gray-100 dark:hover:bg-gray-800 rounded">
            <X size={20} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-4 space-y-4">
          {/* Title */}
          <div>
            <label className="block text-sm font-medium mb-1">Title *</label>
            <input
              type="text"
              required
              value={formData.title}
              onChange={(e) => setFormData(prev => ({ ...prev, title: e.target.value }))}
              className="w-full px-3 py-2 border rounded-lg dark:bg-gray-800 dark:border-gray-700"
              placeholder="e.g., Python API for E-commerce"
            />
          </div>

          {/* Source */}
          <div>
            <label className="block text-sm font-medium mb-1">Source</label>
            <select
              value={formData.source}
              onChange={(e) => setFormData(prev => ({ ...prev, source: e.target.value as OpportunitySource }))}
              className="w-full px-3 py-2 border rounded-lg dark:bg-gray-800 dark:border-gray-700"
            >
              <option value="upwork">Upwork</option>
              <option value="useme">Useme</option>
              <option value="direct">Direct</option>
              <option value="referral">Referral</option>
              <option value="other">Other</option>
            </select>
          </div>

          {/* Value & Currency */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1">Value</label>
              <input
                type="number"
                value={formData.value || ''}
                onChange={(e) => setFormData(prev => ({ ...prev, value: e.target.value ? Number(e.target.value) : undefined }))}
                className="w-full px-3 py-2 border rounded-lg dark:bg-gray-800 dark:border-gray-700"
                placeholder="5000"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Currency</label>
              <select
                value={formData.currency}
                onChange={(e) => setFormData(prev => ({ ...prev, currency: e.target.value }))}
                className="w-full px-3 py-2 border rounded-lg dark:bg-gray-800 dark:border-gray-700"
              >
                <option value="EUR">EUR</option>
                <option value="USD">USD</option>
                <option value="PLN">PLN</option>
                <option value="GBP">GBP</option>
              </select>
            </div>
          </div>

          {/* Client Name */}
          <div>
            <label className="block text-sm font-medium mb-1">Client Name</label>
            <input
              type="text"
              value={formData.client_name || ''}
              onChange={(e) => setFormData(prev => ({ ...prev, client_name: e.target.value }))}
              className="w-full px-3 py-2 border rounded-lg dark:bg-gray-800 dark:border-gray-700"
              placeholder="Client or company name"
            />
          </div>

          {/* External URL */}
          <div>
            <label className="block text-sm font-medium mb-1">Job URL</label>
            <input
              type="url"
              value={formData.external_url || ''}
              onChange={(e) => setFormData(prev => ({ ...prev, external_url: e.target.value }))}
              className="w-full px-3 py-2 border rounded-lg dark:bg-gray-800 dark:border-gray-700"
              placeholder="https://upwork.com/jobs/..."
            />
          </div>

          {/* Tech Stack */}
          <div>
            <label className="block text-sm font-medium mb-1">Tech Stack</label>
            <div className="flex gap-2">
              <input
                type="text"
                value={techInput}
                onChange={(e) => setTechInput(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && (e.preventDefault(), addTech())}
                className="flex-1 px-3 py-2 border rounded-lg dark:bg-gray-800 dark:border-gray-700"
                placeholder="Python, FastAPI, etc."
              />
              <button
                type="button"
                onClick={addTech}
                className="px-3 py-2 bg-gray-100 dark:bg-gray-800 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-700"
              >
                Add
              </button>
            </div>
            {formData.tech_stack && formData.tech_stack.length > 0 && (
              <div className="flex flex-wrap gap-2 mt-2">
                {formData.tech_stack.map((tech, i) => (
                  <span
                    key={i}
                    className="inline-flex items-center gap-1 px-2 py-1 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400 rounded text-sm"
                  >
                    {tech}
                    <button type="button" onClick={() => removeTech(i)}>
                      <X size={14} />
                    </button>
                  </span>
                ))}
              </div>
            )}
          </div>

          {/* Description */}
          <div>
            <label className="block text-sm font-medium mb-1">Description</label>
            <textarea
              value={formData.description || ''}
              onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))}
              className="w-full px-3 py-2 border rounded-lg dark:bg-gray-800 dark:border-gray-700"
              rows={3}
              placeholder="Project details..."
            />
          </div>

          {/* Actions */}
          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-2 border rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isLoading || !formData.title}
              className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 flex items-center justify-center gap-2"
            >
              {isLoading && <Loader2 size={16} className="animate-spin" />}
              Add Opportunity
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ==========================================================================
// Opportunity Card
// ==========================================================================

interface OpportunityCardProps {
  opportunity: Opportunity;
  onMove: (id: string, status: OpportunityStatus) => void;
  onAnalyze: (id: string) => void;
  onDelete: (id: string) => void;
}

function OpportunityCard({ opportunity, onMove, onAnalyze, onDelete }: OpportunityCardProps) {
  const [menuOpen, setMenuOpen] = useState(false);

  const nextStatus = getNextStatus(opportunity.status);

  return (
    <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700 p-3 shadow-sm hover:shadow-md transition-shadow">
      {/* Header */}
      <div className="flex items-start justify-between gap-2">
        <h3 className="font-medium text-sm line-clamp-2">{opportunity.title}</h3>
        <div className="relative">
          <button
            onClick={() => setMenuOpen(!menuOpen)}
            className="p-1 hover:bg-gray-100 dark:hover:bg-gray-800 rounded"
          >
            <MoreVertical size={16} />
          </button>
          {menuOpen && (
            <>
              <div className="fixed inset-0" onClick={() => setMenuOpen(false)} />
              <div className="absolute right-0 top-full mt-1 w-40 bg-white dark:bg-gray-800 border dark:border-gray-700 rounded-lg shadow-lg z-10">
                <button
                  onClick={() => { onAnalyze(opportunity.id); setMenuOpen(false); }}
                  className="w-full px-3 py-2 text-left text-sm hover:bg-gray-50 dark:hover:bg-gray-700 flex items-center gap-2"
                >
                  <Sparkles size={14} />
                  Analyze
                </button>
                <button
                  onClick={() => { setMenuOpen(false); }}
                  className="w-full px-3 py-2 text-left text-sm hover:bg-gray-50 dark:hover:bg-gray-700 flex items-center gap-2"
                >
                  <FileText size={14} />
                  Proposal
                </button>
                <button
                  onClick={() => { setMenuOpen(false); }}
                  className="w-full px-3 py-2 text-left text-sm hover:bg-gray-50 dark:hover:bg-gray-700 flex items-center gap-2"
                >
                  <Clock size={14} />
                  Estimate
                </button>
                <hr className="dark:border-gray-700" />
                <button
                  onClick={() => { onDelete(opportunity.id); setMenuOpen(false); }}
                  className="w-full px-3 py-2 text-left text-sm hover:bg-gray-50 dark:hover:bg-gray-700 flex items-center gap-2 text-red-600"
                >
                  <Trash2 size={14} />
                  Delete
                </button>
              </div>
            </>
          )}
        </div>
      </div>

      {/* Client & Value */}
      <div className="mt-2 flex items-center justify-between text-sm text-gray-500">
        <span>{opportunity.client_name || 'Unknown'}</span>
        {opportunity.value && (
          <span className="font-medium text-gray-900 dark:text-gray-100">
            {Number(opportunity.value).toLocaleString()}
          </span>
        )}
      </div>

      {/* Tech Stack */}
      {opportunity.tech_stack && opportunity.tech_stack.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1">
          {opportunity.tech_stack.slice(0, 3).map((tech, i) => (
            <span
              key={i}
              className="px-1.5 py-0.5 bg-gray-100 dark:bg-gray-800 rounded text-xs"
            >
              {tech}
            </span>
          ))}
          {opportunity.tech_stack.length > 3 && (
            <span className="px-1.5 py-0.5 text-xs text-gray-500">
              +{opportunity.tech_stack.length - 3}
            </span>
          )}
        </div>
      )}

      {/* NH Score */}
      {opportunity.nh_score !== null && (
        <div className="mt-2 flex items-center gap-2">
          <div className="flex-1 h-1 bg-gray-200 dark:bg-gray-700 rounded-full">
            <div
              className={`h-full rounded-full ${getScoreColor(opportunity.nh_score)}`}
              style={{ width: `${opportunity.nh_score}%` }}
            />
          </div>
          <span className="text-xs text-gray-500">{opportunity.nh_score}</span>
        </div>
      )}

      {/* Actions */}
      <div className="mt-3 flex items-center gap-2">
        {opportunity.external_url && (
          <a
            href={opportunity.external_url}
            target="_blank"
            rel="noopener noreferrer"
            className="p-1.5 hover:bg-gray-100 dark:hover:bg-gray-800 rounded"
          >
            <ExternalLink size={14} />
          </a>
        )}
        <div className="flex-1" />
        {nextStatus && (
          <button
            onClick={() => onMove(opportunity.id, nextStatus)}
            className="flex items-center gap-1 px-2 py-1 text-xs bg-blue-50 dark:bg-blue-900/30 text-blue-600 rounded hover:bg-blue-100 dark:hover:bg-blue-900/50"
          >
            Move to {STATUS_CONFIG[nextStatus].label}
            <ChevronRight size={12} />
          </button>
        )}
      </div>
    </div>
  );
}

// ==========================================================================
// Kanban Column
// ==========================================================================

interface KanbanColumnProps {
  status: OpportunityStatus;
  opportunities: Opportunity[];
  onMove: (id: string, status: OpportunityStatus) => void;
  onAnalyze: (id: string) => void;
  onDelete: (id: string) => void;
}

function KanbanColumn({ status, opportunities, onMove, onAnalyze, onDelete }: KanbanColumnProps) {
  const config = STATUS_CONFIG[status];
  const totalValue = opportunities.reduce((sum, o) => sum + (Number(o.value) || 0), 0);

  return (
    <div className="flex-shrink-0 w-72">
      <div className={`rounded-t-lg px-3 py-2 ${config.bgColor}`}>
        <div className="flex items-center justify-between">
          <span className={`font-medium ${config.color}`}>{config.label}</span>
          <span className="text-sm text-gray-500">{opportunities.length}</span>
        </div>
        {totalValue > 0 && (
          <div className="text-sm text-gray-500">{totalValue.toLocaleString()}</div>
        )}
      </div>
      <div className="bg-gray-50 dark:bg-gray-800/50 rounded-b-lg p-2 min-h-[400px] space-y-2">
        {opportunities.map((opp) => (
          <OpportunityCard
            key={opp.id}
            opportunity={opp}
            onMove={onMove}
            onAnalyze={onAnalyze}
            onDelete={onDelete}
          />
        ))}
        {opportunities.length === 0 && (
          <div className="text-center py-8 text-gray-400 text-sm">
            No opportunities
          </div>
        )}
      </div>
    </div>
  );
}

// ==========================================================================
// Helpers
// ==========================================================================

function getNextStatus(current: OpportunityStatus): OpportunityStatus | null {
  const flow: Record<OpportunityStatus, OpportunityStatus | null> = {
    lead: 'qualified',
    qualified: 'proposal',
    proposal: 'negotiating',
    negotiating: 'won',
    won: 'delivered',
    delivered: null,
    lost: null,
  };
  return flow[current];
}

function getScoreColor(score: number): string {
  if (score >= 80) return 'bg-green-500';
  if (score >= 60) return 'bg-yellow-500';
  if (score >= 40) return 'bg-orange-500';
  return 'bg-red-500';
}

// ==========================================================================
// Main Component
// ==========================================================================

export default function PipelinePage() {
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');

  const { data, isLoading, error } = useOpportunities({ page_size: 100 });
  const createMutation = useCreateOpportunity();
  const moveMutation = useMoveOpportunity();
  const deleteMutation = useDeleteOpportunity();
  const analyzeMutation = useAnalyzeOpportunity();

  // Group opportunities by status
  const opportunitiesByStatus = STATUSES.reduce((acc, status) => {
    acc[status] = data?.items.filter(o => o.status === status) || [];
    return acc;
  }, {} as Record<OpportunityStatus, Opportunity[]>);

  // Filter by search
  const filterOpportunities = (opps: Opportunity[]) => {
    if (!searchQuery) return opps;
    const query = searchQuery.toLowerCase();
    return opps.filter(o =>
      o.title.toLowerCase().includes(query) ||
      o.client_name?.toLowerCase().includes(query) ||
      o.tech_stack?.some(t => t.toLowerCase().includes(query))
    );
  };

  const handleCreate = async (formData: OpportunityCreate) => {
    try {
      await createMutation.mutateAsync(formData);
      setIsAddModalOpen(false);
    } catch {
      // Error handled by mutation
    }
  };

  const handleMove = async (id: string, status: OpportunityStatus) => {
    await moveMutation.mutateAsync({ id, status });
  };

  const handleAnalyze = async (id: string) => {
    await analyzeMutation.mutateAsync(id);
  };

  const handleDelete = async (id: string) => {
    if (confirm('Are you sure you want to delete this opportunity?')) {
      await deleteMutation.mutateAsync(id);
    }
  };

  if (error) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <AlertCircle className="mx-auto text-red-500 mb-2" size={32} />
          <p className="text-red-500">Failed to load pipeline</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4" data-testid="pipeline-page">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Pipeline</h1>
        <button
          onClick={() => setIsAddModalOpen(true)}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          <Plus size={20} />
          Add Opportunity
        </button>
      </div>

      {/* Search & Filter */}
      <div className="flex items-center gap-4">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={18} />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search opportunities..."
            className="w-full pl-10 pr-4 py-2 border rounded-lg dark:bg-gray-800 dark:border-gray-700"
          />
        </div>
        <button className="flex items-center gap-2 px-3 py-2 border rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800">
          <Filter size={18} />
          Filter
        </button>
      </div>

      {/* Kanban Board */}
      {isLoading ? (
        <div className="flex items-center justify-center h-64">
          <Loader2 className="animate-spin text-gray-400" size={32} />
        </div>
      ) : (
        <div className="flex gap-4 overflow-x-auto pb-4">
          {STATUSES.map((status) => (
            <KanbanColumn
              key={status}
              status={status}
              opportunities={filterOpportunities(opportunitiesByStatus[status])}
              onMove={handleMove}
              onAnalyze={handleAnalyze}
              onDelete={handleDelete}
            />
          ))}
        </div>
      )}

      {/* Add Modal */}
      <AddOpportunityModal
        isOpen={isAddModalOpen}
        onClose={() => setIsAddModalOpen(false)}
        onSubmit={handleCreate}
        isLoading={createMutation.isPending}
      />
    </div>
  );
}
