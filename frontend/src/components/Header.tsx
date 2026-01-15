import { Command, Activity, RefreshCw, Moon, Sun, Wifi, WifiOff } from 'lucide-react';

interface HeaderProps {
  health: { status: string; timestamp: string } | null;
  isLoading: boolean;
  onRefresh: () => void;
  afkActive?: boolean;
  isConnected?: boolean;
}

export default function Header({ health, isLoading, onRefresh, afkActive = false, isConnected = false }: HeaderProps) {
  return (
    <header className="bg-slate-900/80 border-b border-slate-700/50 backdrop-blur-sm sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="bg-gradient-to-br from-cyan-500 to-blue-600 p-2 rounded-lg">
              <Command className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-white">NH Mission Control</h1>
              <p className="text-sm text-gray-400">Neural Holding Operations Center</p>
            </div>
          </div>
          <div className="flex items-center gap-4">
            {/* Real-time Connection Status */}
            <div className={`flex items-center gap-2 px-3 py-1.5 rounded-lg ${
              isConnected
                ? 'bg-green-500/20 border border-green-500/30'
                : 'bg-yellow-500/20 border border-yellow-500/30'
            }`}>
              {isConnected ? (
                <>
                  <Wifi className="w-4 h-4 text-green-400" />
                  <span className="text-sm text-green-400 font-medium">Live</span>
                </>
              ) : (
                <>
                  <WifiOff className="w-4 h-4 text-yellow-400" />
                  <span className="text-sm text-yellow-400">Polling</span>
                </>
              )}
            </div>
            {/* AFK Mode Indicator */}
            <div className={`flex items-center gap-2 px-3 py-1.5 rounded-lg ${
              afkActive
                ? 'bg-cyan-500/20 border border-cyan-500/30'
                : 'bg-slate-800/50'
            }`}>
              {afkActive ? (
                <>
                  <Moon className="w-4 h-4 text-cyan-400" />
                  <span className="text-sm text-cyan-400 font-medium">AFK Active</span>
                </>
              ) : (
                <>
                  <Sun className="w-4 h-4 text-gray-400" />
                  <span className="text-sm text-gray-400">Manual Mode</span>
                </>
              )}
            </div>
            {/* Health Status */}
            <div className="flex items-center gap-2">
              <Activity className={`w-4 h-4 ${health?.status === 'healthy' ? 'text-green-400' : 'text-red-400'}`} />
              <span className={`text-sm ${health?.status === 'healthy' ? 'text-green-400' : 'text-red-400'}`}>
                {health?.status || 'Unknown'}
              </span>
            </div>
            <button
              onClick={onRefresh}
              disabled={isLoading}
              className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 transition-colors disabled:opacity-50"
            >
              <RefreshCw className={`w-5 h-5 text-gray-400 ${isLoading ? 'animate-spin' : ''}`} />
            </button>
          </div>
        </div>
      </div>
    </header>
  );
}
