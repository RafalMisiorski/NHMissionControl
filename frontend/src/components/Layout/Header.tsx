/**
 * NH Mission Control - Header Component
 * =======================================
 * 
 * Top header with user menu and theme toggle.
 * 
 * EPOCH 2 - Dashboard Shell (WILL BE LOCKED)
 */

import { Moon, Sun, LogOut, User, Bell } from 'lucide-react';
import { useTheme } from '../../providers/ThemeProvider';
import { useAuth } from '../../providers/AuthProvider';

export function Header() {
  const { resolvedTheme, setTheme } = useTheme();
  const { user, logout } = useAuth();

  const toggleTheme = () => {
    setTheme(resolvedTheme === 'dark' ? 'light' : 'dark');
  };

  return (
    <header
      className="flex h-16 items-center justify-between border-b bg-card px-6"
      data-testid="header"
    >
      {/* Left side - Breadcrumbs placeholder */}
      <div className="flex items-center gap-2">
        {/* TODO: Add breadcrumbs */}
      </div>

      {/* Right side - Actions */}
      <div className="flex items-center gap-4">
        {/* Notifications */}
        <button
          className="rounded-lg p-2 hover:bg-accent"
          data-testid="notifications-btn"
        >
          <Bell className="h-5 w-5" />
        </button>

        {/* Theme toggle */}
        <button
          onClick={toggleTheme}
          className="rounded-lg p-2 hover:bg-accent"
          data-testid="theme-toggle"
        >
          {resolvedTheme === 'dark' ? (
            <Sun className="h-5 w-5" />
          ) : (
            <Moon className="h-5 w-5" />
          )}
        </button>

        {/* User menu */}
        <div className="flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary text-primary-foreground">
            <User className="h-4 w-4" />
          </div>
          <div className="hidden md:block">
            <p className="text-sm font-medium">{user?.name}</p>
            <p className="text-xs text-muted-foreground">{user?.email}</p>
          </div>
          <button
            onClick={logout}
            className="rounded-lg p-2 hover:bg-accent"
            data-testid="logout-btn"
          >
            <LogOut className="h-5 w-5" />
          </button>
        </div>
      </div>
    </header>
  );
}
