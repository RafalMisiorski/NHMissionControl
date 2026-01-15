/**
 * Guardrails Monitor
 * ==================
 *
 * 4-layer guardrails visualization with policy editing and violation logs.
 * Connects to /api/v1/guardrails/* endpoints.
 */

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Shield,
  Lock,
  FileText,
  Sliders,
  Settings,
  AlertTriangle,
  CheckCircle,
  XCircle,
  ChevronRight,
  ChevronDown,
  ArrowRight,
  RefreshCw,
  Edit3,
  Save,
  X,
  Clock,
  User,
} from 'lucide-react';

// ==========================================================================
// Types
// ==========================================================================

interface InvariantItem {
  name: string;
  value: unknown;
  description: string;
}

interface PolicyItem {
  name: string;
  value: number;
  min_value: number;
  max_value: number;
  description: string;
}

interface PreferenceItem {
  name: string;
  value: unknown;
}

interface RolePermissions {
  role: string;
  can_approve_po_review: boolean;
  can_override_guardrails: boolean;
  can_modify_policies: boolean;
  can_modify_invariants: boolean;
}

interface GuardrailsConfig {
  invariants: InvariantItem[];
  policies: PolicyItem[];
  preferences: PreferenceItem[];
  roles: RolePermissions[];
}

interface GuardrailViolation {
  id: string;
  layer: string;
  rule_name: string;
  attempted_action: string;
  blocked: boolean;
  override_reason: string | null;
  actor: string | null;
  pipeline_run_id: string | null;
  context: Record<string, unknown> | null;
  created_at: string;
}

interface StageTransition {
  from: string;
  to: string;
  description: string;
}

interface StageTransitions {
  stage_order: string[];
  valid_transitions: StageTransition[];
}

// ==========================================================================
// API Functions
// ==========================================================================

const API_BASE = '/api/v1/guardrails';

async function fetchGuardrailsConfig(): Promise<GuardrailsConfig> {
  const res = await fetch(API_BASE);
  if (!res.ok) throw new Error('Failed to fetch guardrails config');
  return res.json();
}

async function fetchViolations(limit = 20): Promise<GuardrailViolation[]> {
  const res = await fetch(`${API_BASE}/violations?limit=${limit}`);
  if (!res.ok) throw new Error('Failed to fetch violations');
  return res.json();
}

async function fetchStageTransitions(): Promise<StageTransitions> {
  const res = await fetch(`${API_BASE}/stage-transitions`);
  if (!res.ok) throw new Error('Failed to fetch stage transitions');
  return res.json();
}

async function updatePolicy(name: string, value: number): Promise<void> {
  const res = await fetch(`${API_BASE}/policies/${name}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ value }),
  });
  if (!res.ok) throw new Error('Failed to update policy');
}

async function updatePreference(name: string, value: unknown): Promise<void> {
  const res = await fetch(`${API_BASE}/preferences/${name}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ value }),
  });
  if (!res.ok) throw new Error('Failed to update preference');
}

// ==========================================================================
// Layer Configuration
// ==========================================================================

const LAYERS = [
  {
    id: 'invariants',
    label: 'L1: Invariants',
    description: 'Immutable rules that cannot be changed',
    icon: Lock,
    color: 'red',
    locked: true,
  },
  {
    id: 'contracts',
    label: 'L2: Contracts',
    description: 'Schema-based validation rules',
    icon: FileText,
    color: 'orange',
    locked: true,
  },
  {
    id: 'policies',
    label: 'L3: Policies',
    description: 'Configurable within defined bounds',
    icon: Sliders,
    color: 'yellow',
    locked: false,
  },
  {
    id: 'preferences',
    label: 'L4: Preferences',
    description: 'Freely changeable settings',
    icon: Settings,
    color: 'green',
    locked: false,
  },
];

// ==========================================================================
// InvariantRow Component
// ==========================================================================

interface InvariantRowProps {
  item: InvariantItem;
}

function InvariantRow({ item }: InvariantRowProps) {
  const [expanded, setExpanded] = useState(false);

  const displayValue = Array.isArray(item.value)
    ? `[${(item.value as string[]).length} items]`
    : typeof item.value === 'object'
    ? JSON.stringify(item.value)
    : String(item.value);

  return (
    <div className="border-b border-gray-800 last:border-0">
      <div
        className="flex items-center gap-3 px-3 py-2 hover:bg-gray-800/50 cursor-pointer"
        onClick={() => setExpanded(!expanded)}
      >
        {expanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
        <Lock size={12} className="text-red-400" />
        <span className="text-sm text-white flex-1">{item.name}</span>
        <span className="text-xs text-gray-500 font-mono">{displayValue}</span>
      </div>
      {expanded && (
        <div className="px-10 pb-3 text-xs text-gray-400">
          <p className="mb-2">{item.description}</p>
          {Array.isArray(item.value) && (
            <div className="bg-gray-800 rounded p-2 font-mono">
              {(item.value as string[]).map((v, i) => (
                <div key={i} className="text-gray-300">{v}</div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ==========================================================================
// PolicyRow Component
// ==========================================================================

interface PolicyRowProps {
  policy: PolicyItem;
  onUpdate: (name: string, value: number) => void;
}

function PolicyRow({ policy, onUpdate }: PolicyRowProps) {
  const [editing, setEditing] = useState(false);
  const [value, setValue] = useState(policy.value);

  const handleSave = () => {
    if (value >= policy.min_value && value <= policy.max_value) {
      onUpdate(policy.name, value);
      setEditing(false);
    }
  };

  const percentage = ((policy.value - policy.min_value) / (policy.max_value - policy.min_value)) * 100;

  return (
    <div className="border-b border-gray-800 last:border-0 px-3 py-3">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <Sliders size={12} className="text-yellow-400" />
          <span className="text-sm text-white">{policy.name}</span>
        </div>
        {editing ? (
          <div className="flex items-center gap-2">
            <input
              type="number"
              value={value}
              onChange={(e) => setValue(Number(e.target.value))}
              min={policy.min_value}
              max={policy.max_value}
              className="w-16 px-2 py-1 text-xs bg-gray-800 border border-gray-600 rounded text-white"
            />
            <button
              onClick={handleSave}
              className="p-1 text-green-400 hover:text-green-300"
            >
              <Save size={14} />
            </button>
            <button
              onClick={() => { setEditing(false); setValue(policy.value); }}
              className="p-1 text-gray-400 hover:text-gray-300"
            >
              <X size={14} />
            </button>
          </div>
        ) : (
          <div className="flex items-center gap-2">
            <span className="text-sm font-mono text-yellow-400">{policy.value}</span>
            <button
              onClick={() => setEditing(true)}
              className="p-1 text-gray-500 hover:text-white"
            >
              <Edit3 size={12} />
            </button>
          </div>
        )}
      </div>
      <p className="text-xs text-gray-500 mb-2">{policy.description}</p>
      <div className="flex items-center gap-2">
        <span className="text-xs text-gray-600">{policy.min_value}</span>
        <div className="flex-1 h-1.5 bg-gray-700 rounded-full overflow-hidden">
          <div
            className="h-full bg-yellow-500 transition-all"
            style={{ width: `${percentage}%` }}
          />
        </div>
        <span className="text-xs text-gray-600">{policy.max_value}</span>
      </div>
    </div>
  );
}

// ==========================================================================
// PreferenceRow Component
// ==========================================================================

interface PreferenceRowProps {
  pref: PreferenceItem;
  onUpdate: (name: string, value: unknown) => void;
}

function PreferenceRow({ pref, onUpdate }: PreferenceRowProps) {
  const [editing, setEditing] = useState(false);
  const [value, setValue] = useState(String(pref.value));

  const handleSave = () => {
    let parsed: unknown = value;
    if (value === 'true') parsed = true;
    else if (value === 'false') parsed = false;
    else if (!isNaN(Number(value))) parsed = Number(value);
    onUpdate(pref.name, parsed);
    setEditing(false);
  };

  return (
    <div className="flex items-center justify-between px-3 py-2 border-b border-gray-800 last:border-0">
      <div className="flex items-center gap-2">
        <Settings size={12} className="text-green-400" />
        <span className="text-sm text-white">{pref.name}</span>
      </div>
      {editing ? (
        <div className="flex items-center gap-2">
          <input
            type="text"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            className="w-32 px-2 py-1 text-xs bg-gray-800 border border-gray-600 rounded text-white"
          />
          <button onClick={handleSave} className="p-1 text-green-400 hover:text-green-300">
            <Save size={14} />
          </button>
          <button
            onClick={() => { setEditing(false); setValue(String(pref.value)); }}
            className="p-1 text-gray-400 hover:text-gray-300"
          >
            <X size={14} />
          </button>
        </div>
      ) : (
        <div className="flex items-center gap-2">
          <span className="text-xs font-mono text-green-400">{String(pref.value)}</span>
          <button onClick={() => setEditing(true)} className="p-1 text-gray-500 hover:text-white">
            <Edit3 size={12} />
          </button>
        </div>
      )}
    </div>
  );
}

// ==========================================================================
// RoleRow Component
// ==========================================================================

interface RoleRowProps {
  role: RolePermissions;
}

function RoleRow({ role }: RoleRowProps) {
  return (
    <div className="px-3 py-2 border-b border-gray-800 last:border-0">
      <div className="flex items-center gap-2 mb-2">
        <User size={12} className="text-blue-400" />
        <span className="text-sm font-medium text-white capitalize">{role.role}</span>
      </div>
      <div className="flex flex-wrap gap-2 text-xs">
        {role.can_approve_po_review && (
          <span className="px-2 py-0.5 bg-green-500/20 text-green-400 rounded">Approve PO</span>
        )}
        {role.can_override_guardrails && (
          <span className="px-2 py-0.5 bg-orange-500/20 text-orange-400 rounded">Override</span>
        )}
        {role.can_modify_policies && (
          <span className="px-2 py-0.5 bg-yellow-500/20 text-yellow-400 rounded">Modify Policies</span>
        )}
        {role.can_modify_invariants && (
          <span className="px-2 py-0.5 bg-red-500/20 text-red-400 rounded">Modify Invariants</span>
        )}
      </div>
    </div>
  );
}

// ==========================================================================
// LayerCard Component
// ==========================================================================

interface LayerCardProps {
  layer: typeof LAYERS[number];
  config: GuardrailsConfig;
  onUpdatePolicy: (name: string, value: number) => void;
  onUpdatePreference: (name: string, value: unknown) => void;
}

function LayerCard({ layer, config, onUpdatePolicy, onUpdatePreference }: LayerCardProps) {
  const [expanded, setExpanded] = useState(true);

  const colorClasses: Record<string, string> = {
    red: 'border-red-500/50 bg-red-500/5',
    orange: 'border-orange-500/50 bg-orange-500/5',
    yellow: 'border-yellow-500/50 bg-yellow-500/5',
    green: 'border-green-500/50 bg-green-500/5',
  };

  const iconColorClasses: Record<string, string> = {
    red: 'text-red-400',
    orange: 'text-orange-400',
    yellow: 'text-yellow-400',
    green: 'text-green-400',
  };

  const Icon = layer.icon;

  return (
    <div className={`rounded-lg border ${colorClasses[layer.color]}`}>
      {/* Header */}
      <div
        className="flex items-center gap-3 px-4 py-3 cursor-pointer"
        onClick={() => setExpanded(!expanded)}
      >
        <Icon size={16} className={iconColorClasses[layer.color]} />
        <div className="flex-1">
          <h3 className="text-sm font-medium text-white">{layer.label}</h3>
          <p className="text-xs text-gray-500">{layer.description}</p>
        </div>
        {layer.locked && <Lock size={12} className="text-gray-500" />}
        {expanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
      </div>

      {/* Content */}
      {expanded && (
        <div className="border-t border-gray-800">
          {layer.id === 'invariants' && (
            <div>
              {config.invariants.map((item) => (
                <InvariantRow key={item.name} item={item} />
              ))}
            </div>
          )}

          {layer.id === 'contracts' && (
            <div className="px-4 py-3 text-xs text-gray-500">
              <p className="mb-2">Schema validation rules for:</p>
              <ul className="list-disc list-inside space-y-1">
                <li>HandoffToken - trust_score: 0-100, signature required</li>
                <li>PipelineRun - valid stage transitions only</li>
                <li>POReviewRequest - health_score validation</li>
              </ul>
            </div>
          )}

          {layer.id === 'policies' && (
            <div>
              {config.policies.map((policy) => (
                <PolicyRow
                  key={policy.name}
                  policy={policy}
                  onUpdate={onUpdatePolicy}
                />
              ))}
            </div>
          )}

          {layer.id === 'preferences' && (
            <div>
              {config.preferences.map((pref) => (
                <PreferenceRow
                  key={pref.name}
                  pref={pref}
                  onUpdate={onUpdatePreference}
                />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ==========================================================================
// StageTransitionDiagram Component
// ==========================================================================

interface StageTransitionDiagramProps {
  transitions: StageTransitions | null;
}

function StageTransitionDiagram({ transitions }: StageTransitionDiagramProps) {
  if (!transitions) return null;

  const stageColors: Record<string, string> = {
    queued: 'bg-gray-600',
    developing: 'bg-blue-500',
    testing: 'bg-yellow-500',
    verifying: 'bg-orange-500',
    po_review: 'bg-purple-500',
    deploying: 'bg-cyan-500',
    completed: 'bg-green-500',
  };

  return (
    <div className="rounded-lg border border-gray-700 bg-gray-900 p-4">
      <h3 className="text-sm font-medium text-white mb-4 flex items-center gap-2">
        <ArrowRight size={14} />
        Stage Flow (Invariant)
      </h3>
      <div className="flex items-center gap-2 overflow-x-auto pb-2">
        {transitions.stage_order.map((stage, i) => (
          <div key={stage} className="flex items-center gap-2">
            <div
              className={`px-3 py-1.5 rounded text-xs font-medium text-white whitespace-nowrap ${stageColors[stage] || 'bg-gray-600'}`}
            >
              {stage.replace('_', ' ')}
            </div>
            {i < transitions.stage_order.length - 1 && (
              <ArrowRight size={14} className="text-gray-600 flex-shrink-0" />
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

// ==========================================================================
// ViolationsList Component
// ==========================================================================

interface ViolationsListProps {
  violations: GuardrailViolation[];
  isLoading: boolean;
}

function ViolationsList({ violations, isLoading }: ViolationsListProps) {
  if (isLoading) {
    return (
      <div className="animate-pulse space-y-3">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-16 bg-gray-800 rounded" />
        ))}
      </div>
    );
  }

  if (violations.length === 0) {
    return (
      <div className="text-center text-gray-500 text-sm py-8">
        <CheckCircle size={24} className="mx-auto mb-2 text-green-500" />
        No violations recorded
      </div>
    );
  }

  const layerColors: Record<string, string> = {
    invariant: 'text-red-400 bg-red-500/10',
    contract: 'text-orange-400 bg-orange-500/10',
    policy: 'text-yellow-400 bg-yellow-500/10',
    preference: 'text-green-400 bg-green-500/10',
  };

  return (
    <div className="space-y-2">
      {violations.map((v) => (
        <div
          key={v.id}
          className={`rounded-lg border p-3 ${
            v.blocked ? 'border-red-500/30 bg-red-500/5' : 'border-yellow-500/30 bg-yellow-500/5'
          }`}
        >
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <span className={`px-2 py-0.5 text-xs rounded ${layerColors[v.layer] || 'text-gray-400 bg-gray-500/10'}`}>
                {v.layer}
              </span>
              <span className="text-sm text-white">{v.rule_name}</span>
            </div>
            {v.blocked ? (
              <XCircle size={14} className="text-red-400" />
            ) : (
              <AlertTriangle size={14} className="text-yellow-400" />
            )}
          </div>
          <p className="text-xs text-gray-400 mb-1">{v.attempted_action}</p>
          <div className="flex items-center gap-3 text-xs text-gray-500">
            <span className="flex items-center gap-1">
              <Clock size={10} />
              {new Date(v.created_at).toLocaleString()}
            </span>
            {v.actor && (
              <span className="flex items-center gap-1">
                <User size={10} />
                {v.actor}
              </span>
            )}
          </div>
          {v.override_reason && (
            <div className="mt-2 text-xs text-yellow-400">
              Override: {v.override_reason}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

// ==========================================================================
// Main GuardrailsMonitor Component
// ==========================================================================

export default function GuardrailsMonitor() {
  const queryClient = useQueryClient();

  // Queries
  const { data: config, isLoading: configLoading, refetch: refetchConfig } = useQuery({
    queryKey: ['guardrailsConfig'],
    queryFn: fetchGuardrailsConfig,
  });

  const { data: violations = [], isLoading: violationsLoading } = useQuery({
    queryKey: ['guardrailViolations'],
    queryFn: () => fetchViolations(20),
    refetchInterval: 10000,
  });

  const { data: transitions } = useQuery({
    queryKey: ['stageTransitions'],
    queryFn: fetchStageTransitions,
  });

  // Mutations
  const updatePolicyMutation = useMutation({
    mutationFn: ({ name, value }: { name: string; value: number }) => updatePolicy(name, value),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['guardrailsConfig'] });
    },
  });

  const updatePreferenceMutation = useMutation({
    mutationFn: ({ name, value }: { name: string; value: unknown }) => updatePreference(name, value),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['guardrailsConfig'] });
    },
  });

  if (configLoading || !config) {
    return (
      <div className="min-h-screen bg-gray-950 text-white flex items-center justify-center">
        <div className="text-center">
          <RefreshCw size={24} className="mx-auto mb-2 animate-spin text-cyan-400" />
          <p className="text-gray-400">Loading guardrails configuration...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-950 text-white">
      {/* Header */}
      <div className="border-b border-gray-800 px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-gradient-to-r from-red-500 to-yellow-500">
              <Shield size={20} />
            </div>
            <div>
              <h1 className="text-lg font-bold">Guardrails Monitor</h1>
              <p className="text-xs text-gray-500">4-Layer Constraint System</p>
            </div>
          </div>

          <button
            onClick={() => refetchConfig()}
            className="p-2 rounded hover:bg-gray-800 transition-colors"
            title="Refresh"
          >
            <RefreshCw size={16} className={configLoading ? 'animate-spin' : ''} />
          </button>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex">
        {/* Left Panel - Layers */}
        <div className="flex-1 p-4 space-y-4 overflow-y-auto max-h-[calc(100vh-80px)]">
          {/* Stage Transition Diagram */}
          <StageTransitionDiagram transitions={transitions ?? null} />

          {/* Layer Cards */}
          {LAYERS.map((layer) => (
            <LayerCard
              key={layer.id}
              layer={layer}
              config={config}
              onUpdatePolicy={(name, value) => updatePolicyMutation.mutate({ name, value })}
              onUpdatePreference={(name, value) => updatePreferenceMutation.mutate({ name, value })}
            />
          ))}

          {/* Roles Section */}
          <div className="rounded-lg border border-blue-500/50 bg-blue-500/5">
            <div className="flex items-center gap-3 px-4 py-3 border-b border-gray-800">
              <User size={16} className="text-blue-400" />
              <div>
                <h3 className="text-sm font-medium text-white">Role Permissions</h3>
                <p className="text-xs text-gray-500">Access control by role</p>
              </div>
            </div>
            <div>
              {config.roles.map((role) => (
                <RoleRow key={role.role} role={role} />
              ))}
            </div>
          </div>
        </div>

        {/* Right Panel - Violations */}
        <div className="w-96 border-l border-gray-800 p-4 overflow-y-auto max-h-[calc(100vh-80px)]">
          <h3 className="text-sm font-medium text-white mb-4 flex items-center gap-2">
            <AlertTriangle size={14} className="text-red-400" />
            Recent Violations
            {violations.length > 0 && (
              <span className="px-2 py-0.5 text-xs bg-red-500/20 text-red-400 rounded-full">
                {violations.length}
              </span>
            )}
          </h3>
          <ViolationsList violations={violations} isLoading={violationsLoading} />
        </div>
      </div>
    </div>
  );
}
