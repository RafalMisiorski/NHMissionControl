/**
 * NH Complete System Overview
 * ============================
 *
 * Interactive visualization of the complete NH ecosystem:
 * - CC Dispatcher (task routing)
 * - SyncWave Integration (notifications)
 * - GitHub Auto-Update (progress tracking)
 * - Asset Registry (resources)
 * - Nerve Center (real-time monitoring)
 */

import { useState, useEffect } from 'react';
import {
  Brain,
  Smartphone,
  GitBranch,
  Zap,
  Activity,
  Package,
  ArrowRight,
  Bell,
  CheckCircle,
  Terminal,
  Globe,
  Layers,
  Play,
  Pause,
} from 'lucide-react';

// ==========================================================================
// Types
// ==========================================================================

interface RoutingExample {
  task: string;
  project: string;
  priority: 'critical' | 'high' | 'medium' | 'low';
  tool: string;
  reason: string;
}

interface Notification {
  type: 'task' | 'github' | 'progress' | 'complete' | 'blocker' | 'error';
  icon: string;
  title: string;
  body: string;
  time: string;
}

interface ProjectStatus {
  id: string;
  name: string;
  completion: number;
  priority: 'critical' | 'high' | 'medium' | 'low';
  status: 'active' | 'paused' | 'blocked';
}

interface SystemNodeProps {
  icon: React.ReactNode;
  title: string;
  subtitle: string;
  active?: boolean;
  onClick?: () => void;
}

interface DataFlowProps {
  from: string;
  to: string;
  label?: string;
  active?: boolean;
}

interface NotificationItemProps {
  notif: Notification;
}

interface RoutingDemoProps {
  example: RoutingExample;
  isActive: boolean;
}

interface ProjectProgressProps {
  project: ProjectStatus;
}

interface SyncWaveStatus {
  syncwave_enabled: boolean;
  mode: 'live' | 'logging_only';
  api_url: string | null;
}

// ==========================================================================
// Mock Data
// ==========================================================================

const ROUTING_EXAMPLES: RoutingExample[] = [
  { task: 'Fix NH auth bug', project: 'NHMC', priority: 'critical', tool: 'Claude Opus', reason: 'Critical project' },
  { task: 'Write SF docs', project: 'SF', priority: 'high', tool: 'Gemini CLI', reason: 'Free, good for docs' },
  { task: 'Add TOA tests', project: 'TOA', priority: 'high', tool: 'Codex CLI', reason: 'Simple tests' },
  { task: 'Design PF arch', project: 'PF', priority: 'high', tool: 'Claude Opus', reason: 'Architecture = Opus' },
];

const NOTIFICATIONS: Notification[] = [
  { type: 'task', icon: '🚀', title: 'Task Started', body: 'Fix auth bug → Claude Opus', time: '2s ago' },
  { type: 'github', icon: '📦', title: 'Push: SW', body: '3 commits → +2.5%', time: '5m ago' },
  { type: 'progress', icon: '📈', title: 'Progress: SW', body: '70% → 72.5%', time: '5m ago' },
  { type: 'complete', icon: '✅', title: 'Task Done', body: 'README by Gemini', time: '12m ago' },
  { type: 'blocker', icon: '🔓', title: 'Blocker Update', body: 'FPR: watermark solution found', time: '1h ago' },
];

const PROJECTS_STATUS: ProjectStatus[] = [
  { id: 'NH', name: 'Neural Holding', completion: 35, priority: 'critical', status: 'active' },
  { id: 'NHMC', name: 'Mission Control', completion: 60, priority: 'critical', status: 'active' },
  { id: 'SW', name: 'Synaptic Weavers', completion: 72.5, priority: 'high', status: 'active' },
  { id: 'SF', name: 'Signal Factory', completion: 65, priority: 'high', status: 'active' },
  { id: 'TOA', name: 'Time Org App', completion: 25, priority: 'high', status: 'active' },
  { id: 'FPR', name: 'Floor Plan', completion: 20, priority: 'medium', status: 'paused' },
];

// ==========================================================================
// Components
// ==========================================================================

function SystemNode({ icon, title, subtitle, active, onClick }: SystemNodeProps) {
  return (
    <div
      onClick={onClick}
      className={`p-3 rounded-lg border cursor-pointer transition-all ${
        active
          ? 'border-blue-500 bg-blue-500/10 shadow-lg shadow-blue-500/20'
          : 'border-gray-700 bg-gray-900 hover:border-gray-600'
      }`}
    >
      <div className="flex items-center gap-2">
        <div className={`p-2 rounded-lg ${active ? 'bg-blue-500/20' : 'bg-gray-800'}`}>
          {icon}
        </div>
        <div>
          <div className="font-medium text-sm">{title}</div>
          <div className="text-[10px] text-gray-500">{subtitle}</div>
        </div>
      </div>
    </div>
  );
}

function DataFlow({ from, to, label, active }: DataFlowProps) {
  return (
    <div className={`flex items-center gap-1 text-[10px] ${active ? 'text-blue-400' : 'text-gray-600'}`}>
      <span>{from}</span>
      <ArrowRight size={10} className={active ? 'animate-pulse' : ''} />
      <span>{to}</span>
      {label && <span className="text-gray-500">({label})</span>}
    </div>
  );
}

function NotificationItem({ notif }: NotificationItemProps) {
  const bgColors: Record<Notification['type'], string> = {
    task: 'bg-blue-500/10',
    github: 'bg-purple-500/10',
    progress: 'bg-green-500/10',
    complete: 'bg-green-500/10',
    blocker: 'bg-yellow-500/10',
    error: 'bg-red-500/10',
  };

  return (
    <div className={`p-2 rounded-lg ${bgColors[notif.type]} flex items-start gap-2`}>
      <span className="text-lg">{notif.icon}</span>
      <div className="flex-1 min-w-0">
        <div className="font-medium text-xs">{notif.title}</div>
        <div className="text-[10px] text-gray-400 truncate">{notif.body}</div>
      </div>
      <span className="text-[10px] text-gray-500">{notif.time}</span>
    </div>
  );
}

function RoutingDemo({ example, isActive }: RoutingDemoProps) {
  const priorityColors: Record<RoutingExample['priority'], string> = {
    critical: 'text-red-400 bg-red-400/10',
    high: 'text-orange-400 bg-orange-400/10',
    medium: 'text-yellow-400 bg-yellow-400/10',
    low: 'text-gray-400 bg-gray-400/10',
  };

  return (
    <div className={`p-2 rounded-lg border ${isActive ? 'border-green-500/50 bg-green-500/5' : 'border-gray-800'}`}>
      <div className="flex items-center justify-between">
        <div className="flex-1">
          <div className="text-xs font-medium">{example.task}</div>
          <div className="flex items-center gap-2 mt-1">
            <span className={`px-1.5 py-0.5 text-[10px] rounded ${priorityColors[example.priority]}`}>
              {example.project}
            </span>
            <ArrowRight size={10} className="text-gray-500" />
            <span className="text-[10px] text-purple-400">{example.tool}</span>
          </div>
        </div>
        {isActive && <CheckCircle size={14} className="text-green-400" />}
      </div>
      <div className="text-[10px] text-gray-500 mt-1">💡 {example.reason}</div>
    </div>
  );
}

function ProjectProgress({ project }: ProjectProgressProps) {
  const priorityColors: Record<ProjectStatus['priority'], string> = {
    critical: 'bg-red-500',
    high: 'bg-orange-500',
    medium: 'bg-yellow-500',
    low: 'bg-gray-500',
  };

  return (
    <div className="flex items-center gap-2 py-1">
      <div className={`w-1.5 h-1.5 rounded-full ${priorityColors[project.priority]}`} />
      <span className="text-xs w-16 truncate">{project.id}</span>
      <div className="flex-1 h-1.5 bg-gray-800 rounded-full overflow-hidden">
        <div
          className={`h-full ${project.status === 'active' ? 'bg-blue-500' : 'bg-gray-600'}`}
          style={{ width: `${project.completion}%` }}
        />
      </div>
      <span className="text-[10px] text-gray-500 w-10 text-right">{project.completion}%</span>
    </div>
  );
}

// ==========================================================================
// Main Component
// ==========================================================================

export default function SystemOverview() {
  const [activeNode, setActiveNode] = useState<string | null>(null);
  const [activeRouting, setActiveRouting] = useState(0);
  const [isFlowing, setIsFlowing] = useState(true);
  const [syncWaveStatus, setSyncWaveStatus] = useState<SyncWaveStatus | null>(null);
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [projects, setProjects] = useState<ProjectStatus[]>([]);

  // Fetch real data on mount
  useEffect(() => {
    // Fetch SyncWave status
    fetch('/api/v1/notify/status')
      .then(res => res.json())
      .then(data => setSyncWaveStatus(data))
      .catch(() => setSyncWaveStatus({ syncwave_enabled: false, mode: 'logging_only', api_url: null }));

    // Fetch recent events for notifications
    fetch('/api/v1/nerve-center/events?limit=10')
      .then(res => res.json())
      .then(events => {
        const notifs: Notification[] = events.map((e: any) => {
          const typeMap: Record<string, Notification['type']> = {
            'system': 'complete',
            'agent': 'task',
            'api': 'github',
            'analysis': 'progress',
            'error': 'error',
          };
          const iconMap: Record<string, string> = {
            'system': '🚀',
            'agent': '🤖',
            'api': '📡',
            'analysis': '📊',
            'file': '📁',
            'error': '❌',
          };
          const timeDiff = Date.now() - new Date(e.timestamp).getTime();
          const timeStr = timeDiff < 60000 ? 'just now' : 
                          timeDiff < 3600000 ? Math.floor(timeDiff / 60000) + 'm ago' :
                          Math.floor(timeDiff / 3600000) + 'h ago';
          return {
            type: typeMap[e.category] || 'task',
            icon: iconMap[e.category] || '📌',
            title: e.event_type.split('.').pop()?.replace(/_/g, ' ').replace(/\w/g, (l: string) => l.toUpperCase()) || 'Event',
            body: e.message.substring(0, 50),
            time: timeStr,
          };
        });
        setNotifications(notifs.length > 0 ? notifs : NOTIFICATIONS);
      })
      .catch(() => setNotifications(NOTIFICATIONS));

    // Fetch projects progress
    fetch('/api/v1/webhooks/projects/progress')
      .then(res => res.json())
      .then(data => {
        const projectMap: Record<string, { name: string; priority: ProjectStatus['priority'] }> = {
          'nh': { name: 'Neural Holding', priority: 'critical' },
          'nhmc': { name: 'Mission Control', priority: 'critical' },
          'sw': { name: 'Synaptic Weavers', priority: 'high' },
          'sf': { name: 'Signal Factory', priority: 'high' },
          'toa': { name: 'Time Org App', priority: 'high' },
          'pf': { name: 'Prospect Finder', priority: 'medium' },
          'fpr': { name: 'Floor Plan', priority: 'medium' },
          'cn': { name: 'Career Navigator', priority: 'medium' },
          'us': { name: 'Upwork Scraper', priority: 'low' },
        };
        const projs: ProjectStatus[] = data.projects.map((p: any) => ({
          id: p.id.toUpperCase(),
          name: projectMap[p.id]?.name || p.id,
          completion: p.completion,
          priority: projectMap[p.id]?.priority || 'medium',
          status: p.completion >= 100 ? 'completed' : 'active',
        }));
        setProjects(projs.length > 0 ? projs : PROJECTS_STATUS);
      })
      .catch(() => setProjects(PROJECTS_STATUS));
  }, []);

  // Simulate routing animation
  useEffect(() => {
    if (!isFlowing) return;

    const interval = setInterval(() => {
      setActiveRouting(prev => (prev + 1) % ROUTING_EXAMPLES.length);
    }, 3000);

    return () => clearInterval(interval);
  }, [isFlowing]);

  return (
    <div className="min-h-screen bg-gray-950 text-white p-4">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-gradient-to-r from-blue-500 to-purple-500">
            <Zap size={20} />
          </div>
          <div>
            <h1 className="font-bold text-lg">NH System Overview</h1>
            <p className="text-xs text-gray-400">Complete ecosystem visualization</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setIsFlowing(!isFlowing)}
            className={`p-2 rounded-lg ${isFlowing ? 'bg-green-500/20 text-green-400' : 'bg-gray-800'}`}
          >
            {isFlowing ? <Play size={14} /> : <Pause size={14} />}
          </button>
          <div className="text-xs text-gray-500">
            {isFlowing ? 'Live' : 'Paused'}
          </div>
        </div>
      </div>

      {/* Main Grid */}
      <div className="grid grid-cols-12 gap-4">
        {/* Left: System Architecture */}
        <div className="col-span-8 space-y-4">
          {/* Top Row: User Inputs */}
          <div className="grid grid-cols-3 gap-3">
            <SystemNode
              icon={<Smartphone size={16} className="text-green-400" />}
              title="SyncWave"
              subtitle="Phone App"
              active={activeNode === 'syncwave'}
              onClick={() => setActiveNode('syncwave')}
            />
            <SystemNode
              icon={<Globe size={16} className="text-blue-400" />}
              title="Claude.ai"
              subtitle="Web Interface"
              active={activeNode === 'claude'}
              onClick={() => setActiveNode('claude')}
            />
            <SystemNode
              icon={<Terminal size={16} className="text-purple-400" />}
              title="Claude Code"
              subtitle="CLI"
              active={activeNode === 'cc'}
              onClick={() => setActiveNode('cc')}
            />
          </div>

          {/* Flow Indicators */}
          <div className="flex justify-center gap-8 py-2">
            <DataFlow from="SyncWave" to="CC" active={isFlowing} />
            <DataFlow from="Claude.ai" to="Memory" active={isFlowing} />
            <DataFlow from="CC" to="Dispatcher" active={isFlowing} />
          </div>

          {/* Center: CC Dispatcher */}
          <div className="bg-gray-900 rounded-xl border border-purple-500/30 p-4">
            <div className="flex items-center gap-2 mb-3">
              <Brain size={18} className="text-purple-400" />
              <span className="font-semibold">CC Dispatcher</span>
              <span className="text-[10px] text-purple-400 bg-purple-400/20 px-2 py-0.5 rounded">Task Router</span>
            </div>

            <div className="grid grid-cols-2 gap-3">
              {ROUTING_EXAMPLES.map((ex, i) => (
                <RoutingDemo key={i} example={ex} isActive={activeRouting === i && isFlowing} />
              ))}
            </div>
          </div>

          {/* AI Tools Row */}
          <div className="grid grid-cols-4 gap-3">
            <SystemNode
              icon={<Brain size={16} className="text-red-400" />}
              title="Claude Opus"
              subtitle="Critical Tasks"
              active={activeRouting === 0 || activeRouting === 3}
            />
            <SystemNode
              icon={<Brain size={16} className="text-blue-400" />}
              title="Claude Sonnet"
              subtitle="Standard"
              active={false}
            />
            <SystemNode
              icon={<Zap size={16} className="text-yellow-400" />}
              title="Gemini CLI"
              subtitle="Docs (Free)"
              active={activeRouting === 1}
            />
            <SystemNode
              icon={<Terminal size={16} className="text-green-400" />}
              title="Codex CLI"
              subtitle="Simple Code"
              active={activeRouting === 2}
            />
          </div>

          {/* Bottom: Infrastructure */}
          <div className="grid grid-cols-3 gap-3">
            <SystemNode
              icon={<Activity size={16} className="text-green-400" />}
              title="Nerve Center"
              subtitle="Real-time Events"
              active={activeNode === 'nerve'}
              onClick={() => setActiveNode('nerve')}
            />
            <SystemNode
              icon={<Package size={16} className="text-blue-400" />}
              title="Asset Registry"
              subtitle="11 Projects"
              active={activeNode === 'assets'}
              onClick={() => setActiveNode('assets')}
            />
            <SystemNode
              icon={<GitBranch size={16} className="text-purple-400" />}
              title="GitHub Hooks"
              subtitle="Auto-Update"
              active={activeNode === 'github'}
              onClick={() => setActiveNode('github')}
            />
          </div>
        </div>

        {/* Right: Live Panels */}
        <div className="col-span-4 space-y-4">
          {/* SyncWave Notifications */}
          <div className="bg-gray-900 rounded-xl border border-green-500/30 p-3">
            <div className="flex items-center gap-2 mb-3">
              <Bell size={14} className="text-green-400" />
              <span className="font-medium text-sm">SyncWave Feed</span>
              {syncWaveStatus?.syncwave_enabled ? (
                <span className="text-[10px] text-green-400">● Live</span>
              ) : (
                <span className="text-[10px] text-yellow-400">● Logging Only</span>
              )}
            </div>
            <div className="space-y-2 max-h-48 overflow-y-auto">
              {notifications.map((n, i) => (
                <NotificationItem key={i} notif={n} />
              ))}
            </div>
          </div>

          {/* Project Progress */}
          <div className="bg-gray-900 rounded-xl border border-blue-500/30 p-3">
            <div className="flex items-center gap-2 mb-3">
              <Layers size={14} className="text-blue-400" />
              <span className="font-medium text-sm">Projects</span>
            </div>
            <div className="space-y-1">
              {projects.map(p => (
                <ProjectProgress key={p.id} project={p} />
              ))}
            </div>
          </div>

          {/* Memory Sync */}
          <div className="bg-gray-900 rounded-xl border border-yellow-500/30 p-3">
            <div className="flex items-center gap-2 mb-2">
              <Brain size={14} className="text-yellow-400" />
              <span className="font-medium text-sm">Claude Memory</span>
              <CheckCircle size={12} className="text-green-400" />
            </div>
            <div className="text-[10px] text-gray-400 space-y-1">
              <div>✓ Projects: NH, NHMC, SW, SF, TOA, PF, FPR</div>
              <div>✓ Delegation: Opus/Sonnet/Gemini/Codex</div>
              <div>✓ Hardware: Bambu X1C, Einstar</div>
              <div>✓ Goal: Apr 2026 autonomy</div>
            </div>
          </div>
        </div>
      </div>

      {/* Footer Stats */}
      <div className="mt-6 grid grid-cols-5 gap-4 text-center">
        <div className="bg-gray-900 rounded-lg p-3">
          <div className="text-2xl font-bold text-blue-400">11</div>
          <div className="text-[10px] text-gray-500">Projects</div>
        </div>
        <div className="bg-gray-900 rounded-lg p-3">
          <div className="text-2xl font-bold text-purple-400">4</div>
          <div className="text-[10px] text-gray-500">AI Tools</div>
        </div>
        <div className="bg-gray-900 rounded-lg p-3">
          <div className="text-2xl font-bold text-green-400">2</div>
          <div className="text-[10px] text-gray-500">Hardware</div>
        </div>
        <div className="bg-gray-900 rounded-lg p-3">
          <div className="text-2xl font-bold text-yellow-400">6</div>
          <div className="text-[10px] text-gray-500">Memory Items</div>
        </div>
        <div className="bg-gray-900 rounded-lg p-3">
          <div className="text-2xl font-bold text-red-400">Apr 26</div>
          <div className="text-[10px] text-gray-500">Target Date</div>
        </div>
      </div>
    </div>
  );
}
