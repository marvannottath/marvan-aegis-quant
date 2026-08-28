'use client';

import React from 'react';
import { AlertTriangle } from 'lucide-react';

interface CircuitBreakerProps {
  tripped: boolean;
  reason: string;
  onReset: () => void;
}

export const CircuitBreakerBanner: React.FC<CircuitBreakerProps> = ({ tripped, reason, onReset }) => {
  if (!tripped) return null;

  return (
    <div className="bg-red-950/90 border border-red-500/50 p-3.5 md:p-4 rounded-xl flex items-center justify-between text-red-200 shadow-xl">
      <div className="flex items-center space-x-3">
        <AlertTriangle className="w-6 h-6 text-red-400 animate-bounce flex-shrink-0" />
        <div>
          <h3 className="font-bold text-xs md:text-sm">CIRCUIT BREAKER ACTIVATED</h3>
          <p className="text-[11px] md:text-xs text-red-300">{reason}</p>
        </div>
      </div>
      <button
        onClick={onReset}
        className="bg-red-600 hover:bg-red-500 active:scale-95 text-white px-3 py-1.5 rounded-lg text-xs font-bold transition flex-shrink-0"
      >
        Reset Lock
      </button>
    </div>
  );
};
