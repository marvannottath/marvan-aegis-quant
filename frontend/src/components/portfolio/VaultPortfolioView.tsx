'use client';

import React, { useState, useEffect } from 'react';
import { useTradingContext } from '../../context/TradingContext';
import { api } from '../../lib/api';
import { Badge } from '../common/Badge';
import { Wallet, ShieldCheck, ArrowDownRight, Layers, Lock, AlertCircle } from 'lucide-react';

export function VaultPortfolioView() {
  const { capital, portfolio, environment, workspace } = useTradingContext();
  const [vaultData, setVaultData] = useState<any>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const curr = portfolio?.currency_symbol || '$';

  useEffect(() => {
    const loadVault = async () => {
      try {
        setIsLoading(true);
        const data = await api.getVaultHistory(environment);
        setVaultData(data);
      } catch (err) {
        console.error('Failed to load vault history:', err);
      } finally {
        setIsLoading(false);
      }
    };
    loadVault();
  }, [environment]);

  const totalEquity = capital?.total_equity ?? portfolio?.total_equity ?? 0;
  const brokerBalance = capital?.broker_balance ?? totalEquity;
  const availableCash = capital?.available_cash ?? portfolio?.free_cash ?? 0;
  const reservedCash = capital?.reserved_cash ?? 0;
  const usedMargin = capital?.used_margin ?? portfolio?.used_margin ?? 0;
  const openOrderReserve = capital?.open_orders_reserved ?? 0;
  const residualDust = capital?.residual_dust_capital ?? 0;
  const safetyBuffer = capital?.safety_buffer ?? (totalEquity * 0.02);
  const tradeableCapital = capital?.tradeable_capital ?? Math.max(0, availableCash - safetyBuffer);
  const vaultBalance = portfolio?.vault_balance ?? vaultData?.vault_balance ?? 0;

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

  return (
    <div className="space-y-6">
      {/* 9-Bucket Capital Breakdown */}
      <div className="card-panel overflow-hidden">
        <div className="px-5 py-3.5 border-b border-line bg-slate-50/50 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Layers className="h-4 w-4 text-brand" />
            <h3 className="text-xs font-bold uppercase tracking-wider text-txt-primary">
              9-Bucket Authoritative Capital Breakdown
            </h3>
          </div>
          <Badge variant={capital?.can_open_new_trades ? 'success' : 'warning'} size="sm">
            {capital?.can_open_new_trades ? 'CAPITAL DEPLOYABLE' : 'NEW ENTRIES BLOCKED (LOW CAPITAL)'}
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
                  {curr}
                  {Number(b.value).toLocaleString('en-US', { minimumFractionDigits: 2 })}
                </div>
              </div>
              <p className="text-[11px] text-txt-subtle mt-2">{b.desc}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Segregated Profit Vault Section */}
      <div className="card-panel p-5 space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line pb-4">
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-emerald-50 text-profit rounded-lg border border-emerald-100">
              <ShieldCheck className="h-6 w-6" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-sm font-bold text-txt-primary">
                  Segregated Profit Vault
                </h3>
                <Badge variant="success">Secured Earnings</Badge>
              </div>
              <p className="text-xs text-txt-muted mt-0.5">
                Automatically sweeps realized profits to protect gains from trading drawdown.
              </p>
            </div>
          </div>

          <div className="text-right">
            <span className="text-xs text-txt-muted block">Current Vault Holdings</span>
            <span className="text-2xl font-bold font-mono text-profit">
              {curr}
              {Number(vaultBalance).toLocaleString('en-US', { minimumFractionDigits: 2 })}
            </span>
          </div>
        </div>

        {/* Accounting Clarification Notice */}
        <div className="p-3.5 rounded-lg bg-amber-50/70 border border-amber-200/60 flex items-start gap-2.5 text-xs text-amber-900">
          <AlertCircle className="h-4 w-4 text-warn shrink-0 mt-0.5" />
          <div className="space-y-0.5">
            <span className="font-semibold block">Institutional Accounting Isolation Rule:</span>
            <p className="text-[11px] text-amber-800 leading-relaxed">
              Vault balance is an independent internal segregation of realized gains and is NOT counted as additional live broker trading margin.
              This prevents phantom capital leverage and protects realized profits from future market volatility.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
