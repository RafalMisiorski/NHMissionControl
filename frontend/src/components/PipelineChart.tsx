import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from 'recharts';
import { GitBranch } from 'lucide-react';
import type { PipelineStatus } from '../types';

interface PipelineChartProps {
  status: PipelineStatus;
}

const COLORS = {
  running: '#22c55e',
  queued: '#eab308',
  completed: '#3b82f6',
  failed: '#ef4444',
};

export default function PipelineChart({ status }: PipelineChartProps) {
  const data = [
    { name: 'Running', value: status.running, color: COLORS.running },
    { name: 'Queued', value: status.queued, color: COLORS.queued },
    { name: 'Completed', value: status.completed, color: COLORS.completed },
    { name: 'Failed', value: status.failed, color: COLORS.failed },
  ].filter(d => d.value > 0);

  const total = status.running + status.queued + status.completed + status.failed;

  return (
    <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-6">
      <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
        <GitBranch className="w-5 h-5" />
        Pipeline Status
      </h2>
      {total === 0 ? (
        <div className="text-center py-8 text-gray-400">
          <GitBranch className="w-12 h-12 mx-auto mb-3 opacity-50" />
          <p>No pipeline data</p>
        </div>
      ) : (
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={data}
                cx="50%"
                cy="50%"
                innerRadius={50}
                outerRadius={80}
                paddingAngle={5}
                dataKey="value"
              >
                {data.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{
                  backgroundColor: '#1e293b',
                  border: '1px solid #475569',
                  borderRadius: '8px',
                }}
                labelStyle={{ color: '#fff' }}
              />
              <Legend
                formatter={(value) => <span className="text-gray-300">{value}</span>}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>
      )}
      <div className="grid grid-cols-4 gap-2 mt-4">
        {Object.entries(status).map(([key, value]) => (
          <div key={key} className="text-center">
            <div className="text-2xl font-bold text-white">{value}</div>
            <div className="text-xs text-gray-400 capitalize">{key}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
