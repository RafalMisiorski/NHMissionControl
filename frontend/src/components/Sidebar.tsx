import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  Target,
  DollarSign,
  Settings,
  Command,
  Zap,
  Package,
  Network,
  GitBranch,
  Shield,
  Terminal,
} from 'lucide-react';

const navItems = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/pipeline', icon: GitBranch, label: 'Pipeline', badge: 'NEW' },
  { to: '/cc-sessions', icon: Terminal, label: 'CC Sessions', badge: 'E8' },
  { to: '/opportunities', icon: Target, label: 'Opportunities' },
  { to: '/finance', icon: DollarSign, label: 'Finance' },
  { to: '/assets', icon: Package, label: 'Asset Registry' },
  { to: '/nerve-center', icon: Zap, label: 'Nerve Center', badge: 'LIVE' },
  { to: '/guardrails', icon: Shield, label: 'Guardrails' },
  { to: '/system', icon: Network, label: 'System Overview' },
];

export default function Sidebar() {
  return (
    <aside className="w-16 bg-slate-900/80 border-r border-slate-700/50 flex flex-col items-center py-4 gap-2">
      {/* Logo */}
      <div className="bg-gradient-to-br from-cyan-500 to-blue-600 p-2 rounded-lg mb-4">
        <Command className="w-5 h-5 text-white" />
      </div>

      {/* Navigation */}
      <nav className="flex flex-col gap-1">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              `p-3 rounded-lg transition-all flex items-center justify-center relative ${
                isActive
                  ? 'bg-cyan-500/20 text-cyan-400'
                  : 'text-gray-400 hover:text-white hover:bg-slate-800'
              }`
            }
            title={item.label}
          >
            <item.icon className="w-5 h-5" />
            {'badge' in item && item.badge && (
              <span className="absolute -top-1 -right-1 px-1 py-0.5 text-[8px] font-bold bg-green-500 text-white rounded">
                {item.badge}
              </span>
            )}
          </NavLink>
        ))}
      </nav>

      {/* Settings at bottom */}
      <div className="mt-auto">
        <button
          className="p-3 rounded-lg text-gray-400 hover:text-white hover:bg-slate-800 transition-all"
          title="Settings"
        >
          <Settings className="w-5 h-5" />
        </button>
      </div>
    </aside>
  );
}
