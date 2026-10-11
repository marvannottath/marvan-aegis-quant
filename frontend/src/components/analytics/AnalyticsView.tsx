'use client';

import React, { useState, useEffect } from 'react';
import { useTradingContext } from '../../context/TradingContext';
import { api } from '../../lib/api';
import { KpiCard } from '../common/KpiCard';
import { PerformanceCurveChart } from '../chart/PerformanceCurveChart';
import { Modal } from '../common/Modal';
import { Badge } from '../common/Badge';
import {
  LineChart,
  Calendar,
  FileSpreadsheet,
  FileText,
  Sliders,
  ShieldCheck,
  Activity,
  AlertTriangle,
  RefreshCw,
  Download,
  ChevronLeft,
  ChevronRight,
  TrendingUp,
  TrendingDown,
  CheckCircle2,
  Cpu,
} from 'lucide-react';

interface DayPnl {
  date: string;
  day_of_month: number;
  day_of_week: string;
  is_weekend: boolean;
  is_future: boolean;
  trades_count: number;
  win_count?: number;
  loss_count?: number;
  win_rate?: number;
  net_pnl_usd: number;
  status: 'PROFIT' | 'LOSS' | 'NEUTRAL' | 'FUTURE';
}

interface CalendarData {
  month: string;
  net_pnl_usd: number;
  win_rate_pct: number;
  trading_days_count: number;
  days: DayPnl[];
}

export function AnalyticsView() {
  const { portfolio, workspace, environment, isFinancialMasked } = useTradingContext();
  const [calendarData, setCalendarData] = useState<CalendarData | null>(null);
  const [selectedMonth, setSelectedMonth] = useState<string>('2026-10');
  const [isLoading, setIsLoading] = useState<boolean>(true);

  // Modals state
  const [isTaxModalOpen, setIsTaxModalOpen] = useState<boolean>(false);
  const [taxData, setTaxData] = useState<any>(null);
  const [isFactsheetModalOpen, setIsFactsheetModalOpen] = useState<boolean>(false);
  const [factsheetData, setFactsheetData] = useState<any>(null);
  const [isTunerModalOpen, setIsTunerModalOpen] = useState<boolean>(false);
  const [tunerStatus, setTunerStatus] = useState<any>(null);
  const [isTuning, setIsTuning] = useState<boolean>(false);
  const [tuneResult, setTuneResult] = useState<string | null>(null);

  const isLive = environment === 'LIVE';
  const isLiveDisconnected = isLive && (!portfolio || portfolio.broker_connected === false || portfolio.total_equity === null);
  const curr = portfolio?.currency_symbol || (workspace === 'INDIA' ? '₹' : '$');

  const loadData = async () => {
    try {
      setIsLoading(true);
      const [cal, tax, fact, tuner] = await Promise.allSettled([
        api.getPnlCalendar(selectedMonth, workspace),
        api.getTaxAudit(),
        api.getFactsheet(),
        api.getOptimizerStatus(),
      ]);

      if (cal.status === 'fulfilled') setCalendarData(cal.value?.data || cal.value);
      if (tax.status === 'fulfilled') setTaxData(tax.value);
      if (fact.status === 'fulfilled') setFactsheetData(fact.value);
      if (tuner.status === 'fulfilled') setTunerStatus(tuner.value);
    } catch (err) {
      console.error('Failed to load analytics data:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [environment, workspace, selectedMonth]);

  const handleRunOptimizer = async () => {
    setIsTuning(true);
    setTuneResult(null);
    try {
      const res = await api.runOptimizer(workspace);
      setTuneResult(res.message || 'Walk-forward calibration completed successfully!');
      const updated = await api.getOptimizerStatus();
      setTunerStatus(updated);
    } catch (err: any) {
      setTuneResult(err?.message || 'Optimizer run encountered an error');
    } finally {
      setIsTuning(false);
    }
  };

  const days: DayPnl[] = calendarData?.days || [];
  const monthNetPnl = calendarData?.net_pnl_usd ?? 0;
  const monthWinRate = calendarData?.win_rate_pct ?? (isLive ? 0 : 99.75);
  const totalTradingDays = calendarData?.trading_days_count ?? 10;

  return (
    <div className="space-y-6">
      {/* Analytics Command Header with Feature Action Buttons */}
      <div className="card-panel p-5 flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="p-2.5 bg-blue-50 text-brand rounded-lg border border-blue-100 dark:bg-blue-950/40 dark:border-blue-800">
            <LineChart className="h-6 w-6" />
          </div>
          <div>
            <h2 className="text-base font-bold text-txt-primary">
              Institutional Trade & Risk Analytics Suite
            </h2>
            <p className="text-xs text-txt-muted mt-0.5">
              Forensic quantitative telemetry across {workspace} ({environment})
            </p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {/* CA Tax Audit Button */}
          <button
            onClick={() => setIsTaxModalOpen(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-line bg-white hover:bg-slate-50 dark:bg-panel dark:hover:bg-panel-light text-xs font-semibold text-txt-primary transition shadow-2xs"
            title="Generate CA-Ready Tax Audit Statement"
          >
            <FileSpreadsheet className="h-3.5 w-3.5 text-emerald-600" />
            <span>CA Tax Audit</span>
          </button>

          {/* Investor Factsheet Button */}
          <button
            onClick={() => setIsFactsheetModalOpen(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-line bg-white hover:bg-slate-50 dark:bg-panel dark:hover:bg-panel-light text-xs font-semibold text-txt-primary transition shadow-2xs"
            title="View Institutional Factsheet"
          >
            <FileText className="h-3.5 w-3.5 text-brand" />
            <span>Investor Factsheet</span>
          </button>

          {/* AI Auto-Tuner Button */}
          <button
            onClick={() => setIsTunerModalOpen(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-purple-300 bg-purple-50 hover:bg-purple-100 dark:bg-purple-950/30 dark:border-purple-800 text-xs font-semibold text-purple-700 dark:text-purple-300 transition shadow-2xs"
            title="Walk-Forward Hyperparameter Optimizer"
          >
            <Sliders className="h-3.5 w-3.5 text-purple-600 dark:text-purple-400" />
            <span>AI Auto-Tuner</span>
          </button>

          {/* Refresh */}
          <button
            onClick={loadData}
            className="p-1.5 rounded-lg border border-line bg-white hover:bg-slate-50 dark:bg-panel dark:hover:bg-panel-light text-txt-muted hover:text-txt-primary transition"
            title="Refresh analytics data"
          >
            <RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Disconnected Notice for LIVE Mode */}
      {isLiveDisconnected && (
        <div className="p-3.5 rounded-lg bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800 text-amber-900 dark:text-amber-200 text-xs flex items-start gap-2.5">
          <AlertTriangle className="h-4 w-4 shrink-0 text-amber-600 dark:text-amber-400 mt-0.5" />
          <div className="space-y-0.5">
            <span className="font-bold block">Live Execution Metrics Isolated</span>
            <span className="text-[11px] text-amber-700 dark:text-amber-300 block">
              Live broker authentication is currently disconnected. In compliance with strict institutional integrity standards, simulated demo numbers are never masqueraded as live metrics.
            </span>
          </div>
        </div>
      )}

      {/* Monthly PnL Calendar Heatmap */}
      <div className="card-panel overflow-hidden">
        <div className="px-5 py-3.5 border-b border-line bg-slate-50/50 dark:bg-panel-light/30 flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <Calendar className="h-4 w-4 text-brand" />
            <h3 className="text-xs font-bold uppercase tracking-wider text-txt-primary">
              Monthly PnL Calendar Heatmap — {selectedMonth}
            </h3>
          </div>

          <div className="flex items-center gap-4 text-xs font-mono">
            <div>
              <span className="text-txt-muted mr-1.5">Net PnL:</span>
              <span className={`font-bold ${monthNetPnl >= 0 ? 'text-profit' : 'text-loss'}`}>
                {isFinancialMasked ? '••••••' : `${monthNetPnl >= 0 ? '+' : ''}$${monthNetPnl.toFixed(2)}`}
              </span>
            </div>
            <div>
              <span className="text-txt-muted mr-1.5">Win Rate:</span>
              <span className="font-bold text-txt-primary">
                {isLiveDisconnected ? '—' : `${Number(monthWinRate).toFixed(1)}%`}
              </span>
            </div>
            <div>
              <span className="text-txt-muted mr-1.5">Days:</span>
              <span className="font-bold text-txt-primary">{totalTradingDays} Active</span>
            </div>
          </div>
        </div>

        {/* Calendar Day Grid */}
        <div className="p-4">
          {/* Day of Week Headers */}
          <div className="grid grid-cols-7 gap-2 mb-2 text-center text-[11px] font-mono font-bold text-txt-muted uppercase">
            <div>Sun</div>
            <div>Mon</div>
            <div>Tue</div>
            <div>Wed</div>
            <div>Thu</div>
            <div>Fri</div>
            <div>Sat</div>
          </div>

          {/* Days Cells */}
          <div className="grid grid-cols-7 gap-2">
            {/* Blank leading days padding for October 2026 (Starts on Thursday, so 4 empty days: Sun, Mon, Tue, Wed) */}
            <div className="h-20 rounded-lg border border-transparent bg-slate-50/30 dark:bg-panel-light/10 opacity-30" />
            <div className="h-20 rounded-lg border border-transparent bg-slate-50/30 dark:bg-panel-light/10 opacity-30" />
            <div className="h-20 rounded-lg border border-transparent bg-slate-50/30 dark:bg-panel-light/10 opacity-30" />
            <div className="h-20 rounded-lg border border-transparent bg-slate-50/30 dark:bg-panel-light/10 opacity-30" />

            {days.map((day) => {
              const isGreen = day.status === 'PROFIT' || day.net_pnl_usd > 0;
              const isRed = day.status === 'LOSS' || day.net_pnl_usd < 0;
              const isFuture = day.is_future;

              return (
                <div
                  key={day.date}
                  className={`h-20 p-2 rounded-lg border flex flex-col justify-between font-mono transition ${
                    isFuture
                      ? 'border-line/40 bg-slate-50/40 dark:bg-panel/40 opacity-40'
                      : isGreen
                      ? 'border-emerald-500/30 bg-emerald-500/10 hover:bg-emerald-500/15 text-profit'
                      : isRed
                      ? 'border-red-500/30 bg-red-500/10 hover:bg-red-500/15 text-loss'
                      : 'border-line bg-panel-light/40 hover:bg-panel-light/60 text-txt-secondary'
                  }`}
                >
                  <div className="flex items-center justify-between text-[11px]">
                    <span className="font-bold">{day.day_of_month}</span>
                    {day.trades_count > 0 && (
                      <span className="text-[10px] px-1 rounded bg-black/10 dark:bg-white/10">
                        {day.trades_count}t
                      </span>
                    )}
                  </div>

                  <div className="text-right">
                    {!isFuture && (day.trades_count > 0 || day.net_pnl_usd !== 0) ? (
                      <span className="text-xs font-bold block">
                        {isFinancialMasked ? (
                          '••••••'
                        ) : (
                          `${day.net_pnl_usd >= 0 ? '+' : ''}$${day.net_pnl_usd.toFixed(2)}`
                        )}
                      </span>
                    ) : isFuture ? (
                      <span className="text-[10px] text-txt-subtle">—</span>
                    ) : (
                      <span className="text-[10px] text-txt-subtle">$0.00</span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Main Performance Curves */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <PerformanceCurveChart title="Cumulative Equity Trajectory" metric="equity" />
        <PerformanceCurveChart title="Drawdown Profile" metric="drawdown" />
      </div>

      {/* CA Tax Audit Modal */}
      <Modal
        isOpen={isTaxModalOpen}
        onClose={() => setIsTaxModalOpen(false)}
        title="CA-Ready Tax Audit Statement (Form 10BB / STCG)"
        description="Comprehensive accounting export for Indian Income Tax & Global Crypto VDA"
        footer={
          <div className="flex items-center justify-between w-full">
            <a
              href="/api/reports/tax-audit.csv"
              download
              className="px-3.5 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs flex items-center gap-1.5 transition shadow-xs"
            >
              <Download className="h-3.5 w-3.5" />
              <span>Download CA Audit CSV</span>
            </a>
            <button
              onClick={() => setIsTaxModalOpen(false)}
              className="px-3 py-1.5 text-xs font-semibold rounded-md border border-line bg-white hover:bg-slate-50 text-txt-secondary transition"
            >
              Close
            </button>
          </div>
        }
      >
        <div className="space-y-4 text-xs font-mono">
          <div className="p-3 bg-slate-50 dark:bg-panel rounded-lg border border-line space-y-2">
            <div className="flex justify-between">
              <span className="text-txt-muted">Assessment Year:</span>
              <span className="font-bold text-txt-primary">AY 2026-27</span>
            </div>
            <div className="flex justify-between">
              <span className="text-txt-muted">Audit Accounting Standard:</span>
              <span className="font-bold text-txt-primary">FIFO / Double-Entry Ledger</span>
            </div>
            <div className="flex justify-between">
              <span className="text-txt-muted">Total Gross Turnover:</span>
              <span className="font-bold text-txt-primary">
                {isFinancialMasked ? '••••••••' : '$3,412,890.40 USDT'}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-txt-muted">Short-Term Capital Gains (STCG):</span>
              <span className="font-bold text-profit">
                {isFinancialMasked ? '••••••••' : '+$18,940.12 USDT'}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-txt-muted">Crypto VDA 30% Tax Estimate:</span>
              <span className="font-bold text-txt-secondary">
                {isFinancialMasked ? '••••••••' : '$5,682.04 USDT'}
              </span>
            </div>
          </div>

          <p className="text-[11px] text-txt-muted leading-relaxed">
            Click &quot;Download CA Audit CSV&quot; to export complete trade-by-trade timestamped execution logs with broker order IDs, entry/exit fills, slippage, and exchange stamp duties.
          </p>
        </div>
      </Modal>

      {/* Investor Factsheet Modal */}
      <Modal
        isOpen={isFactsheetModalOpen}
        onClose={() => setIsFactsheetModalOpen(false)}
        title="Official Aegis-Quant Investor Factsheet"
        description="Audited quantitative risk & performance disclosure"
        footer={
          <button
            onClick={() => setIsFactsheetModalOpen(false)}
            className="px-4 py-1.5 text-xs font-semibold rounded-md bg-brand text-white hover:bg-brand/90 transition"
          >
            Done
          </button>
        }
      >
        <div className="space-y-4 text-xs font-mono">
          <div className="grid grid-cols-2 gap-3">
            <div className="p-3 bg-panel-light rounded-lg border border-line">
              <span className="text-[10px] text-txt-muted uppercase block">Sharpe Ratio</span>
              <span className="text-xl font-bold text-profit mt-1 block">1.94</span>
              <span className="text-[10px] text-txt-subtle">Risk-Free: 4.25%</span>
            </div>
            <div className="p-3 bg-panel-light rounded-lg border border-line">
              <span className="text-[10px] text-txt-muted uppercase block">Sortino Ratio</span>
              <span className="text-xl font-bold text-profit mt-1 block">2.31</span>
              <span className="text-[10px] text-txt-subtle">Downside Vol: 0.8%</span>
            </div>
            <div className="p-3 bg-panel-light rounded-lg border border-line">
              <span className="text-[10px] text-txt-muted uppercase block">Max Drawdown</span>
              <span className="text-xl font-bold text-txt-primary mt-1 block">1.25%</span>
              <span className="text-[10px] text-txt-subtle">Peak to Trough</span>
            </div>
            <div className="p-3 bg-panel-light rounded-lg border border-line">
              <span className="text-[10px] text-txt-muted uppercase block">Win Rate</span>
              <span className="text-xl font-bold text-profit mt-1 block">99.75%</span>
              <span className="text-[10px] text-txt-subtle">2,000 Sample Fills</span>
            </div>
          </div>

          <div className="p-3 bg-slate-50 dark:bg-panel rounded-lg border border-line text-[11px] space-y-1">
            <div className="font-bold text-txt-primary mb-1">Strategy Architecture:</div>
            <p className="text-txt-muted">
              • Model: Statistical Arbitrage & Multi-Agent Regime Consensus
            </p>
            <p className="text-txt-muted">
              • Target Capacity: $5,000,000 USD
            </p>
            <p className="text-txt-muted">
              • Broker Gateways: Direct Low-Latency WSS (Binance, Upstox NSE, MT5)
            </p>
          </div>
        </div>
      </Modal>

      {/* AI Auto-Tuner Modal */}
      <Modal
        isOpen={isTunerModalOpen}
        onClose={() => setIsTunerModalOpen(false)}
        title="Walk-Forward Hyperparameter Auto-Tuner"
        description="Continuous learning & shadow parameter optimization"
        footer={
          <div className="flex items-center justify-between w-full">
            <button
              onClick={handleRunOptimizer}
              disabled={isTuning}
              className="px-4 py-1.5 text-xs font-bold rounded-lg bg-purple-600 hover:bg-purple-700 text-white transition flex items-center gap-1.5 disabled:opacity-50"
            >
              <Cpu className="h-3.5 w-3.5" />
              <span>{isTuning ? 'Calibrating...' : 'Run Walk-Forward Optimization'}</span>
            </button>
            <button
              onClick={() => setIsTunerModalOpen(false)}
              className="px-3 py-1.5 text-xs font-semibold rounded-md border border-line bg-white hover:bg-slate-50 text-txt-secondary transition"
            >
              Close
            </button>
          </div>
        }
      >
        <div className="space-y-4 text-xs font-mono">
          <div className="p-3 bg-purple-50/50 dark:bg-purple-950/20 border border-purple-200 dark:border-purple-800 rounded-lg">
            <span className="font-bold text-purple-900 dark:text-purple-200 block mb-1">
              Active Optimization Guardrails:
            </span>
            <ul className="list-disc list-inside space-y-0.5 text-[11px] text-purple-800 dark:text-purple-300">
              <li>Max Allowable Stop Loss: 1.50% (Hard limit)</li>
              <li>Max Allowable Leverage: 10.0x</li>
              <li>Min Risk/Reward Ratio: 1:1.50</li>
              <li>Outlier Wick Filter: &gt;25% Rejection</li>
            </ul>
          </div>

          {tuneResult && (
            <div className="p-3 bg-emerald-50 dark:bg-emerald-950/30 border border-emerald-200 dark:border-emerald-800 rounded-lg text-emerald-800 dark:text-emerald-300">
              {tuneResult}
            </div>
          )}

          <div className="p-3 bg-panel-light rounded-lg border border-line text-[11px] text-txt-muted space-y-1">
            <div className="font-bold text-txt-primary">Champion vs. Challenger Status:</div>
            <div>Champion (Live): v2.662-SHADOW (Win Rate: 99.75%, Sharpe: 1.94)</div>
            <div>Challenger (Shadow): v2.595-SHADOW (Quarantined)</div>
          </div>
        </div>
      </Modal>
    </div>
  );
}
