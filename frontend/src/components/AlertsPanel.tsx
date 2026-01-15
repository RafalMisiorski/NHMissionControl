import { AlertTriangle, CheckCircle, Info, XCircle, Bell } from 'lucide-react';
import type { Alert } from '../types';

interface AlertsPanelProps {
  alerts: Alert[];
  onAcknowledge: (id: string) => void;
}

const severityConfig = {
  info: { icon: Info, bg: 'bg-blue-500/20', border: 'border-blue-500/30', text: 'text-blue-400' },
  warning: { icon: AlertTriangle, bg: 'bg-yellow-500/20', border: 'border-yellow-500/30', text: 'text-yellow-400' },
  error: { icon: XCircle, bg: 'bg-red-500/20', border: 'border-red-500/30', text: 'text-red-400' },
  critical: { icon: Bell, bg: 'bg-red-600/30', border: 'border-red-600/50', text: 'text-red-300' },
};

export default function AlertsPanel({ alerts, onAcknowledge }: AlertsPanelProps) {
  if (alerts.length === 0) {
    return (
      <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-6">
        <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <Bell className="w-5 h-5" />
          Alerts
        </h2>
        <div className="text-center py-8 text-gray-400">
          <CheckCircle className="w-12 h-12 mx-auto mb-3 text-green-400" />
          <p>No active alerts</p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-6">
      <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
        <Bell className="w-5 h-5" />
        Alerts
        <span className="bg-red-500 text-white text-xs px-2 py-0.5 rounded-full">
          {alerts.filter(a => !a.acknowledged).length}
        </span>
      </h2>
      <div className="space-y-3 max-h-96 overflow-y-auto">
        {alerts.map((alert) => {
          const config = severityConfig[alert.severity];
          const Icon = config.icon;
          return (
            <div
              key={alert.id}
              className={`${config.bg} ${config.border} border rounded-lg p-4 ${
                alert.acknowledged ? 'opacity-60' : ''
              }`}
            >
              <div className="flex items-start gap-3">
                <Icon className={`w-5 h-5 ${config.text} mt-0.5`} />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between gap-2">
                    <h3 className="font-medium text-white truncate">{alert.title}</h3>
                    <span className={`text-xs ${config.text} uppercase font-semibold`}>
                      {alert.severity}
                    </span>
                  </div>
                  <p className="text-gray-400 text-sm mt-1">{alert.message}</p>
                  <div className="flex items-center justify-between mt-2">
                    <span className="text-xs text-gray-500">
                      {new Date(alert.created_at).toLocaleString()}
                    </span>
                    {!alert.acknowledged && (
                      <button
                        onClick={() => onAcknowledge(alert.id)}
                        className="text-xs text-cyan-400 hover:text-cyan-300 transition-colors"
                      >
                        Acknowledge
                      </button>
                    )}
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
