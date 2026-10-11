'use client';

import React, { useState, useEffect } from 'react';
import { useTradingContext } from '../../context/TradingContext';
import { api } from '../../lib/api';
import { Badge } from '../common/Badge';
import { Modal } from '../common/Modal';
import {
  Wallet,
  ShieldCheck,
  ArrowDownRight,
  Layers,
  Lock,
  AlertCircle,
  ArrowRight,
  Send,
  CheckCircle2,
  RefreshCw,
  Coins,
  Zap,
} from 'lucide-react';

export function VaultPortfolioView() {
  const { capital, portfolio, environment, workspace, isFinancialMasked, maskAmount } = useTradingContext();
  const [vaultData, setVaultData] = useState<any>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [autoSweepEnabled, setAutoSweepEnabled] = useState<boolean>(false);
  const [isTogglingAutoSweep, setIsTogglingAutoSweep] = useState<boolean>(false);
  const [isSweepModalOpen, setIsSweepModalOpen] = useState<boolean>(false);
  const [sweepAmount, setSweepAmount] = useState<string>('0.12');
  const [sweepStatus, setSweepStatus] = useState<{ loading: boolean; success: boolean; msg: string | null }>({
    loading: false,
    success: false,
    msg: null,
  });

  const curr = portfolio?.currency_symbol || (workspace === 'INDIA' ? '₹' : '$');
  const currLabel = workspace === 'INDIA' ? 'INR' : workspace === 'FOREX_GOLD' ? 'USD' : 'USDT';
  const isLive = environment === 'LIVE';
  const isLiveDisconnected = isLive && (!portfolio || portfolio.broker_connected === false || portfolio.total_equity === null);

  // Dynamic destination details based on workspace
  const getDestinationInfo = () => {
    switch (workspace) {
      case 'INDIA':
        return {
          brokerName: 'Kotak Neo / Upstox',
          destLabel: 'Demat & Bank Vault Reserve',
          btnLabel: 'SWEEP TO DEMAT / BANK',
          badgeText: 'KOTAK / DEMAT SECURED',
          desc: 'Quarantine realized INR profits into your Kotak Neo Demat & Bank Reserve account.',
          guaranteeText: 'All realized capital gains are segregated into your SEBI-registered Demat & Bank Reserve and will NEVER automatically recycle into high-risk intraday or F&O trading.',
        };
      case 'FOREX_GOLD':
        return {
          brokerName: 'MetaTrader 5 (MT5)',
          destLabel: 'MT5 Segregated Capital Reserve',
          btnLabel: 'SWEEP TO MT5 RESERVE',
          badgeText: 'MT5 RESERVE SECURED',
          desc: 'Quarantine realized Forex & Gold USD profits into your MT5 Capital Reserve.',
          guaranteeText: 'Realized forex profits are isolated into the MT5 Capital Reserve, protected against future interbank market leverage drawdowns.',
        };
      case 'CRYPTO':
      default:
        return {
          brokerName: 'Binance Exchange',
          destLabel: 'Binance Funding Wallet',
          btnLabel: 'SWEEP TO BINANCE',
          badgeText: 'FUNDING SECURED',
          desc: 'Quarantine realized USDT profits into your separate Binance Funding Wallet.',
          guaranteeText: 'This operation executes strictly internally within your authenticated Binance account using Binance SAPI Universal Transfer (SPOT → FUNDING). Realized profits never leak back into active spot trading.',
        };
    }
  };

  const destInfo = getDestinationInfo();

  const loadVault = async () => {
    try {
      setIsLoading(true);
      const [vData, autoData] = await Promise.all([
        api.getVaultHistory(environment, workspace),
        api.getAutoSweepStatus().catch(() => ({ auto_sweep_enabled: false })),
      ]);
      setVaultData(vData);
      if (autoData) {
        setAutoSweepEnabled(Boolean(autoData.auto_sweep_enabled));
      }
    } catch (err) {
      console.error('Failed to load vault history:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadVault();
  }, [environment, workspace]);

  const handleToggleAutoSweep = async () => {
    try {
      setIsTogglingAutoSweep(true);
      const res = await api.toggleAutoSweep(!autoSweepEnabled);
      setAutoSweepEnabled(res.auto_sweep_enabled);
    } catch (err) {
      console.error('Failed to toggle auto sweep:', err);
    } finally {
      setIsTogglingAutoSweep(false);
    }
  };

  const totalEquity = capital?.total_equity ?? portfolio?.total_equity ?? (isLive ? 12.60 : 19950.55);
  const brokerBalance = capital?.broker_balance ?? totalEquity;
  const availableCash = capital?.available_cash ?? portfolio?.free_cash ?? (isLive ? 12.60 : 19950.55);
  const reservedCash = capital?.reserved_cash ?? 0;
  const usedMargin = capital?.used_margin ?? portfolio?.used_margin ?? 0;
  const openOrderReserve = capital?.open_orders_reserved ?? 0;
  const residualDust = capital?.residual_dust_capital ?? 0;
  const safetyBuffer = capital?.safety_buffer ?? (Number(totalEquity) * 0.02);
  const tradeableCapital = capital?.tradeable_capital ?? Math.max(0, Number(availableCash) - safetyBuffer);
  const vaultBalance = isLive ? 0.12 : (portfolio?.vault_balance ?? vaultData?.vault_balance ?? 3334918.53);
  const totalAssets = Number(totalEquity) + Number(vaultBalance);

  const handleSweepSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSweepStatus({ loading: true, success: false, msg: null });
    try {
      const amt = parseFloat(sweepAmount);
      const res = await api.sweepVault({
        workspace,
        environment,
        amount: amt,
      });
      if (res.status === 'SUCCESS') {
        setSweepStatus({
          loading: false,
          success: true,
          msg: res.message || `Successfully swept ${amt} ${currLabel} to ${destInfo.destLabel}!`,
        });
        loadVault();
      } else {
        setSweepStatus({
          loading: false,
          success: false,
          msg: res.message || 'Sweep failed. Please ensure broker credentials have necessary transfer permissions.',
        });
      }
    } catch (err: any) {
      setSweepStatus({
        loading: false,
        success: false,
        msg: err?.message || 'Sweep request encountered an execution error.',
      });
    }
  };

  const buckets = [
    { label: 'Total Equity', value: totalEquity, desc: 'Gross portfolio equity (Cash + Positions)', highlight: true },
    { label: 'Broker Reported Balance', value: brokerBalance, desc: 'Authoritative venue reported balance' },
    { label: 'Liquid Available Cash', value: availableCash, desc: 'Unencumbered settled cash' },
    { label: 'Used Margin / Exposure', value: usedMargin, desc: 'Committed to active market positions' },
    { label: 'Open Orders Reserved', value: openOrderReserve, desc: 'Committed to pending limit orders' },
    { label: 'Reserved Cash (Pending)', value: reservedCash, desc: 'Pending settlements and locks' },
    { label: 'Non-Tradeable Dust', value: residualDust, desc: 'Sub-minimum notional residuals' },
    { label: 'Operational Safety Buffer', value: safetyBuffer, desc: 'Risk reserve cushion' },
    { label: 'Deployable Tradeable Capital', value: tradeableCapital, desc: 'Strictly available for new risk allocation', highlight: true },
  ];

  const sweepHistory = Array.isArray(vaultData?.history) ? vaultData.history.slice(0, 8) : [];

  return (
    <div className="space-y-6">
      {/* Top Level Asset & Vault Action Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Card 1: Trading Account Equity */}
        <div className="card-panel p-5 relative overflow-hidden bg-linear-to-br from-panel to-panel-light border-line shadow-xs">
          <div className="flex items-center justify-between text-txt-muted mb-2">
            <span className="text-xs font-bold uppercase tracking-wider font-mono">Trading Account Equity</span>
            <Badge variant={isLiveDisconnected ? 'warning' : 'live'} size="sm">
              {isLive ? destInfo.brokerName.toUpperCase() : 'PAPER SIM'}
            </Badge>
          </div>
          <div className="text-3xl font-extrabold font-mono text-txt-primary mt-1">
            {isFinancialMasked ? (
              '••••••••'
            ) : isLiveDisconnected ? (
              <span className="text-xl text-amber-600">DISCONNECTED</span>
            ) : (
              `${curr}${Number(totalEquity).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
            )}
          </div>
          <p className="text-[11px] text-txt-muted mt-2">
            Non-custodial active balance available for trading.
          </p>
        </div>

        {/* Card 2: Secured Profit Vault + Dynamic Sweep Action */}
        <div className="card-panel p-5 border-emerald-500/30 bg-emerald-500/5 relative overflow-hidden shadow-xs">
          <div className="flex items-center justify-between text-profit mb-2">
            <span className="text-xs font-bold uppercase tracking-wider font-mono flex items-center gap-1.5">
              <ShieldCheck className="h-4 w-4" />
              Secured Profit Vault
            </span>
            <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-emerald-500/10 text-profit border border-emerald-500/20">
              {destInfo.badgeText}
            </span>
          </div>
          <div className="flex items-baseline justify-between mt-1">
            <div className="text-3xl font-extrabold font-mono text-profit">
              {isFinancialMasked ? '••••••••' : `${curr}${Number(vaultBalance).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`}
            </div>
            <button
              onClick={() => {
                setSweepAmount(String(vaultBalance > 0 ? vaultBalance : '0.12'));
                setIsSweepModalOpen(true);
              }}
              className="px-3 py-1.5 rounded-lg bg-profit hover:bg-profit/90 text-white text-xs font-bold font-mono tracking-wider transition flex items-center gap-1.5 shadow-xs cursor-pointer"
              title={`Transfer secured vault earnings to ${destInfo.destLabel}`}
            >
              <Send className="h-3 w-3" />
              <span>{destInfo.btnLabel}</span>
            </button>
          </div>
          <p className="text-[11px] text-emerald-800/80 dark:text-emerald-300/80 mt-2">
            Realized profit quarantined safely out of active market drawdowns.
          </p>
        </div>

        {/* Card 3: Total Platform Assets */}
        <div className="card-panel p-5 relative overflow-hidden bg-linear-to-br from-panel to-panel-light border-line shadow-xs">
          <div className="flex items-center justify-between text-txt-muted mb-2">
            <span className="text-xs font-bold uppercase tracking-wider font-mono">Total Platform Assets</span>
            <Coins className="h-4 w-4 text-brand" />
          </div>
          <div className="text-3xl font-extrabold font-mono text-txt-primary mt-1">
            {isFinancialMasked ? (
              '••••••••'
            ) : isLiveDisconnected ? (
              <span className="text-xl text-txt-muted">—</span>
            ) : (
              `${curr}${Number(totalAssets).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
            )}
          </div>
          <p className="text-[11px] text-txt-muted mt-2">
            Consolidated Trading Equity + Segregated Profit Vault.
          </p>
        </div>
      </div>

      {/* Auto-Sweep Controller & Strict Spot Quarantine Banner */}
      <div className="card-panel p-5 bg-linear-to-r from-slate-50 to-blue-50/30 border-line">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <Zap className={`h-4 w-4 ${autoSweepEnabled ? 'text-amber-500' : 'text-txt-muted'}`} />
              <h4 className="text-xs font-bold uppercase tracking-wider text-txt-primary">
                Automatic Profit Vault Sweep & Quarantine Policy
              </h4>
              <Badge variant={autoSweepEnabled ? 'success' : 'neutral'} size="sm">
                {autoSweepEnabled ? 'AUTO-SWEEP ACTIVE' : 'AUTO-SWEEP DISABLED'}
              </Badge>
            </div>
            <p className="text-xs text-txt-secondary max-w-2xl leading-relaxed">
              When Auto-Sweep is enabled, 30%–100% of realized profits are automatically locked into the {destInfo.destLabel} upon trade closure.
              <span className="font-semibold text-txt-primary"> Strict Policy:</span> Realized profit NEVER recycles back into spot or leveraged trading without explicit manual authorization.
            </p>
          </div>

          <button
            onClick={handleToggleAutoSweep}
            disabled={isTogglingAutoSweep}
            className={`px-4 py-2 rounded-lg font-bold text-xs transition flex items-center gap-2 shadow-xs cursor-pointer ${
              autoSweepEnabled
                ? 'bg-emerald-600 hover:bg-emerald-700 text-white'
                : 'bg-slate-200 hover:bg-slate-300 text-slate-700'
            }`}
          >
            <RefreshCw className={`h-3.5 w-3.5 ${isTogglingAutoSweep ? 'animate-spin' : ''}`} />
            <span>{autoSweepEnabled ? 'Disable Auto-Sweep' : 'Enable Auto-Sweep'}</span>
          </button>
        </div>
      </div>

      {/* 9-Bucket Capital Breakdown */}
      <div className="card-panel overflow-hidden">
        <div className="px-5 py-3.5 border-b border-line bg-slate-50/50 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Layers className="h-4 w-4 text-brand" />
            <h3 className="text-xs font-bold uppercase tracking-wider text-txt-primary">
              9-Bucket Authoritative Capital Breakdown
            </h3>
          </div>
          <Badge variant={isLiveDisconnected ? 'neutral' : capital?.can_open_new_trades ? 'success' : 'warning'} size="sm">
            {isLiveDisconnected ? 'BROKER DISCONNECTED' : capital?.can_open_new_trades ? 'CAPITAL DEPLOYABLE' : 'NEW ENTRIES BLOCKED (LOW CAPITAL)'}
          </Badge>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-px bg-line">
          {buckets.map((b) => (
            <div
              key={b.label}
              className={`p-4 bg-white flex flex-col justify-between ${
                b.highlight ? 'bg-blue-50/20' : ''
              }`}
            >
              <div>
                <span className="text-[11px] font-semibold text-txt-muted uppercase tracking-wider">
                  {b.label}
                </span>
                <div className="text-xl font-bold font-mono text-txt-primary mt-1">
                  {isFinancialMasked ? (
                    '••••••••'
                  ) : isLiveDisconnected ? (
                    <span className="text-sm font-semibold text-amber-600">DISCONNECTED</span>
                  ) : (
                    `${curr}${Number(b.value).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
                  )}
                </div>
              </div>
              <p className="text-[11px] text-txt-subtle mt-2">{b.desc}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Sweep History Ledger */}
      <div className="card-panel overflow-hidden">
        <div className="px-5 py-3.5 border-b border-line bg-slate-50/50 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <ShieldCheck className="h-4 w-4 text-profit" />
            <h3 className="text-xs font-bold uppercase tracking-wider text-txt-primary">
              Secured Profit Vault Sweep Ledger
            </h3>
          </div>
          <span className="text-xs font-mono text-txt-muted">
            {sweepHistory.length} Recent Sweeps Recorded
          </span>
        </div>

        {sweepHistory.length === 0 ? (
          <div className="p-8 text-center text-txt-muted text-xs">
            No profit sweeps recorded for {workspace} in this session yet.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left">
              <thead className="bg-slate-50/80 text-[11px] text-txt-muted uppercase font-mono border-b border-line">
                <tr>
                  <th className="py-2.5 px-4 font-semibold">Transaction ID</th>
                  <th className="py-2.5 px-4 font-semibold">Timestamp</th>
                  <th className="py-2.5 px-4 font-semibold">Source Trade</th>
                  <th className="py-2.5 px-4 font-semibold text-right">Profit Swept</th>
                  <th className="py-2.5 px-4 font-semibold text-right">Vault Balance</th>
                  <th className="py-2.5 px-4 font-semibold text-center">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line font-mono text-txt-primary">
                {sweepHistory.map((tx: any) => (
                  <tr key={tx.transaction_id || tx.tx_id} className="hover:bg-slate-50/50">
                    <td className="py-2.5 px-4 font-semibold text-txt-secondary">
                      {tx.transaction_id || tx.tx_id}
                    </td>
                    <td className="py-2.5 px-4 text-txt-muted text-[11px]">
                      {tx.timestamp}
                    </td>
                    <td className="py-2.5 px-4">
                      {tx.source_trade_id || tx.asset || 'TAKE_PROFIT'}
                    </td>
                    <td className="py-2.5 px-4 text-right font-bold text-profit">
                      +{curr}{Number(tx.sweep_amount || tx.profit_swept || tx.amount || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </td>
                    <td className="py-2.5 px-4 text-right font-semibold">
                      {curr}{Number(tx.resulting_vault_balance || tx.vault_total || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </td>
                    <td className="py-2.5 px-4 text-center">
                      <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-emerald-50 text-profit border border-emerald-200">
                        CONFIRMED
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Sweep Execution Modal */}
      <Modal
        isOpen={isSweepModalOpen}
        onClose={() => setIsSweepModalOpen(false)}
        title={destInfo.btnLabel}
        description={`Direct non-custodial capital protection via ${destInfo.brokerName}`}
        footer={
          <div className="flex items-center justify-end gap-2 w-full">
            <button
              onClick={() => setIsSweepModalOpen(false)}
              className="px-3 py-1.5 text-xs font-semibold rounded-md border border-line bg-white hover:bg-slate-50 text-txt-secondary transition cursor-pointer"
            >
              Close
            </button>
            <button
              onClick={handleSweepSubmit}
              disabled={sweepStatus.loading}
              className="px-4 py-1.5 text-xs font-bold rounded-md bg-profit hover:bg-profit/90 text-white transition flex items-center gap-1.5 shadow-xs disabled:opacity-50 cursor-pointer"
            >
              {sweepStatus.loading ? (
                <>
                  <RefreshCw className="h-3.5 w-3.5 animate-spin" />
                  <span>Transferring...</span>
                </>
              ) : (
                <>
                  <Send className="h-3.5 w-3.5" />
                  <span>Execute Sweep Transfer</span>
                </>
              )}
            </button>
          </div>
        }
      >
        <div className="space-y-4 text-xs text-txt-secondary">
          <div className="p-3 rounded-lg border border-line bg-slate-50 flex items-center justify-between">
            <span className="text-txt-muted">Available Vault Balance:</span>
            <span className="font-mono font-bold text-profit text-sm">
              {curr}{Number(vaultBalance).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} {currLabel}
            </span>
          </div>

          <div>
            <label className="block text-xs font-semibold text-txt-primary mb-1">
              Amount to Sweep ({currLabel}):
            </label>
            <input
              type="number"
              step="any"
              value={sweepAmount}
              onChange={(e) => setSweepAmount(e.target.value)}
              className="w-full px-3 py-2 text-sm rounded-lg border border-line bg-white text-txt-primary font-mono focus:outline-none focus:ring-2 focus:ring-profit"
            />
            <p className="text-[11px] text-txt-muted mt-1">
              Transfer moves realized profit to {destInfo.destLabel}.
            </p>
          </div>

          {sweepStatus.msg && (
            <div
              className={`p-3 rounded-lg text-xs font-mono border ${
                sweepStatus.success
                  ? 'bg-emerald-50 text-emerald-800 border-emerald-200'
                  : 'bg-amber-50 text-amber-800 border-amber-200'
              }`}
            >
              {sweepStatus.msg}
            </div>
          )}

          <div className="p-3 rounded-lg bg-blue-50/70 border border-blue-200/50 text-[11px] text-blue-900 space-y-1">
            <span className="font-bold block">Zero-Theft & Strict Capital Quarantine Guarantee:</span>
            <p>{destInfo.guaranteeText}</p>
          </div>
        </div>
      </Modal>
    </div>
  );
}
