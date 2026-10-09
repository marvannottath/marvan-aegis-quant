'use client';

import React from 'react';
import { RiskDashboard } from '../../components/risk/RiskDashboard';

export default function RiskPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold tracking-tight text-txt-primary">
          Risk Center & Sentinel
        </h1>
        <p className="text-xs text-txt-muted mt-0.5">
          Real-time risk enforcement, circuit breaker thresholds, and pre-broker safety gates.
        </p>
      </div>
      <RiskDashboard />
    </div>
  );
}
