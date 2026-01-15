import { Folder, Play, Pause, CheckCircle, Archive } from 'lucide-react';
import type { Project } from '../types';

interface ProjectsListProps {
  projects: Project[];
}

const statusConfig = {
  active: { icon: Play, color: 'text-green-400', bg: 'bg-green-500/20' },
  paused: { icon: Pause, color: 'text-yellow-400', bg: 'bg-yellow-500/20' },
  completed: { icon: CheckCircle, color: 'text-blue-400', bg: 'bg-blue-500/20' },
  archived: { icon: Archive, color: 'text-gray-400', bg: 'bg-gray-500/20' },
};

export default function ProjectsList({ projects }: ProjectsListProps) {
  return (
    <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-6">
      <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
        <Folder className="w-5 h-5" />
        Projects
        <span className="text-gray-400 text-sm font-normal">({projects.length})</span>
      </h2>
      {projects.length === 0 ? (
        <div className="text-center py-8 text-gray-400">
          <Folder className="w-12 h-12 mx-auto mb-3 opacity-50" />
          <p>No projects yet</p>
        </div>
      ) : (
        <div className="space-y-2">
          {projects.map((project) => {
            const config = statusConfig[project.status];
            const Icon = config.icon;
            return (
              <div
                key={project.id}
                className="flex items-center justify-between p-3 rounded-lg bg-slate-700/30 hover:bg-slate-700/50 transition-colors"
              >
                <div className="flex items-center gap-3">
                  <div className={`p-2 rounded-lg ${config.bg}`}>
                    <Icon className={`w-4 h-4 ${config.color}`} />
                  </div>
                  <div>
                    <h3 className="font-medium text-white">{project.name}</h3>
                    {project.description && (
                      <p className="text-sm text-gray-400 truncate max-w-xs">
                        {project.description}
                      </p>
                    )}
                  </div>
                </div>
                <span className={`text-xs ${config.color} uppercase font-medium`}>
                  {project.status}
                </span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
