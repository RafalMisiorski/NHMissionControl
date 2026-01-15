/**
 * NH Asset Registry - Dashboard Component
 * ========================================
 * 
 * Visual interface to view and manage all NH assets:
 * - Hardware inventory
 * - AI tools and delegation rules
 * - Active projects with status
 * - Services and subscriptions
 */

import { useState, useMemo } from 'react';
import {
  Brain,
  HardDrive,
  Layers,
  Package,
  Pause,
  Play,
  Sparkles,
  Target,
  AlertCircle,
  CheckCircle,
  Search,
  ArrowUpDown,
} from 'lucide-react';

// ==========================================================================
// Types (matching Python schema)
// ==========================================================================

type ProjectStatus = 'idea' | 'planning' | 'active' | 'paused' | 'blocked' | 'completed' | 'abandoned';
type ProjectPriority = 'critical' | 'high' | 'medium' | 'low' | 'experimental';
type AssetStatus = 'active' | 'inactive' | 'deprecated' | 'pending' | 'maintenance';

interface BaseAsset {
  id: string;
  name: string;
  type: string;
  status: AssetStatus;
  description: string;
  tags: string[];
}

interface Project extends BaseAsset {
  codename: string;
  project_status: ProjectStatus;
  priority: ProjectPriority;
  category: string;
  tech_stack: string[];
  completion_percent: number;
  income_potential: string;
  can_delegate_to: string[];
  notes?: string;
  blockers?: string[];
}

interface AITool extends BaseAsset {
  provider: string;
  model_name: string;
  cli_command?: string;
  best_for: string[];
  avoid_for: string[];
  speed: string;
  quality: string;
  cost_efficiency: string;
  cost_per_1k_input_tokens: number;
  cost_per_1k_output_tokens: number;
}

interface Hardware extends BaseAsset {
  manufacturer: string;
  model: string;
  capabilities: string[];
  location: string;
}

// ==========================================================================
// Sample Data (from rafal_assets.py)
// ==========================================================================

const PROJECTS: Project[] = [
  {
    id: 'proj-nh-core',
    name: 'Neural Holding (NH)',
    codename: 'NH',
    type: 'project',
    status: 'active',
    project_status: 'active',
    priority: 'critical',
    category: 'ai-enterprise',
    description: '22-layer autonomous enterprise system to enable Citi exit by April 2026',
    tech_stack: ['Python', 'FastAPI', 'React', 'TypeScript', 'PostgreSQL'],
    completion_percent: 35,
    income_potential: 'critical',
    can_delegate_to: ['ai-claude-opus'],
    tags: ['core', 'enterprise', 'autonomous'],
    notes: 'Primary project - must reach operational state by April 2026',
  },
  {
    id: 'proj-nh-mission-control',
    name: 'NH Mission Control',
    codename: 'NHMC',
    type: 'project',
    status: 'active',
    project_status: 'active',
    priority: 'critical',
    category: 'ai-enterprise',
    description: 'Real-time dashboard for NH operations monitoring',
    tech_stack: ['React', 'TypeScript', 'FastAPI', 'PostgreSQL', 'WebSocket'],
    completion_percent: 60,
    income_potential: 'critical',
    can_delegate_to: ['ai-claude-opus', 'ai-claude-sonnet'],
    tags: ['dashboard', 'monitoring'],
  },
  {
    id: 'proj-synaptic-weavers',
    name: 'Synaptic Weavers (SW)',
    codename: 'SW',
    type: 'project',
    status: 'active',
    project_status: 'active',
    priority: 'high',
    category: 'ai-agents',
    description: 'Multi-agent AI system for FastAPI backend generation using TDD',
    tech_stack: ['Python', 'FastAPI', 'Vue 3', 'React'],
    completion_percent: 70,
    income_potential: 'high',
    can_delegate_to: ['ai-claude-opus', 'ai-claude-sonnet'],
    tags: ['multi-agent', 'code-generation'],
  },
  {
    id: 'proj-signal-factory',
    name: 'Signal Factory',
    codename: 'SF',
    type: 'project',
    status: 'active',
    project_status: 'active',
    priority: 'high',
    category: 'trading',
    description: 'Algo trading system with Markov game optimization',
    tech_stack: ['Python', 'NumPy', 'Pandas', 'XTB API'],
    completion_percent: 65,
    income_potential: 'high',
    can_delegate_to: ['ai-claude-opus', 'ai-claude-sonnet'],
    tags: ['trading', 'ml', 'quantitative'],
    notes: 'V8.5-V18 achieved 1.10 Sharpe ratio',
  },
  {
    id: 'proj-time-org-app',
    name: 'Time Organization App',
    codename: 'TOA',
    type: 'project',
    status: 'active',
    project_status: 'active',
    priority: 'high',
    category: 'productivity',
    description: 'ADHD-optimized time management app',
    tech_stack: ['React', 'TypeScript', 'Zustand'],
    completion_percent: 25,
    income_potential: 'medium',
    can_delegate_to: ['ai-claude-opus', 'ai-claude-sonnet'],
    tags: ['productivity', 'adhd', 'personal'],
  },
  {
    id: 'proj-floor-plan-recognition',
    name: 'Floor Plan Recognition',
    codename: 'FPR',
    type: 'project',
    status: 'active',
    project_status: 'paused',
    priority: 'medium',
    category: 'computer-vision',
    description: 'Convert PDF floor plans to IFC format for BIM',
    tech_stack: ['Python', 'OpenCV', 'PyTorch', 'IFCOpenShell'],
    completion_percent: 20,
    income_potential: 'medium',
    can_delegate_to: ['ai-claude-opus', 'ai-gemini-cli'],
    tags: ['cv', 'architecture', 'bim'],
    blockers: ['Watermark handling', 'IFC export complexity'],
  },
  {
    id: 'proj-prospect-finder',
    name: 'NH Prospect Finder',
    codename: 'PF',
    type: 'project',
    status: 'active',
    project_status: 'planning',
    priority: 'high',
    category: 'business',
    description: 'AI-powered lead generation system',
    tech_stack: ['Python', 'FastAPI', 'LangChain'],
    completion_percent: 5,
    income_potential: 'high',
    can_delegate_to: ['ai-claude-opus', 'ai-gemini-cli'],
    tags: ['lead-gen', 'automation'],
  },
];

const AI_TOOLS: AITool[] = [
  {
    id: 'ai-claude-opus',
    name: 'Claude Opus 4',
    type: 'ai_tool',
    status: 'active',
    provider: 'Anthropic',
    model_name: 'claude-opus-4-5-20251101',
    description: 'Most advanced Claude model for critical tasks',
    best_for: ['Complex architecture', 'Critical code', 'NH core', 'Novel problems'],
    avoid_for: ['Simple tasks', 'Basic docs', 'Trivial changes'],
    speed: 'medium',
    quality: 'excellent',
    cost_efficiency: 'low',
    cost_per_1k_input_tokens: 0.015,
    cost_per_1k_output_tokens: 0.075,
    tags: ['primary', 'critical'],
  },
  {
    id: 'ai-claude-sonnet',
    name: 'Claude Sonnet 4',
    type: 'ai_tool',
    status: 'active',
    provider: 'Anthropic',
    model_name: 'claude-sonnet-4-5-20250929',
    description: 'Balanced Claude model for most tasks',
    best_for: ['Standard code', 'Code review', 'Documentation', 'Medium tasks'],
    avoid_for: ['Mission-critical', 'Complex architecture'],
    speed: 'fast',
    quality: 'high',
    cost_efficiency: 'high',
    cost_per_1k_input_tokens: 0.003,
    cost_per_1k_output_tokens: 0.015,
    tags: ['balanced', 'everyday'],
  },
  {
    id: 'ai-gemini-cli',
    name: 'Gemini CLI',
    type: 'ai_tool',
    status: 'active',
    provider: 'Google',
    model_name: 'gemini-2.0-flash',
    cli_command: 'gemini',
    description: 'Fast, free - great for documentation and bulk tasks',
    best_for: ['Documentation', 'README files', 'API docs', 'Bulk processing'],
    avoid_for: ['Critical NH', 'Complex debugging', 'Architecture'],
    speed: 'fast',
    quality: 'medium',
    cost_efficiency: 'high',
    cost_per_1k_input_tokens: 0,
    cost_per_1k_output_tokens: 0,
    tags: ['documentation', 'free'],
  },
  {
    id: 'ai-codex-cli',
    name: 'OpenAI Codex CLI',
    type: 'ai_tool',
    status: 'active',
    provider: 'OpenAI',
    model_name: 'gpt-4o',
    cli_command: 'codex',
    description: 'Good for straightforward coding tasks',
    best_for: ['Simple code', 'Bug fixes', 'Test generation', 'Refactoring'],
    avoid_for: ['NH core', 'Complex multi-file', 'Architecture'],
    speed: 'fast',
    quality: 'medium',
    cost_efficiency: 'medium',
    cost_per_1k_input_tokens: 0.005,
    cost_per_1k_output_tokens: 0.015,
    tags: ['coding', 'simpler-tasks'],
  },
];

const HARDWARE: Hardware[] = [
  {
    id: 'hw-bambu-x1c',
    name: 'Bambu Lab X1 Carbon',
    type: 'hardware',
    status: 'active',
    manufacturer: 'Bambu Lab',
    model: 'X1 Carbon',
    description: 'High-speed 3D printer with AMS',
    capabilities: ['3D printing', 'Multi-material', 'High-speed', 'Lidar scanning'],
    location: 'home_office',
    tags: ['3d-printing', 'prototyping'],
  },
  {
    id: 'hw-einstar-scanner',
    name: 'Einstar 3D Scanner',
    type: 'hardware',
    status: 'active',
    manufacturer: 'Shining 3D',
    model: 'Einstar',
    description: 'Handheld 3D scanner for digitization',
    capabilities: ['3D scanning', 'Texture capture', 'Mesh export'],
    location: 'home_office',
    tags: ['3d-scanning', 'reverse-engineering'],
  },
];

// ==========================================================================
// Style Constants
// ==========================================================================

const PRIORITY_STYLES = {
  critical: { bg: 'bg-red-500/20', text: 'text-red-400', border: 'border-red-500/50' },
  high: { bg: 'bg-orange-500/20', text: 'text-orange-400', border: 'border-orange-500/50' },
  medium: { bg: 'bg-yellow-500/20', text: 'text-yellow-400', border: 'border-yellow-500/50' },
  low: { bg: 'bg-green-500/20', text: 'text-green-400', border: 'border-green-500/50' },
  experimental: { bg: 'bg-purple-500/20', text: 'text-purple-400', border: 'border-purple-500/50' },
};

const STATUS_STYLES: Record<ProjectStatus, { icon: React.ReactNode; color: string }> = {
  active: { icon: <Play size={12} />, color: 'text-green-400' },
  paused: { icon: <Pause size={12} />, color: 'text-yellow-400' },
  planning: { icon: <Target size={12} />, color: 'text-blue-400' },
  idea: { icon: <Sparkles size={12} />, color: 'text-purple-400' },
  blocked: { icon: <AlertCircle size={12} />, color: 'text-red-400' },
  completed: { icon: <CheckCircle size={12} />, color: 'text-green-400' },
  abandoned: { icon: <AlertCircle size={12} />, color: 'text-gray-500' },
};

// ==========================================================================
// Project Card Component
// ==========================================================================

function ProjectCard({ project }: { project: Project }) {
  const [expanded, setExpanded] = useState(false);
  const priority = PRIORITY_STYLES[project.priority];
  const status = STATUS_STYLES[project.project_status] || STATUS_STYLES.active;
  
  return (
    <div className={`rounded-lg border ${priority.border} bg-gray-900 overflow-hidden`}>
      <div 
        className="p-4 cursor-pointer hover:bg-gray-800/50"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <span className={`px-2 py-0.5 text-xs font-bold rounded ${priority.bg} ${priority.text}`}>
                {project.priority.toUpperCase()}
              </span>
              <span className={`flex items-center gap-1 text-xs ${status.color}`}>
                {status.icon}
                {project.project_status}
              </span>
            </div>
            <h3 className="font-semibold text-white mt-2">{project.name}</h3>
            <p className="text-xs text-gray-400 mt-1">{project.description}</p>
          </div>
          
          <div className="text-right">
            <div className="text-2xl font-bold text-white">{project.completion_percent}%</div>
            <div className="w-20 h-1.5 bg-gray-700 rounded-full mt-1">
              <div 
                className={`h-full rounded-full ${
                  project.completion_percent >= 70 ? 'bg-green-500' :
                  project.completion_percent >= 40 ? 'bg-yellow-500' :
                  'bg-red-500'
                }`}
                style={{ width: `${project.completion_percent}%` }}
              />
            </div>
          </div>
        </div>
        
        <div className="flex items-center gap-2 mt-3 flex-wrap">
          {project.tech_stack.slice(0, 4).map(tech => (
            <span key={tech} className="px-2 py-0.5 text-xs bg-gray-800 text-gray-400 rounded">
              {tech}
            </span>
          ))}
          {project.tech_stack.length > 4 && (
            <span className="text-xs text-gray-500">+{project.tech_stack.length - 4}</span>
          )}
        </div>
      </div>
      
      {expanded && (
        <div className="px-4 pb-4 border-t border-gray-800 pt-3 space-y-3">
          {/* Delegation */}
          <div>
            <div className="text-xs text-gray-500 mb-1">Can delegate to:</div>
            <div className="flex gap-2">
              {project.can_delegate_to.map(tool => (
                <span key={tool} className="px-2 py-1 text-xs bg-purple-500/20 text-purple-400 rounded">
                  {AI_TOOLS.find(t => t.id === tool)?.name || tool}
                </span>
              ))}
            </div>
          </div>
          
          {/* Notes */}
          {project.notes && (
            <div>
              <div className="text-xs text-gray-500 mb-1">Notes:</div>
              <p className="text-sm text-gray-300">{project.notes}</p>
            </div>
          )}
          
          {/* Blockers */}
          {project.blockers && project.blockers.length > 0 && (
            <div>
              <div className="text-xs text-gray-500 mb-1">Blockers:</div>
              <ul className="text-sm text-red-400 list-disc list-inside">
                {project.blockers.map((b, i) => <li key={i}>{b}</li>)}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ==========================================================================
// AI Tool Card Component
// ==========================================================================

function AIToolCard({ tool }: { tool: AITool }) {
  const [expanded, setExpanded] = useState(false);
  
  const qualityColors: Record<string, string> = {
    excellent: 'text-green-400',
    high: 'text-blue-400',
    medium: 'text-yellow-400',
    low: 'text-red-400',
  };
  
  return (
    <div className="rounded-lg border border-purple-500/30 bg-gray-900 overflow-hidden">
      <div 
        className="p-4 cursor-pointer hover:bg-gray-800/50"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-purple-500/20">
            <Brain size={20} className="text-purple-400" />
          </div>
          <div className="flex-1">
            <h3 className="font-semibold text-white">{tool.name}</h3>
            <p className="text-xs text-gray-400">{tool.provider} • {tool.model_name}</p>
          </div>
          <div className="text-right text-xs">
            <div className={qualityColors[tool.quality]}>Quality: {tool.quality}</div>
            <div className="text-gray-500">Speed: {tool.speed}</div>
          </div>
        </div>
        
        {/* Cost indicators */}
        <div className="flex items-center gap-4 mt-3 text-xs">
          <span className="text-gray-500">
            In: ${tool.cost_per_1k_input_tokens}/1K
          </span>
          <span className="text-gray-500">
            Out: ${tool.cost_per_1k_output_tokens}/1K
          </span>
          {tool.cli_command && (
            <span className="px-2 py-0.5 bg-gray-800 text-gray-400 rounded font-mono">
              $ {tool.cli_command}
            </span>
          )}
        </div>
      </div>
      
      {expanded && (
        <div className="px-4 pb-4 border-t border-gray-800 pt-3 space-y-3">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <div className="text-xs text-green-500 mb-1">✓ Best for:</div>
              <ul className="text-xs text-gray-300 space-y-1">
                {tool.best_for.map((item, i) => <li key={i}>• {item}</li>)}
              </ul>
            </div>
            <div>
              <div className="text-xs text-red-500 mb-1">✗ Avoid for:</div>
              <ul className="text-xs text-gray-300 space-y-1">
                {tool.avoid_for.map((item, i) => <li key={i}>• {item}</li>)}
              </ul>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ==========================================================================
// Hardware Card Component
// ==========================================================================

function HardwareCard({ hw }: { hw: Hardware }) {
  return (
    <div className="rounded-lg border border-blue-500/30 bg-gray-900 p-4">
      <div className="flex items-center gap-3">
        <div className="p-2 rounded-lg bg-blue-500/20">
          <HardDrive size={20} className="text-blue-400" />
        </div>
        <div className="flex-1">
          <h3 className="font-semibold text-white">{hw.name}</h3>
          <p className="text-xs text-gray-400">{hw.manufacturer} • {hw.model}</p>
        </div>
        <span className="px-2 py-0.5 text-xs bg-green-500/20 text-green-400 rounded">
          {hw.status}
        </span>
      </div>
      
      <div className="flex flex-wrap gap-1 mt-3">
        {hw.capabilities.map(cap => (
          <span key={cap} className="px-2 py-0.5 text-xs bg-gray-800 text-gray-400 rounded">
            {cap}
          </span>
        ))}
      </div>
    </div>
  );
}

// ==========================================================================
// Delegation Matrix Component
// ==========================================================================

function DelegationMatrix() {
  const matrix = [
    { task: 'Critical Code', trivial: '-', low: '-', medium: 'Opus', high: 'Opus', critical: 'Opus' },
    { task: 'Documentation', trivial: 'Gemini', low: 'Gemini', medium: 'Gemini', high: 'Sonnet', critical: 'Opus' },
    { task: 'Simple Fixes', trivial: 'Codex', low: 'Codex', medium: 'Sonnet', high: 'Sonnet', critical: 'Opus' },
    { task: 'Code Review', trivial: 'Codex', low: 'Sonnet', medium: 'Sonnet', high: 'Opus', critical: 'Opus' },
    { task: 'Architecture', trivial: '-', low: '-', medium: 'Opus', high: 'Opus', critical: 'Opus' },
    { task: 'Testing', trivial: 'Codex', low: 'Codex', medium: 'Sonnet', high: 'Sonnet', critical: 'Opus' },
  ];

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-gray-500 text-xs">
            <th className="text-left py-2 px-3">Task Type</th>
            <th className="text-center py-2 px-2">Trivial</th>
            <th className="text-center py-2 px-2">Low</th>
            <th className="text-center py-2 px-2">Medium</th>
            <th className="text-center py-2 px-2">High</th>
            <th className="text-center py-2 px-2">Critical</th>
          </tr>
        </thead>
        <tbody>
          {matrix.map((row, i) => (
            <tr key={i} className="border-t border-gray-800">
              <td className="py-2 px-3 text-white">{row.task}</td>
              <td className="text-center py-2 px-2 text-gray-400">{row.trivial}</td>
              <td className="text-center py-2 px-2 text-gray-400">{row.low}</td>
              <td className="text-center py-2 px-2 text-yellow-400">{row.medium}</td>
              <td className="text-center py-2 px-2 text-orange-400">{row.high}</td>
              <td className="text-center py-2 px-2 text-red-400">{row.critical}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ==========================================================================
// Main Component
// ==========================================================================

type TabType = 'projects' | 'ai-tools' | 'hardware' | 'delegation';

export default function AssetRegistryDashboard() {
  const [activeTab, setActiveTab] = useState<TabType>('projects');
  const [searchQuery, setSearchQuery] = useState('');
  const [priorityFilter, setPriorityFilter] = useState<ProjectPriority | 'all'>('all');
  
  const filteredProjects = useMemo(() => {
    return PROJECTS.filter(p => {
      if (searchQuery && !p.name.toLowerCase().includes(searchQuery.toLowerCase())) {
        return false;
      }
      if (priorityFilter !== 'all' && p.priority !== priorityFilter) {
        return false;
      }
      return true;
    });
  }, [searchQuery, priorityFilter]);
  
  const stats = useMemo(() => ({
    totalProjects: PROJECTS.length,
    activeProjects: PROJECTS.filter(p => p.project_status === 'active').length,
    criticalProjects: PROJECTS.filter(p => p.priority === 'critical').length,
    avgCompletion: Math.round(PROJECTS.reduce((sum, p) => sum + p.completion_percent, 0) / PROJECTS.length),
  }), []);

  const tabs = [
    { id: 'projects', label: 'Projects', icon: <Layers size={16} />, count: PROJECTS.length },
    { id: 'ai-tools', label: 'AI Tools', icon: <Brain size={16} />, count: AI_TOOLS.length },
    { id: 'hardware', label: 'Hardware', icon: <HardDrive size={16} />, count: HARDWARE.length },
    { id: 'delegation', label: 'Delegation Matrix', icon: <ArrowUpDown size={16} /> },
  ];

  return (
    <div className="min-h-screen bg-gray-950 text-white">
      {/* Header */}
      <div className="border-b border-gray-800 bg-gray-900">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-gradient-to-r from-blue-500 to-purple-500">
                <Package size={24} />
              </div>
              <div>
                <h1 className="text-xl font-bold">NH Asset Registry</h1>
                <p className="text-sm text-gray-400">All resources available to Neural Holding</p>
              </div>
            </div>
            
            {/* Quick Stats */}
            <div className="flex items-center gap-6 text-sm">
              <div className="text-center">
                <div className="text-2xl font-bold text-blue-400">{stats.activeProjects}</div>
                <div className="text-xs text-gray-500">Active</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-red-400">{stats.criticalProjects}</div>
                <div className="text-xs text-gray-500">Critical</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-green-400">{stats.avgCompletion}%</div>
                <div className="text-xs text-gray-500">Avg Completion</div>
              </div>
            </div>
          </div>
        </div>
      </div>
      
      {/* Tabs */}
      <div className="border-b border-gray-800 bg-gray-900/50">
        <div className="max-w-7xl mx-auto px-4">
          <div className="flex gap-1">
            {tabs.map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as TabType)}
                className={`flex items-center gap-2 px-4 py-3 text-sm border-b-2 transition-colors ${
                  activeTab === tab.id 
                    ? 'border-blue-500 text-white' 
                    : 'border-transparent text-gray-400 hover:text-white'
                }`}
              >
                {tab.icon}
                {tab.label}
                {tab.count !== undefined && (
                  <span className="px-1.5 py-0.5 text-xs bg-gray-800 rounded">{tab.count}</span>
                )}
              </button>
            ))}
          </div>
        </div>
      </div>
      
      {/* Content */}
      <div className="max-w-7xl mx-auto px-4 py-6">
        {/* Projects Tab */}
        {activeTab === 'projects' && (
          <div className="space-y-4">
            {/* Filters */}
            <div className="flex items-center gap-4">
              <div className="relative flex-1 max-w-md">
                <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
                <input
                  type="text"
                  placeholder="Search projects..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-10 pr-4 py-2 bg-gray-900 border border-gray-700 rounded-lg text-sm"
                />
              </div>
              <select
                value={priorityFilter}
                onChange={(e) => setPriorityFilter(e.target.value as ProjectPriority | 'all')}
                className="px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg text-sm"
              >
                <option value="all">All Priorities</option>
                <option value="critical">Critical</option>
                <option value="high">High</option>
                <option value="medium">Medium</option>
                <option value="low">Low</option>
                <option value="experimental">Experimental</option>
              </select>
            </div>
            
            {/* Project Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {filteredProjects.map(project => (
                <ProjectCard key={project.id} project={project} />
              ))}
            </div>
          </div>
        )}
        
        {/* AI Tools Tab */}
        {activeTab === 'ai-tools' && (
          <div className="space-y-4">
            <p className="text-gray-400 text-sm">
              AI tools available for task delegation. NH automatically routes tasks based on complexity and priority.
            </p>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {AI_TOOLS.map(tool => (
                <AIToolCard key={tool.id} tool={tool} />
              ))}
            </div>
          </div>
        )}
        
        {/* Hardware Tab */}
        {activeTab === 'hardware' && (
          <div className="space-y-4">
            <p className="text-gray-400 text-sm">
              Physical hardware assets available for prototyping and production.
            </p>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {HARDWARE.map(hw => (
                <HardwareCard key={hw.id} hw={hw} />
              ))}
            </div>
          </div>
        )}
        
        {/* Delegation Matrix Tab */}
        {activeTab === 'delegation' && (
          <div className="space-y-4">
            <div className="bg-gray-900 rounded-lg border border-gray-800 p-4">
              <h3 className="font-semibold text-white mb-4">Task Delegation Rules</h3>
              <p className="text-gray-400 text-sm mb-4">
                NH automatically routes tasks to the best AI tool based on task type and complexity.
                This matrix shows which tool handles what.
              </p>
              <DelegationMatrix />
            </div>
            
            <div className="bg-gray-900 rounded-lg border border-gray-800 p-4">
              <h3 className="font-semibold text-white mb-3">Delegation Rules</h3>
              <ul className="space-y-2 text-sm text-gray-300">
                <li className="flex items-start gap-2">
                  <span className="text-red-400">1.</span>
                  <span><strong>Critical projects</strong> (NH, Mission Control) → Always Claude Opus</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-orange-400">2.</span>
                  <span><strong>Documentation</strong> → Gemini CLI (free, good for bulk)</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-yellow-400">3.</span>
                  <span><strong>Simple code fixes</strong> → Codex CLI (saves Claude tokens)</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-green-400">4.</span>
                  <span><strong>Experimental projects</strong> → Codex/Sonnet (acceptable risk)</span>
                </li>
              </ul>
            </div>
          </div>
        )}
      </div>
      
      {/* Footer */}
      <div className="border-t border-gray-800 bg-gray-900/50 px-4 py-3">
        <div className="max-w-7xl mx-auto flex items-center justify-between text-xs text-gray-500">
          <span>NH Asset Registry v1.0</span>
          <span>Last updated: {new Date().toLocaleDateString()}</span>
        </div>
      </div>
    </div>
  );
}
