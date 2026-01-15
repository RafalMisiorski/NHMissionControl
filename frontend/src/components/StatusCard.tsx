import type { ReactNode } from 'react';

interface StatusCardProps {
  title: string;
  value: string | number;
  icon: ReactNode;
  trend?: number;
  color?: 'blue' | 'green' | 'yellow' | 'red' | 'cyan';
}

const colorClasses = {
  blue: 'from-blue-500/20 to-blue-600/20 border-blue-500/30',
  green: 'from-green-500/20 to-green-600/20 border-green-500/30',
  yellow: 'from-yellow-500/20 to-yellow-600/20 border-yellow-500/30',
  red: 'from-red-500/20 to-red-600/20 border-red-500/30',
  cyan: 'from-cyan-500/20 to-cyan-600/20 border-cyan-500/30',
};

const iconColorClasses = {
  blue: 'text-blue-400',
  green: 'text-green-400',
  yellow: 'text-yellow-400',
  red: 'text-red-400',
  cyan: 'text-cyan-400',
};

export default function StatusCard({ title, value, icon, trend, color = 'blue' }: StatusCardProps) {
  return (
    <div className={`bg-gradient-to-br ${colorClasses[color]} border rounded-xl p-6 backdrop-blur-sm`}>
      <div className="flex items-center justify-between">
        <div>
          <p className="text-gray-400 text-sm font-medium mb-1">{title}</p>
          <p className="text-3xl font-bold text-white">{value}</p>
          {trend !== undefined && (
            <p className={`text-sm mt-1 ${trend >= 0 ? 'text-green-400' : 'text-red-400'}`}>
              {trend >= 0 ? '↑' : '↓'} {Math.abs(trend)}%
            </p>
          )}
        </div>
        <div className={`${iconColorClasses[color]} opacity-80`}>
          {icon}
        </div>
      </div>
    </div>
  );
}
