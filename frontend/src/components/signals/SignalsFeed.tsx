'use client';

import React, { useState, useEffect } from 'react';
import { useTradingContext } from '../../context/TradingContext';
import { AISignal } from '../../lib/types';
import { api } from '../../lib/api';
import { Badge } from '../common/Badge';
import { Cpu, RefreshCw, ArrowUpRight, ArrowDownRight, Compass } from 'lucide-react';

export function SignalsFeed() {
  const { workspace, portfolio } = useTradingContext();
  const [signals, setSignals] = useState<AISignal[]>([]);
  const [aiInfo, setAiInfo] = useState<any>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const curr = portfolio?.currency_symbol || '$';

  const loadSignals = async () => {
    try {
      setIsLoading(true);
      const res = await api.getAiStatus();
      setAiInfo(res);
      setSignals(res.signals || []);
    } catch (err) {
      console.error('Failed to load AI signals:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadSignals();
  }, [workspace]);

  return (
    <div className="space-y-6">
      {/* Header & Model Regime Card */}
      <div className="card-panel p-5 flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="p-2.5 bg-blue-50 text-brand rounded-lg border border-blue-100">
            <Cpu className="h-6 w-6" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-base font-bold text-txt-primary">
                Multi-Model Quantitative Signals
              </h2>
              <Badge variant="info">Ensemble v4.2</Badge>
            </div>
            <p className="text-xs text-txt-muted mt-0.5">
              Active Model: <span className="font-semibold text-txt-primary">{aiInfo?.active_model || 'Deep Ensemble Transformer'}</span> • Confidence Threshold: 70%
            </p>
          </div>
        </div>

        <button
          onClick={loadSignals}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-md border border-line bg-slate-50 hover:bg-slate-100 text-xs font-semibold text-txt-secondary transition"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${isLoading ? 'animate-spin' : ''}`} />
          <span>Refresh Signals</span>
        </button>
      </div>

      {/* Signals Data Grid */}
      <div className="card-panel overflow-hidden">
        <div className="px-5 py-3.5 border-b border-line bg-slate-50/50 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Compass className="h-4 w-4 text-brand" />
            <h3 className="text-xs font-bold uppercase tracking-wider text-txt-primary">
              Live Signal Pipeline
            </h3>
          </div>
          <span className="text-[11px] text-txt-muted font-mono">
            {signals.length} Signals Evaluated
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-line bg-slate-50 text-txt-muted text-[11px] font-semibold uppercase tracking-wider">
                <th className="py-2.5 px-3">Symbol</th>
                <th className="py-2.5 px-3">Action</th>
                <th className="py-2.5 px-3 text-right">Confidence</th>
                <th className="py-2.5 px-3">Model Engine</th>
                <th className="py-2.5 px-3">Market Regime</th>
                <th className="py-2.5 px-3 text-right">Entry Target</th>
                <th className="py-2.5 px-3 text-right">Stop Loss</th>
                <th className="py-2.5 px-3 text-right">Take Profit</th>
                <th className="py-2.5 px-3 text-center">R:R Ratio</th>
                <th className="py-2.5 px-3 text-center">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {signals.length === 0 ? (
                <tr>
                  <td colSpan={10} className="py-12 text-center text-txt-muted">
                    <div className="flex flex-col items-center justify-center gap-1.5">
                      <Cpu className="h-8 w-8 text-txt-subtle stroke-[1.5]" />
                      <span className="font-medium text-xs">No active signals meeting confidence threshold</span>
                      <span className="text-[11px] text-txt-subtle">
                        High-conviction algorithmic setups appear here as market conditions align.
                      </span>
                    </div>
                  </td>
                </tr>
              ) : (
                signals.map((sig) => {
                  const isBuy = sig.action === 'BUY';
                  return (
                    <tr key={sig.signal_id} className="table-row-hover">
                      <td className="py-2.5 px-3 font-mono font-semibold text-txt-primary">
                        {sig.symbol}
                      </td>
                      <td className="py-2.5 px-3">
                        <Badge variant={isBuy ? 'success' : 'danger'} size="sm">
                          {sig.action}
                        </Badge>
                      </td>
                      <td className="py-2.5 px-3 text-right font-mono font-semibold text-txt-primary">
                        {(sig.confidence * 100).toFixed(1)}%
                      </td>
                      <td className="py-2.5 px-3 text-txt-secondary font-medium">
                        {sig.model || 'Ensemble'}
                      </td>
                      <td className="py-2.5 px-3">
                        <Badge variant="neutral" size="sm">
                          {sig.market_regime || 'TRENDING'}
                        </Badge>
                      </td>
                      <td className="py-2.5 px-3 text-right font-mono tabular-nums text-txt-secondary">
                        {curr}{Number(sig.entry_price).toFixed(2)}
                      </td>
                      <td className="py-2.5 px-3 text-right font-mono tabular-nums text-loss font-semibold">
                        {curr}{Number(sig.stop_loss).toFixed(2)}
                      </td>
                      <td className="py-2.5 px-3 text-right font-mono tabular-nums text-profit font-semibold">
                        {curr}{Number(sig.take_profit).toFixed(2)}
                      </td>
                      <td className="py-2.5 px-3 text-center font-mono font-semibold text-txt-primary">
                        {sig.risk_reward_ratio ? `1:${sig.risk_reward_ratio.toFixed(1)}` : '1:2.5'}
                      </td>
                      <td className="py-2.5 px-3 text-center">
                        <Badge variant="info" size="sm">
                          {sig.status || 'ACTIVE'}
                        </Badge>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
