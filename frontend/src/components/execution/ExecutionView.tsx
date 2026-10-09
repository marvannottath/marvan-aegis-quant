'use client';

import React from 'react';
import { useTradingContext } from '../../context/TradingContext';
import { QuickOrderConsole } from '../overview/QuickOrderConsole';
import { OrdersTable } from '../orders/OrdersTable';
import { Badge } from '../common/Badge';
import { ShieldCheck } from 'lucide-react';

export function ExecutionView() {
  const { environment, workspace } = useTradingContext();

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold tracking-tight text-txt-primary">
              Order Execution & Route Sentinel
            </h1>
            <Badge variant={environment === 'LIVE' ? 'live' : 'demo'}>
              {environment} SPOT GATE
            </Badge>
          </div>
          <p className="text-xs text-txt-muted mt-0.5">
            22-Gate server validation pipeline and low-latency order router for {workspace}.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1">
          <QuickOrderConsole />
        </div>
        <div className="lg:col-span-2">
          <div className="card-panel p-5 space-y-4">
            <div className="flex items-center gap-2 pb-3 border-b border-line">
              <ShieldCheck className="h-5 w-5 text-profit" />
              <h3 className="text-xs font-bold uppercase tracking-wider text-txt-primary">
                Pre-Execution Safety Verification
              </h3>
            </div>
            <div className="space-y-2 text-xs text-txt-secondary leading-relaxed">
              <p>Every order sent to the venue undergoes synchronous server evaluation:</p>
              <ul className="list-disc list-inside space-y-1 text-txt-muted">
                <li>Gate 1-5: Workspace asset boundary and security identifier matching</li>
                <li>Gate 9: Stale market data threshold rejection (&gt; 5.0 seconds)</li>
                <li>Gate 10: Server-enforced emergency kill switch verification</li>
                <li>Gate 11: LIVE trading authorization lock verification</li>
                <li>Gate 12-14: Forensic reconciliation and risk margin caps</li>
              </ul>
            </div>
          </div>
        </div>
      </div>

      <OrdersTable />
    </div>
  );
}
