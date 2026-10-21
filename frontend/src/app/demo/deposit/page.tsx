'use client';

import React from 'react';
import { DepositView } from '../../../components/deposit/DepositView';

export default function DemoDepositPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-txt-primary">
            Deposit Hub & Transaction History (DEMO)
          </h1>
          <p className="text-xs text-txt-muted mt-0.5">
            Simulated test deposit gateway and virtual allocation ledger.
          </p>
        </div>
      </div>
      <DepositView />
    </div>
  );
}
