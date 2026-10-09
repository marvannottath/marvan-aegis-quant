'use client';

import React from 'react';
import { RiskDashboard } from '../../../components/risk/RiskDashboard';

export default function DemoRiskPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold tracking-tight text-txt-primary">
          Risk Center & Sentinel (DEMO)
        </h1>
        <p className="text-xs text-txt-muted mt-0.5">
          Simulated risk enforcement and testing parameters.
        </p>
      </div>
      <RiskDashboard />
    </div>
  );
}
