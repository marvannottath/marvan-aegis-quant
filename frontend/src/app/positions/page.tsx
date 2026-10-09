'use client';

import React from 'react';
import { PositionsTable } from '../../components/positions/PositionsTable';

export default function PositionsPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-txt-primary">
            Positions Management
          </h1>
          <p className="text-xs text-txt-muted mt-0.5">
            Active open positions, mark-to-market valuations, stop-loss, and liquidation controls.
          </p>
        </div>
      </div>
      <PositionsTable />
    </div>
  );
}
