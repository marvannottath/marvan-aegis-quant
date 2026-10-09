'use client';

import React from 'react';
import { FileText, Download } from 'lucide-react';

export default function ReportsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold tracking-tight text-txt-primary">
          Regulatory Reports & Statement Exports
        </h1>
        <p className="text-xs text-txt-muted mt-0.5">
          Download certified CSV trade logs, daily statements, and tax audit summaries.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="card-panel p-4 flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-2">
              <FileText className="h-4 w-4 text-brand" />
              <h3 className="text-xs font-bold text-txt-primary uppercase">Trade Activity (CSV)</h3>
            </div>
            <p className="text-xs text-txt-muted mt-1">Full chronological execution fill logs.</p>
          </div>
          <a
            href="/api/reports/trades.csv"
            download
            className="mt-4 flex items-center justify-center gap-1.5 py-1.5 px-3 rounded bg-slate-900 text-white text-xs font-semibold hover:bg-slate-800 transition"
          >
            <Download className="h-3.5 w-3.5" />
            <span>Download CSV</span>
          </a>
        </div>

        <div className="card-panel p-4 flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-2">
              <FileText className="h-4 w-4 text-brand" />
              <h3 className="text-xs font-bold text-txt-primary uppercase">Tax Audit Statement</h3>
            </div>
            <p className="text-xs text-txt-muted mt-1">Realized capital gains and fee deductions.</p>
          </div>
          <a
            href="/api/reports/tax-audit.csv"
            download
            className="mt-4 flex items-center justify-center gap-1.5 py-1.5 px-3 rounded bg-slate-900 text-white text-xs font-semibold hover:bg-slate-800 transition"
          >
            <Download className="h-3.5 w-3.5" />
            <span>Download CSV</span>
          </a>
        </div>

        <div className="card-panel p-4 flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-2">
              <FileText className="h-4 w-4 text-brand" />
              <h3 className="text-xs font-bold text-txt-primary uppercase">Performance Factsheet</h3>
            </div>
            <p className="text-xs text-txt-muted mt-1">Institutional summary of Sharpe, PnL & drawdowns.</p>
          </div>
          <a
            href="/api/reports/factsheet"
            target="_blank"
            className="mt-4 flex items-center justify-center gap-1.5 py-1.5 px-3 rounded bg-slate-900 text-white text-xs font-semibold hover:bg-slate-800 transition"
          >
            <Download className="h-3.5 w-3.5" />
            <span>View Factsheet</span>
          </a>
        </div>
      </div>
    </div>
  );
}
