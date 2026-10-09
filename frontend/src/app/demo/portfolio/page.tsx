'use client';

import React from 'react';
import { VaultPortfolioView } from '../../../components/portfolio/VaultPortfolioView';

export default function DemoPortfolioPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold tracking-tight text-txt-primary">
          Portfolio & Segregated Vault (DEMO)
        </h1>
        <p className="text-xs text-txt-muted mt-0.5">
          Paper & Testnet balance allocation and simulated vault earnings.
        </p>
      </div>
      <VaultPortfolioView />
    </div>
  );
}
