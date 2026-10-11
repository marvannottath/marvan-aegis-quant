'use client';

import React, { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { useTradingContext } from '../../context/TradingContext';
import { Badge } from '../common/Badge';
import { Cpu, RefreshCw, Compass, AlertTriangle, Lock, ArrowUpRight, Activity } from 'lucide-react';

interface SignalOpportunity {
  symbol: string;
  ticker?: string;
  action: string;
  direction?: string;
  score: number;
  confidence: number;
  rr: string;
  current_price: number;
  price: number;
  entry: number;
  sl: number;
  tp: number;
  timestamp: string;
  risk_state: string;
  volatility?: string;
  fresh?: string;
  sub_agents?: Record<string, number>;
}

export function SignalsFeed() {
  const router = useRouter();
  const { workspace, environment, portfolio } = useTradingContext();
  const [opportunities, setOpportunities] = useState<SignalOpportunity[]>([]);
  const [activeModel, setActiveModel] = useState<string>('7-Agent Quantitative Ensemble');
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [lastUpdated, setLastUpdated] = useState<string>('—');
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const isFirstLoadRef = useRef<boolean>(true);

  const curr = portfolio?.currency_symbol || (workspace === 'INDIA' ? '₹' : '$');
  const isDataUnavailable = opportunities.length === 0 && !isLoading;

  const loadSignals = async (showSpinner: boolean = false) => {
    try {
      if (showSpinner) setIsLoading(true);
      setErrorMsg(null);
      const res = await fetch(`/api/state?workspace=${workspace}&environment=${environment}`);
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}: Failed to load state telemetry`);
      }
      const data = await res.json();
      const opps: SignalOpportunity[] = data.ai_opportunities || [];
      setOpportunities(opps);
      setLastUpdated(new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false }));
      if (data.risk_profile?.profile_name) {
        setActiveModel(`7-Agent Ensemble (${data.risk_profile.profile_name})`);
      }
    } catch (err: any) {
      console.error('Failed to load signals:', err);
      setErrorMsg(err?.message || 'Error querying signal pipeline');
    } finally {
      setIsLoading(false);
      isFirstLoadRef.current = false;
    }
  };

  useEffect(() => {
    loadSignals(true);
    const interval = setInterval(() => {
      loadSignals(false);
    }, 3000);
    return () => clearInterval(interval);
  }, [workspace, environment]);

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
              Active Model: <span className="font-semibold text-txt-primary">{activeModel}</span> • Min Confidence: 70%
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-emerald-50 border border-emerald-200 text-[11px] font-mono text-emerald-800">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
            <span className="font-bold">LIVE STREAMING (3s Auto-Update)</span>
            <span className="text-txt-muted text-[10px] hidden sm:inline">• {lastUpdated}</span>
          </div>

          <button
            onClick={() => loadSignals(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-md border border-line bg-slate-50 hover:bg-slate-100 text-xs font-semibold text-txt-secondary transition"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${isLoading ? 'animate-spin' : ''}`} />
            <span>Refresh Now</span>
          </button>
        </div>
      </div>

      {/* Notice if no signals available */}
      {isDataUnavailable && (
        <div className="p-3.5 rounded-lg bg-amber-50 border border-amber-200 text-amber-900 text-xs flex items-start gap-2.5">
          <Lock className="h-4 w-4 shrink-0 text-amber-600 mt-0.5" />
          <div className="space-y-0.5">
            <span className="font-bold block">{workspace} Signal Evaluation Inactive</span>
            <span className="text-[11px] text-amber-700 block">
              No quantitative opportunities currently evaluated for {workspace}. Signals require an active market feed and risk approval.
            </span>
          </div>
        </div>
      )}

      {errorMsg && (
        <div className="p-3.5 rounded-lg bg-red-50 border border-red-200 text-loss text-xs flex items-center gap-2">
          <AlertTriangle className="h-4 w-4 shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* Signals Data Grid */}
      <div className="card-panel overflow-hidden">
        <div className="px-5 py-3.5 border-b border-line bg-slate-50/50 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Compass className="h-4 w-4 text-brand" />
            <h3 className="text-xs font-bold uppercase tracking-wider text-txt-primary">
              Live Signal Pipeline ({workspace} • {environment})
            </h3>
          </div>
          <span className="text-[11px] text-txt-muted font-mono">
            {opportunities.length} Assets Tracked
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-mono">
            <thead>
              <tr className="border-b border-line bg-slate-50 text-txt-muted text-[10px] font-semibold uppercase tracking-wider">
                <th className="py-2.5 px-3">Symbol</th>
                <th className="py-2.5 px-3">Action</th>
                <th className="py-2.5 px-3 text-right">Confidence</th>
                <th className="py-2.5 px-3 text-right">Price</th>
                <th className="py-2.5 px-3 text-right">Entry Target</th>
                <th className="py-2.5 px-3 text-right">Stop Loss</th>
                <th className="py-2.5 px-3 text-right">Take Profit</th>
                <th className="py-2.5 px-3 text-center">R:R Ratio</th>
                <th className="py-2.5 px-3 text-center">Risk Gate</th>
                <th className="py-2.5 px-3 text-right">Execute / Chart</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line text-[11px]">
              {opportunities.length === 0 ? (
                <tr>
                  <td colSpan={10} className="py-12 text-center text-txt-muted font-sans">
                    {isLoading ? 'Evaluating ensemble signals...' : `No signals evaluated for ${workspace}.`}
                  </td>
                </tr>
              ) : (
                opportunities.map((opp, idx) => {
                  const isActionBuy = opp.action === 'BUY';
                  const isActionSell = opp.action === 'SELL';
                  const isDisabled = opp.action === 'DISABLED' || opp.risk_state === 'BLOCKED';
                  const targetWorkspaceRoute = workspace === 'FOREX_GOLD' ? '/forex-gold' : workspace === 'INDIA' ? '/india' : '/crypto';

                  return (
                    <tr key={`${opp.symbol}-${idx}`} className="table-row-hover">
                      <td className="py-2.5 px-3 font-bold text-txt-primary">
                        {opp.symbol}
                      </td>
                      <td className="py-2.5 px-3">
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                            isDisabled
                              ? 'bg-slate-100 text-txt-muted'
                              : isActionBuy
                              ? 'bg-emerald-50 text-profit border border-emerald-200'
                              : isActionSell
                              ? 'bg-red-50 text-loss border border-red-200'
                              : 'bg-slate-100 text-txt-secondary'
                          }`}
                        >
                          {opp.action}
                        </span>
                      </td>
                      <td className="py-2.5 px-3 text-right">
                        {isDisabled ? (
                          <span className="text-txt-muted">—</span>
                        ) : (
                          <span className="font-bold text-txt-primary">{Number(opp.confidence || opp.score).toFixed(1)}%</span>
                        )}
                      </td>
                      <td className="py-2.5 px-3 text-right text-txt-primary">
                        {isDisabled || (opp.price == null && opp.current_price == null) ? (
                          <span className="text-txt-muted">—</span>
                        ) : (
                          `${curr}${Number(opp.price ?? opp.current_price).toLocaleString('en-US', { minimumFractionDigits: 2 })}`
                        )}
                      </td>
                      <td className="py-2.5 px-3 text-right text-txt-secondary">
                        {isDisabled || opp.entry == null ? '—' : `${curr}${Number(opp.entry).toLocaleString('en-US', { minimumFractionDigits: 2 })}`}
                      </td>
                      <td className="py-2.5 px-3 text-right text-loss">
                        {isDisabled || opp.sl == null ? '—' : `${curr}${Number(opp.sl).toLocaleString('en-US', { minimumFractionDigits: 2 })}`}
                      </td>
                      <td className="py-2.5 px-3 text-right text-profit">
                        {isDisabled || opp.tp == null ? '—' : `${curr}${Number(opp.tp).toLocaleString('en-US', { minimumFractionDigits: 2 })}`}
                      </td>
                      <td className="py-2.5 px-3 text-center">
                        {isDisabled ? '—' : opp.rr || '2.33'}
                      </td>
                      <td className="py-2.5 px-3 text-center">
                        <span
                          className={`px-1.5 py-0.5 rounded text-[9px] font-black ${
                            opp.risk_state === 'APPROVED'
                              ? 'bg-emerald-50 text-profit'
                              : 'bg-amber-50 text-amber-700'
                          }`}
                        >
                          {opp.risk_state}
                        </span>
                      </td>
                      <td className="py-2.5 px-3 text-right">
                        <button
                          onClick={() => router.push(targetWorkspaceRoute)}
                          className="inline-flex items-center gap-1 px-2.5 py-1 rounded bg-accent-blue/10 text-accent-blue hover:bg-accent-blue/20 font-bold transition-colors text-[10px]"
                          title={`View ${opp.symbol} chart & trade console`}
                        >
                          Trade / Chart &rarr;
                        </button>
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
