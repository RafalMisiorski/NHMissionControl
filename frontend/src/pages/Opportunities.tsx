import { useState, useMemo } from 'react';
import {
  Target,
  Search,
  TrendingUp,
  DollarSign,
  Plus,
  MoreVertical,
  ChevronRight,
  Star,
  Clock,
  CheckCircle,
  AlertCircle,
} from 'lucide-react';

// Lead stage types
type LeadStage = 'new' | 'analyzing' | 'proposal' | 'negotiation' | 'won' | 'lost';

interface Lead {
  id: string;
  name: string;
  company: string;
  value: number;
  stage: LeadStage;
  score: number;
  technologies: string[];
  source: string;
  createdAt: string;
  lastActivity: string;
  notes?: string;
}

// Sample data - in production this would come from API
const sampleLeads: Lead[] = [
  {
    id: 'lead_001',
    name: 'E-commerce Platform',
    company: 'RetailMax Inc',
    value: 8500,
    stage: 'new',
    score: 85,
    technologies: ['React', 'Node.js', 'PostgreSQL'],
    source: 'Upwork',
    createdAt: '2026-01-10',
    lastActivity: '2026-01-12',
    notes: 'Looking for full-stack developer for MVP',
  },
  {
    id: 'lead_002',
    name: 'Data Pipeline Modernization',
    company: 'FinTech Solutions',
    value: 15000,
    stage: 'analyzing',
    score: 72,
    technologies: ['Python', 'Kafka', 'Spark'],
    source: 'Referral',
    createdAt: '2026-01-08',
    lastActivity: '2026-01-11',
  },
  {
    id: 'lead_003',
    name: 'API Integration Project',
    company: 'HealthSync',
    value: 5000,
    stage: 'proposal',
    score: 90,
    technologies: ['FastAPI', 'Docker', 'AWS'],
    source: 'LinkedIn',
    createdAt: '2026-01-05',
    lastActivity: '2026-01-10',
  },
  {
    id: 'lead_004',
    name: 'SalonBook SaaS',
    company: 'Neural Holding',
    value: 6500,
    stage: 'won',
    score: 95,
    technologies: ['FastAPI', 'React', 'PostgreSQL'],
    source: 'Internal',
    createdAt: '2025-12-15',
    lastActivity: '2026-01-12',
    notes: 'Phase 2 completed, ongoing maintenance',
  },
  {
    id: 'lead_005',
    name: 'Mobile App Backend',
    company: 'StartupXYZ',
    value: 3500,
    stage: 'negotiation',
    score: 68,
    technologies: ['Node.js', 'MongoDB', 'Firebase'],
    source: 'Cold Outreach',
    createdAt: '2026-01-09',
    lastActivity: '2026-01-11',
  },
];

const stageConfig: Record<LeadStage, { label: string; color: string; bgColor: string }> = {
  new: { label: 'New Leads', color: 'text-blue-400', bgColor: 'bg-blue-500/10 border-blue-500/30' },
  analyzing: { label: 'Analyzing', color: 'text-purple-400', bgColor: 'bg-purple-500/10 border-purple-500/30' },
  proposal: { label: 'Proposal', color: 'text-cyan-400', bgColor: 'bg-cyan-500/10 border-cyan-500/30' },
  negotiation: { label: 'Negotiation', color: 'text-yellow-400', bgColor: 'bg-yellow-500/10 border-yellow-500/30' },
  won: { label: 'Won', color: 'text-green-400', bgColor: 'bg-green-500/10 border-green-500/30' },
  lost: { label: 'Lost', color: 'text-red-400', bgColor: 'bg-red-500/10 border-red-500/30' },
};

interface LeadCardProps {
  lead: Lead;
  onMoveToStage?: (leadId: string, stage: LeadStage) => void;
}

function LeadCard({ lead, onMoveToStage }: LeadCardProps) {
  const [showActions, setShowActions] = useState(false);

  const getScoreColor = (score: number) => {
    if (score >= 80) return 'text-green-400';
    if (score >= 60) return 'text-yellow-400';
    return 'text-red-400';
  };

  const nextStage: LeadStage | null = {
    new: 'analyzing',
    analyzing: 'proposal',
    proposal: 'negotiation',
    negotiation: 'won',
    won: null,
    lost: null,
  }[lead.stage] as LeadStage | null;

  return (
    <div className="bg-gray-800/50 border border-gray-700/50 rounded-lg p-4 hover:border-gray-600/50 transition-all cursor-pointer group">
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1 min-w-0">
          <h4 className="text-sm font-medium text-white truncate">{lead.name}</h4>
          <p className="text-xs text-gray-400">{lead.company}</p>
        </div>
        <div className="relative">
          <button
            onClick={() => setShowActions(!showActions)}
            className="p-1 text-gray-400 hover:text-white opacity-0 group-hover:opacity-100 transition-opacity"
          >
            <MoreVertical className="w-4 h-4" />
          </button>
          {showActions && (
            <div className="absolute right-0 top-6 bg-gray-900 border border-gray-700 rounded-lg shadow-xl z-10 py-1 min-w-[120px]">
              {nextStage && (
                <button
                  onClick={() => {
                    onMoveToStage?.(lead.id, nextStage);
                    setShowActions(false);
                  }}
                  className="w-full px-3 py-1.5 text-left text-xs text-gray-300 hover:bg-gray-800 flex items-center gap-2"
                >
                  <ChevronRight className="w-3 h-3" />
                  Move to {stageConfig[nextStage].label}
                </button>
              )}
              <button
                onClick={() => setShowActions(false)}
                className="w-full px-3 py-1.5 text-left text-xs text-red-400 hover:bg-gray-800 flex items-center gap-2"
              >
                <AlertCircle className="w-3 h-3" />
                Mark as Lost
              </button>
            </div>
          )}
        </div>
      </div>

      <div className="flex items-center gap-3 mb-3">
        <div className="flex items-center gap-1">
          <DollarSign className="w-3 h-3 text-green-400" />
          <span className="text-sm font-medium text-green-400">
            ${lead.value.toLocaleString()}
          </span>
        </div>
        <div className="flex items-center gap-1">
          <Star className={`w-3 h-3 ${getScoreColor(lead.score)}`} />
          <span className={`text-xs font-medium ${getScoreColor(lead.score)}`}>
            {lead.score}
          </span>
        </div>
      </div>

      <div className="flex flex-wrap gap-1 mb-3">
        {lead.technologies.slice(0, 3).map((tech) => (
          <span
            key={tech}
            className="px-2 py-0.5 text-xs bg-gray-700/50 text-gray-300 rounded"
          >
            {tech}
          </span>
        ))}
        {lead.technologies.length > 3 && (
          <span className="px-2 py-0.5 text-xs text-gray-500">
            +{lead.technologies.length - 3}
          </span>
        )}
      </div>

      <div className="flex items-center justify-between text-xs text-gray-500">
        <span className="flex items-center gap-1">
          <Clock className="w-3 h-3" />
          {new Date(lead.lastActivity).toLocaleDateString()}
        </span>
        <span>{lead.source}</span>
      </div>
    </div>
  );
}

interface KanbanColumnProps {
  stage: LeadStage;
  leads: Lead[];
  onMoveToStage?: (leadId: string, stage: LeadStage) => void;
}

function KanbanColumn({ stage, leads, onMoveToStage }: KanbanColumnProps) {
  const config = stageConfig[stage];
  const totalValue = leads.reduce((sum, lead) => sum + lead.value, 0);

  return (
    <div className={`flex flex-col min-w-[280px] max-w-[320px] ${config.bgColor} border rounded-xl`}>
      <div className="p-3 border-b border-gray-700/30">
        <div className="flex items-center justify-between mb-1">
          <h3 className={`text-sm font-semibold ${config.color}`}>{config.label}</h3>
          <span className="px-2 py-0.5 text-xs bg-gray-800/50 text-gray-400 rounded-full">
            {leads.length}
          </span>
        </div>
        <p className="text-xs text-gray-500">
          ${totalValue.toLocaleString()} total
        </p>
      </div>
      <div className="flex-1 p-2 space-y-2 overflow-y-auto max-h-[500px]">
        {leads.length === 0 ? (
          <div className="py-8 text-center text-gray-500 text-xs">
            No leads in this stage
          </div>
        ) : (
          leads.map((lead) => (
            <LeadCard key={lead.id} lead={lead} onMoveToStage={onMoveToStage} />
          ))
        )}
      </div>
    </div>
  );
}

export default function Opportunities() {
  const [leads, setLeads] = useState<Lead[]>(sampleLeads);
  const [searchTerm, setSearchTerm] = useState('');

  const filteredLeads = useMemo(() => {
    if (!searchTerm) return leads;
    const term = searchTerm.toLowerCase();
    return leads.filter(
      (lead) =>
        lead.name.toLowerCase().includes(term) ||
        lead.company.toLowerCase().includes(term) ||
        lead.technologies.some((t) => t.toLowerCase().includes(term))
    );
  }, [leads, searchTerm]);

  const leadsByStage = useMemo(() => {
    const stages: LeadStage[] = ['new', 'analyzing', 'proposal', 'negotiation', 'won'];
    return stages.reduce((acc, stage) => {
      acc[stage] = filteredLeads.filter((lead) => lead.stage === stage);
      return acc;
    }, {} as Record<LeadStage, Lead[]>);
  }, [filteredLeads]);

  const handleMoveToStage = (leadId: string, newStage: LeadStage) => {
    setLeads((prev) =>
      prev.map((lead) =>
        lead.id === leadId ? { ...lead, stage: newStage } : lead
      )
    );
  };

  // Calculate metrics
  const totalPipeline = leads
    .filter((l) => !['won', 'lost'].includes(l.stage))
    .reduce((sum, l) => sum + l.value, 0);
  const wonValue = leads
    .filter((l) => l.stage === 'won')
    .reduce((sum, l) => sum + l.value, 0);
  const avgScore = Math.round(
    leads.reduce((sum, l) => sum + l.score, 0) / leads.length
  );

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 to-slate-950">
      {/* Header */}
      <header className="bg-slate-900/80 border-b border-slate-700/50 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-full mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="bg-gradient-to-br from-purple-500 to-pink-600 p-2 rounded-lg">
                <Target className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className="text-xl font-bold text-white">Opportunities Pipeline</h1>
                <p className="text-sm text-gray-400">Track and manage your sales pipeline</p>
              </div>
            </div>
            <div className="flex items-center gap-4">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                <input
                  type="text"
                  placeholder="Search leads..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-10 pr-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-sm text-white placeholder-gray-400 focus:outline-none focus:border-cyan-500"
                />
              </div>
              <button className="flex items-center gap-2 px-4 py-2 bg-cyan-600 hover:bg-cyan-500 text-white rounded-lg text-sm font-medium transition-colors">
                <Plus className="w-4 h-4" />
                Add Lead
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Metrics */}
      <div className="max-w-full mx-auto px-6 py-6">
        <div className="grid grid-cols-4 gap-4 mb-6">
          <div className="bg-gray-800/50 border border-gray-700/50 rounded-xl p-4">
            <div className="flex items-center gap-2 text-gray-400 text-xs mb-1">
              <TrendingUp className="w-4 h-4" />
              Pipeline Value
            </div>
            <p className="text-2xl font-bold text-white">${totalPipeline.toLocaleString()}</p>
          </div>
          <div className="bg-gray-800/50 border border-gray-700/50 rounded-xl p-4">
            <div className="flex items-center gap-2 text-gray-400 text-xs mb-1">
              <CheckCircle className="w-4 h-4 text-green-400" />
              Won Revenue
            </div>
            <p className="text-2xl font-bold text-green-400">${wonValue.toLocaleString()}</p>
          </div>
          <div className="bg-gray-800/50 border border-gray-700/50 rounded-xl p-4">
            <div className="flex items-center gap-2 text-gray-400 text-xs mb-1">
              <Target className="w-4 h-4" />
              Active Leads
            </div>
            <p className="text-2xl font-bold text-white">
              {leads.filter((l) => !['won', 'lost'].includes(l.stage)).length}
            </p>
          </div>
          <div className="bg-gray-800/50 border border-gray-700/50 rounded-xl p-4">
            <div className="flex items-center gap-2 text-gray-400 text-xs mb-1">
              <Star className="w-4 h-4 text-yellow-400" />
              Avg Lead Score
            </div>
            <p className="text-2xl font-bold text-yellow-400">{avgScore}</p>
          </div>
        </div>

        {/* Kanban Board */}
        <div className="flex gap-4 overflow-x-auto pb-4">
          {(['new', 'analyzing', 'proposal', 'negotiation', 'won'] as LeadStage[]).map(
            (stage) => (
              <KanbanColumn
                key={stage}
                stage={stage}
                leads={leadsByStage[stage] || []}
                onMoveToStage={handleMoveToStage}
              />
            )
          )}
        </div>
      </div>
    </div>
  );
}
