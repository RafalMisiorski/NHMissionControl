/**
 * NH Mission Control - Layout Component
 * =======================================
 * 
 * Main application layout with sidebar navigation.
 * 
 * EPOCH 2 - Dashboard Shell (WILL BE LOCKED)
 * 
 * TODO for CC:
 * - Implement Sidebar component
 * - Implement Header component
 * - Add mobile responsiveness
 * - Add breadcrumbs
 */

import { Outlet } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { Header } from './Header';

export function Layout() {
  return (
    <div className="flex h-screen bg-background" data-testid="app-layout">
      {/* Sidebar */}
      <Sidebar />

      {/* Main content area */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Header */}
        <Header />

        {/* Page content */}
        <main className="flex-1 overflow-auto p-6" data-testid="main-content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
