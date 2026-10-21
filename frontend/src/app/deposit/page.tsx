'use client';

import React from 'react';
import { DepositView } from '../../components/deposit/DepositView';

export default function DepositPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-txt-primary">
            Deposit Hub & Transaction History
          </h1>
          <p className="text-xs text-txt-muted mt-0.5">
            Fund your live trading pool via Cards, Apple Pay, Google Pay, UPI & Binance Pay with full ledger tracking.
          </p>
        </div>
      </div>
      <DepositView />
    </div>
  );
}
