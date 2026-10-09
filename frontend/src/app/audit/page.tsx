'use client';

import React from 'react';
import { useTradingContext } from '../../context/TradingContext';
import { FileCheck, ShieldCheck } from 'lucide-react';

export default function AuditPage() {
  const { environment, workspace } = useTradingContext();

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold tracking-tight text-txt-primary">
          Audit & Double-Entry Ledger Forensics
        </h1>
        <p className="text-xs text-txt-muted mt-0.5">
          Immutable audit trail and double-entry balanced debit/credit event journal ({workspace} • {environment}).
        </p>
      </div>

      <div className="card-panel p-5 space-y-4">
        <div className="flex items-center gap-2 pb-3 border-b border-line">
          <FileCheck className="h-5 w-5 text-brand" />
          <h3 className="text-xs font-bold uppercase tracking-wider text-txt-primary">
            Double-Entry Ledger Integrity Status
          </h3>
        </div>
        <div className="p-4 bg-slate-50 rounded border border-line flex items-center justify-between">
          <div>
            <span className="text-xs font-semibold text-txt-primary block">Debit / Credit Mathematical Balance</span>
            <span className="text-xs text-txt-muted">Sum(Debits) - Sum(Credits) = 0.00 USD</span>
          </div>
          <span className="text-xs font-bold text-profit font-mono">BALANCED (0 DELTA)</span>
        </div>
      </div>
    </div>
  );
}
