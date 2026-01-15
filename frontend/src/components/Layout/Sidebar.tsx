/**
 * NH Mission Control - Sidebar Component
 * ========================================
 * 
 * Navigation sidebar with collapsible sections.
 * 
 * EPOCH 2 - Dashboard Shell (WILL BE LOCKED)
 * 
 * TODO for CC:
 * - Add navigation items with icons
 * - Add collapsible functionality
 * - Add mobile drawer version
 * - Add user profile section at bottom
 */

import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  GitBranch,
  DollarSign,
  Brain,
  Settings,
  ChevronLeft,
} from 'lucide-react';
import { useState } from 'react';
import { cn } from '../../lib/utils';

const navItems = [
  {
    title: 'Dashboard',
    href: '/dashboard',
    icon: LayoutDashboard,
  },
  {
    title: 'Pipeline',
    href: '/pipeline',
    icon: GitBranch,
  },
  {
    title: 'Finance',
    href: '/finance',
    icon: DollarSign,
  },
  {
    title: 'Intelligence',
    href: '/intelligence',
    icon: Brain,
  },
  {
    title: 'Settings',
    href: '/settings',
    icon: Settings,
  },
];

export function Sidebar() {
  const [collapsed, setCollapsed] = useState(false);

  return (
    <aside
      className={cn(
        'flex flex-col border-r bg-card transition-all duration-300',
        collapsed ? 'w-16' : 'w-64'
      )}
      data-testid="sidebar"
    >
      {/* Logo */}
      <div className="flex h-16 items-center justify-between border-b px-4">
        {!collapsed && (
          <span className="text-lg font-bold text-foreground">NH Mission Control</span>
        )}
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="rounded-lg p-2 hover:bg-accent"
          data-testid="sidebar-toggle"
        >
          <ChevronLeft
            className={cn(
              'h-5 w-5 transition-transform',
              collapsed && 'rotate-180'
            )}
          />
        </button>
      </div>

      {/* Navigation */}
      <nav className="flex-1 space-y-1 p-2" data-testid="sidebar-nav">
        {navItems.map((item) => (
          <NavLink
            key={item.href}
            to={item.href}
            className={({ isActive }) =>
              cn(
                'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
                isActive
                  ? 'bg-primary text-primary-foreground'
                  : 'text-muted-foreground hover:bg-accent hover:text-foreground'
              )
            }
            data-testid={`nav-${item.title.toLowerCase()}`}
          >
            <item.icon className="h-5 w-5 shrink-0" />
            {!collapsed && <span>{item.title}</span>}
          </NavLink>
        ))}
      </nav>

      {/* Footer */}
      <div className="border-t p-4">
        {!collapsed && (
          <p className="text-xs text-muted-foreground">
            v0.1.0 • North Star Active
          </p>
        )}
      </div>
    </aside>
  );
}
