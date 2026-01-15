/**
 * CC Sessions Page (EPOCH 8)
 * ==========================
 *
 * Page wrapper for the CC Session Viewer component.
 */

import { CCSessionViewer } from '../components';

export default function CCSessions() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-900 to-slate-800">
      <div className="max-w-7xl mx-auto px-6 py-8">
        <CCSessionViewer />
      </div>
    </div>
  );
}
