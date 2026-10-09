'use client';

import React from 'react';
import { Lock, Shield } from 'lucide-react';

export default function SecurityPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold tracking-tight text-txt-primary">
          Security & Access Controls
        </h1>
        <p className="text-xs text-txt-muted mt-0.5">
          2FA authentication, API key sanitization, and session guard status.
        </p>
      </div>

      <div className="card-panel p-5 space-y-4">
        <div className="flex items-center gap-2 pb-3 border-b border-line">
          <Lock className="h-5 w-5 text-brand" />
          <h3 className="text-xs font-bold uppercase tracking-wider text-txt-primary">
            Session Security Status
          </h3>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs font-mono">
          <div className="p-3 bg-slate-50 rounded border border-line">
            <span className="text-txt-muted block text-[10px] uppercase">API Keys In Memory</span>
            <span className="font-bold text-txt-primary mt-1 block">Sanitized / Masked</span>
          </div>
          <div className="p-3 bg-slate-50 rounded border border-line">
            <span className="text-txt-muted block text-[10px] uppercase">Withdrawal Authority</span>
            <span className="font-bold text-loss mt-1 block">Disabled / Zero Trust</span>
          </div>
          <div className="p-3 bg-slate-50 rounded border border-line">
            <span className="text-txt-muted block text-[10px] uppercase">Rate Limiting</span>
            <span className="font-bold text-profit mt-1 block">Active (100 req/min)</span>
          </div>
        </div>
      </div>
    </div>
  );
}
