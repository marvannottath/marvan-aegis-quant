'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { useSearchParams, useRouter } from 'next/navigation';
import { useTradingContext } from '../../context/TradingContext';
import { api } from '../../lib/api';
import {
  ArrowLeft,
  ChevronLeft,
  ChevronRight,
  Calendar as CalendarIcon,
  Search,
  Filter,
  TrendingUp,
  TrendingDown,
  DollarSign,
  Activity,
  Award,
  Shield,
  Layers,
  ArrowUpRight,
  ArrowDownRight,
  RefreshCw,
} from 'lucide-react';
import { Badge } from '../common/Badge';

export function SessionDetailView() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const { workspace, environment, isFinancialMasked } = useTradingContext();

  const todayStr = new Date().toISOString().slice(0, 10);
  const initialDate = searchParams?.get('date') || todayStr;

  const [currentDate, setCurrentDate] = useState<string>(initialDate);
  const [sessionData, setSessionData] = useState<any>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<'ALL' | 'WIN' | 'LOSS'>('ALL');

  const curr = workspace === 'INDIA' ? '₹' : '$';
  const calendarBackUrl = environment === 'LIVE' ? '/analytics' : '/demo/analytics';

  const loadSessionTrades = async (dateStr: string) => {
    setIsLoading(true);
    try {
      const monthStr = dateStr.slice(0, 7);
      const res = await api.getPnlCalendar(monthStr, workspace, environment);
      const cal = res?.data || res;
      const days = cal?.days || [];
      const matchDay = days.find((d: any) => d.date === dateStr);

      if (matchDay) {
        setSessionData(matchDay);
      } else {
        setSessionData({
          date: dateStr,
          trades_count: 0,
          net_pnl_usd: 0.0,
          win_rate: 0.0,
          win_count: 0,
          loss_count: 0,
          trades: [],
        });
      }
    } catch (e) {
      console.error('Failed to load session trades:', e);
      setSessionData({
        date: dateStr,
        trades_count: 0,
        net_pnl_usd: 0.0,
        win_rate: 0.0,
        win_count: 0,
        loss_count: 0,
        trades: [],
      });
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    const urlDate = searchParams?.get('date');
    if (urlDate && urlDate !== currentDate) {
      setCurrentDate(urlDate);
    }
  }, [searchParams]);

  useEffect(() => {
    loadSessionTrades(currentDate);
  }, [currentDate, workspace, environment]);

  const changeDateByOffset = (daysOffset: number) => {
    try {
      const d = new Date(currentDate);
      d.setDate(d.getDate() + daysOffset);
      const nextDateStr = d.toISOString().slice(0, 10);
      setCurrentDate(nextDateStr);
      router.push(`?date=${nextDateStr}`);
    } catch {
      // ignore
    }
  };

  const handleDateInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    if (val) {
      setCurrentDate(val);
      router.push(`?date=${val}`);
    }
  };

  const trades = sessionData?.trades || [];
  const netPnl = sessionData?.net_pnl_usd ?? 0.0;
  const isNetProfit = netPnl >= 0;

  // Compute breakdown metrics
  const totalTradesCount = sessionData?.trades_count ?? trades.length;
  const winCount = trades.filter((t: any) => (t.net_pnl ?? t.pnl_usd ?? 0) > 0).length;
  const lossCount = trades.filter((t: any) => (t.net_pnl ?? t.pnl_usd ?? 0) < 0).length;
  const grossWin = trades
    .filter((t: any) => (t.net_pnl ?? t.pnl_usd ?? 0) > 0)
    .reduce((acc: number, t: any) => acc + (t.net_pnl ?? t.pnl_usd ?? 0), 0);
  const grossLoss = Math.abs(
    trades
      .filter((t: any) => (t.net_pnl ?? t.pnl_usd ?? 0) < 0)
      .reduce((acc: number, t: any) => acc + (t.net_pnl ?? t.pnl_usd ?? 0), 0)
  );
  const totalFees = trades.reduce((acc: number, t: any) => acc + (t.fee_usd ?? 0), 0);
  const winRate = totalTradesCount > 0 ? (winCount / totalTradesCount) * 100 : 0;

  const filteredTrades = trades.filter((t: any) => {
    const sym = (t.symbol || t.asset || '').toUpperCase();
    const matchesSearch = !searchTerm || sym.includes(searchTerm.toUpperCase());
    const pnl = t.net_pnl ?? t.pnl_usd ?? 0;
    if (statusFilter === 'WIN') return matchesSearch && pnl > 0;
    if (statusFilter === 'LOSS') return matchesSearch && pnl < 0;
    return matchesSearch;
  });

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* Top Header & Navigation Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-line">
        <div className="flex items-center gap-3">
          <Link
            href={calendarBackUrl}
            className="p-2 rounded-lg border border-line bg-panel hover:bg-panel-light text-txt-secondary hover:text-txt-primary transition flex items-center gap-1.5 text-xs font-semibold"
          >
            <ArrowLeft className="w-4 h-4" />
            <span className="hidden sm:inline">Monthly Heatmap</span>
          </Link>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold tracking-tight text-txt-primary">
                Trading Session Detail
              </h1>
              <Badge variant={environment === 'LIVE' ? 'live' : 'info'}>
                {environment} • {workspace}
              </Badge>
            </div>
            <p className="text-xs text-txt-muted mt-0.5">
              Forensic order telemetry, fee breakdown, and execution audit trail for {currentDate}
            </p>
          </div>
        </div>

        {/* Date Selector Navigation Controls */}
        <div className="flex items-center gap-2">
          <button
            onClick={() => changeDateByOffset(-1)}
            className="p-2 rounded-lg border border-line bg-panel hover:bg-panel-light text-txt-secondary hover:text-txt-primary transition cursor-pointer"
            title="Previous Day"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>

          <div className="relative flex items-center">
            <CalendarIcon className="w-4 h-4 text-brand absolute left-2.5 pointer-events-none" />
            <input
              type="date"
              value={currentDate}
              onChange={handleDateInput}
              className="pl-8 pr-3 py-1.5 text-xs font-mono font-bold rounded-lg border border-line bg-panel text-txt-primary focus:outline-none focus:ring-2 focus:ring-brand shadow-2xs"
            />
          </div>

          <button
            onClick={() => changeDateByOffset(1)}
            className="p-2 rounded-lg border border-line bg-panel hover:bg-panel-light text-txt-secondary hover:text-txt-primary transition cursor-pointer"
            title="Next Day"
          >
            <ChevronRight className="w-4 h-4" />
          </button>

          <button
            onClick={() => loadSessionTrades(currentDate)}
            className="p-2 rounded-lg border border-line bg-panel hover:bg-panel-light text-txt-secondary hover:text-txt-primary transition cursor-pointer"
            title="Refresh Session"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        {/* Net Session PnL */}
        <div className="card-panel p-4 space-y-1">
          <span className="text-[10px] uppercase font-mono text-txt-muted font-bold block">
            Net Session PnL
          </span>
          <div className="flex items-center gap-1.5">
            {isNetProfit ? (
              <TrendingUp className="w-4 h-4 text-profit shrink-0" />
            ) : (
              <TrendingDown className="w-4 h-4 text-loss shrink-0" />
            )}
            <span
              className={`text-lg font-bold font-mono tracking-tight ${
                isNetProfit ? 'text-profit' : 'text-loss'
              }`}
            >
              {isFinancialMasked
                ? '••••••'
                : `${isNetProfit ? '+' : ''}${curr}${netPnl.toFixed(2)}`}
            </span>
          </div>
        </div>

        {/* Win Rate */}
        <div className="card-panel p-4 space-y-1">
          <span className="text-[10px] uppercase font-mono text-txt-muted font-bold block">
            Win Rate
          </span>
          <div className="flex items-center gap-1.5">
            <Award className="w-4 h-4 text-amber-500 shrink-0" />
            <span className="text-lg font-bold font-mono text-txt-primary">
              {winRate.toFixed(1)}%
            </span>
          </div>
          <span className="text-[10px] text-txt-muted">
            {winCount}W / {lossCount}L
          </span>
        </div>

        {/* Total Orders */}
        <div className="card-panel p-4 space-y-1">
          <span className="text-[10px] uppercase font-mono text-txt-muted font-bold block">
            Executed Orders
          </span>
          <div className="flex items-center gap-1.5">
            <Activity className="w-4 h-4 text-brand shrink-0" />
            <span className="text-lg font-bold font-mono text-txt-primary">
              {totalTradesCount}
            </span>
          </div>
          <span className="text-[10px] text-txt-muted">Filled Fills</span>
        </div>

        {/* Gross Profit */}
        <div className="card-panel p-4 space-y-1">
          <span className="text-[10px] uppercase font-mono text-txt-muted font-bold block">
            Gross Profit
          </span>
          <span className="text-lg font-bold font-mono text-profit block">
            {isFinancialMasked ? '••••••' : `+${curr}${grossWin.toFixed(2)}`}
          </span>
          <span className="text-[10px] text-txt-muted">Total Winning Trades</span>
        </div>

        {/* Gross Loss */}
        <div className="card-panel p-4 space-y-1">
          <span className="text-[10px] uppercase font-mono text-txt-muted font-bold block">
            Gross Loss
          </span>
          <span className="text-lg font-bold font-mono text-loss block">
            {isFinancialMasked ? '••••••' : `-${curr}${grossLoss.toFixed(2)}`}
          </span>
          <span className="text-[10px] text-txt-muted">Total Losing Trades</span>
        </div>

        {/* Total Fees */}
        <div className="card-panel p-4 space-y-1">
          <span className="text-[10px] uppercase font-mono text-txt-muted font-bold block">
            Exchange Fees
          </span>
          <span className="text-lg font-bold font-mono text-txt-secondary block">
            {isFinancialMasked ? '••••••' : `${curr}${totalFees.toFixed(4)}`}
          </span>
          <span className="text-[10px] text-txt-muted">Broker & Taker Fees</span>
        </div>
      </div>

      {/* Executed Orders Section */}
      <div className="card-panel p-5 space-y-4">
        {/* Table Filters & Search */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-line">
          <div className="flex items-center gap-2">
            <Layers className="w-4 h-4 text-brand" />
            <h2 className="text-sm font-bold text-txt-primary">
              Executed Orders & Trade Fills ({filteredTrades.length})
            </h2>
          </div>

          <div className="flex items-center gap-2">
            {/* Search Input */}
            <div className="relative">
              <Search className="w-3.5 h-3.5 text-txt-muted absolute left-2.5 top-2.5 pointer-events-none" />
              <input
                type="text"
                placeholder="Search symbol..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-8 pr-3 py-1.5 text-xs rounded-lg border border-line bg-panel-light text-txt-primary focus:outline-none focus:ring-1 focus:ring-brand font-mono"
              />
            </div>

            {/* Filter Pill Toggle */}
            <div className="flex items-center rounded-lg border border-line bg-panel-light p-0.5 text-xs">
              <button
                onClick={() => setStatusFilter('ALL')}
                className={`px-2.5 py-1 rounded font-semibold transition cursor-pointer ${
                  statusFilter === 'ALL'
                    ? 'bg-panel text-txt-primary shadow-2xs'
                    : 'text-txt-muted hover:text-txt-primary'
                }`}
              >
                All
              </button>
              <button
                onClick={() => setStatusFilter('WIN')}
                className={`px-2.5 py-1 rounded font-semibold transition cursor-pointer ${
                  statusFilter === 'WIN'
                    ? 'bg-emerald-500/10 text-profit font-bold'
                    : 'text-txt-muted hover:text-profit'
                }`}
              >
                Wins
              </button>
              <button
                onClick={() => setStatusFilter('LOSS')}
                className={`px-2.5 py-1 rounded font-semibold transition cursor-pointer ${
                  statusFilter === 'LOSS'
                    ? 'bg-red-500/10 text-loss font-bold'
                    : 'text-txt-muted hover:text-loss'
                }`}
              >
                Losses
              </button>
            </div>
          </div>
        </div>

        {/* Orders Table */}
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-mono">
            <thead>
              <tr className="border-b border-line text-txt-muted uppercase text-[10px]">
                <th className="py-2.5 px-3">Timestamp</th>
                <th className="py-2.5 px-3">Symbol</th>
                <th className="py-2.5 px-3">Side</th>
                <th className="py-2.5 px-3 text-right">Quantity</th>
                <th className="py-2.5 px-3 text-right">Entry Price</th>
                <th className="py-2.5 px-3 text-right">Exit Price</th>
                <th className="py-2.5 px-3 text-right">Net PnL</th>
                <th className="py-2.5 px-3 text-right">Fee</th>
                <th className="py-2.5 px-3 text-center">Status</th>
                <th className="py-2.5 px-3">Exit Reason</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {isLoading ? (
                <tr>
                  <td colSpan={10} className="py-12 text-center text-txt-muted">
                    <RefreshCw className="w-6 h-6 animate-spin mx-auto text-brand mb-2" />
                    <span>Loading session executions...</span>
                  </td>
                </tr>
              ) : filteredTrades.length === 0 ? (
                <tr>
                  <td colSpan={10} className="py-12 text-center text-txt-muted">
                    <div className="flex flex-col items-center justify-center gap-1.5">
                      <Layers className="h-7 w-7 text-txt-subtle" />
                      <span className="font-semibold text-xs text-txt-primary">
                        No trade fills recorded for {currentDate}
                      </span>
                      <span className="text-[11px] text-txt-muted">
                        No orders were submitted or closed during this session.
                      </span>
                    </div>
                  </td>
                </tr>
              ) : (
                filteredTrades.map((t: any, idx: number) => {
                  const pnl = t.net_pnl ?? t.pnl_usd ?? 0;
                  const isWin = pnl > 0;
                  const isLoss = pnl < 0;
                  const side = (t.side || t.action || 'BUY').toUpperCase();

                  return (
                    <tr key={t.trade_id || idx} className="hover:bg-panel-light/60 transition">
                      <td className="py-2.5 px-3 text-txt-muted whitespace-nowrap">
                        {t.timestamp || t.date || currentDate}
                      </td>
                      <td className="py-2.5 px-3 font-bold text-txt-primary whitespace-nowrap">
                        {t.symbol || t.asset}
                      </td>
                      <td className="py-2.5 px-3">
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                            side === 'BUY'
                              ? 'bg-emerald-500/10 text-profit border border-emerald-500/20'
                              : 'bg-red-500/10 text-loss border border-red-500/20'
                          }`}
                        >
                          {side}
                        </span>
                      </td>
                      <td className="py-2.5 px-3 text-right text-txt-secondary tabular-nums">
                        {Number(t.quantity || t.units || 0).toLocaleString('en-US', {
                          maximumFractionDigits: 6,
                        })}
                      </td>
                      <td className="py-2.5 px-3 text-right text-txt-secondary tabular-nums">
                        {curr}
                        {Number(t.entry_price || 0).toLocaleString('en-US', {
                          minimumFractionDigits: 2,
                          maximumFractionDigits: 4,
                        })}
                      </td>
                      <td className="py-2.5 px-3 text-right text-txt-secondary tabular-nums">
                        {curr}
                        {Number(t.exit_price || t.entry_price || 0).toLocaleString('en-US', {
                          minimumFractionDigits: 2,
                          maximumFractionDigits: 4,
                        })}
                      </td>
                      <td className="py-2.5 px-3 text-right font-bold tabular-nums whitespace-nowrap">
                        <span className={isWin ? 'text-profit' : isLoss ? 'text-loss' : 'text-txt-muted'}>
                          {isFinancialMasked ? (
                            '••••••'
                          ) : (
                            `${isWin ? '+' : ''}${curr}${pnl.toFixed(2)}`
                          )}
                        </span>
                      </td>
                      <td className="py-2.5 px-3 text-right text-txt-muted tabular-nums">
                        {curr}
                        {Number(t.fee_usd || 0).toFixed(4)}
                      </td>
                      <td className="py-2.5 px-3 text-center">
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                            isWin
                              ? 'bg-emerald-500/10 text-profit'
                              : isLoss
                              ? 'bg-red-500/10 text-loss'
                              : 'bg-slate-100 text-txt-muted'
                          }`}
                        >
                          {isWin ? 'WIN' : isLoss ? 'LOSS' : 'FLAT'}
                        </span>
                      </td>
                      <td className="py-2.5 px-3 text-txt-muted text-[11px] truncate max-w-xs">
                        {t.close_reason || t.reason || 'TAKE_PROFIT_HARVEST'}
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
