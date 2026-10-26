'use client';

import React from 'react';
import { useTradingContext } from '../../context/TradingContext';
import { Sparkles, Quote, RefreshCw } from 'lucide-react';

export function MarketTransitionLoader() {
  const { isMarketTransitioning, transitionTargetWs, motivationalThought } = useTradingContext();

  if (!isMarketTransitioning) return null;

  const marketNames: Record<string, string> = {
    CRYPTO: 'Crypto Spot (Binance)',
    INDIA: 'Indian Equities (NSE Cash)',
    FOREX_GOLD: 'Forex & Gold (Interbank)',
  };

  const wsName = transitionTargetWs ? marketNames[transitionTargetWs] || transitionTargetWs : 'Market Engine';

  return (
    <div className="fixed top-16 left-1/2 -translate-x-1/2 z-50 animate-in fade-in slide-in-from-top-3 duration-200 pointer-events-none select-none max-w-xl w-[92%] sm:w-auto">
      <div className="flex items-center gap-3 px-4 py-2.5 rounded-2xl bg-panel/95 backdrop-blur-xl border border-brand/40 shadow-2xl shadow-blue-500/20 text-xs">
        {/* Animated Radar Pulse */}
        <div className="relative flex items-center justify-center shrink-0">
          <span className="animate-ping absolute inline-flex h-5 w-5 rounded-full bg-brand opacity-60"></span>
          <div className="h-7 w-7 rounded-full bg-brand text-white flex items-center justify-center shadow-xs">
            <RefreshCw className="h-3.5 w-3.5 animate-spin" />
          </div>
        </div>

        {/* Content */}
        <div className="flex flex-col min-w-0 pr-1">
          <div className="flex items-center gap-1.5">
            <span className="font-bold text-txt-primary uppercase tracking-wider text-[11px] flex items-center gap-1">
              <Sparkles className="h-3 w-3 text-amber-500" />
              <span>Connecting {wsName}</span>
            </span>
            <span className="text-[10px] font-mono text-txt-muted">• Calibrating Telemetry</span>
          </div>
          <div className="flex items-center gap-1 text-[11px] text-txt-secondary italic mt-0.5 font-medium truncate">
            <Quote className="h-2.5 w-2.5 shrink-0 text-brand opacity-75 inline" />
            <span className="truncate">“{motivationalThought}”</span>
          </div>
        </div>
      </div>
    </div>
  );
}
