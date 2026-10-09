'use client';

import React from 'react';
import { VaultPortfolioView } from '../../components/portfolio/VaultPortfolioView';

export default function PortfolioPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold tracking-tight text-txt-primary">
          Portfolio & Segregated Vault
        </h1>
        <p className="text-xs text-txt-muted mt-0.5">
          9-bucket balance model, cash availability, and profit vault sweeps.
        </p>
      </div>
      <VaultPortfolioView />
    </div>
  );
}
