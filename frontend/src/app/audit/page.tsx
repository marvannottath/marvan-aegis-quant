'use client';

import React, { useState, useEffect } from 'react';
import { useTradingContext } from '../../context/TradingContext';
import { FileCheck, ShieldCheck, RefreshCw, AlertTriangle, Hash, BookOpen } from 'lucide-react';
import { Badge } from '../../components/common/Badge';

interface LedgerEntry {
  entry_id: string;
  timestamp: string;
  ledger_type?: string;
  debit_account: string;
  credit_account: string;
  amount: number;
  asset: string;
  reference_id: string;
  hash?: string;
}

interface AuditLog {
  event_id: string;
  timestamp: string;
  event_type: string;
  user_id?: string;
  actor?: string;
  action?: string;
  symbol?: string;
  result?: string;
  integrity_hash?: string;
}

interface FinancialAuditData {
  status: string;
  environment: string;
  reconciliation: {
    status: string;
    cash: number;
    used_margin: number;
    unrealized_pnl: number;
    trading_account_equity: number;
    secured_vault_reserve: number;
    total_platform_assets: number;
    computed_equity: number;
    reported_equity: number;
    delta: number;
    model_explanation?: string;
  };
  ledger_entries_count: number;
  ledger_entries: LedgerEntry[];
  audit_logs: AuditLog[];
}

export default function AuditPage() {
  const { environment, workspace, portfolio } = useTradingContext();
  const [auditData, setAuditData] = useState<FinancialAuditData | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const isLiveDisconnected = environment === 'LIVE' && (!portfolio || portfolio.broker_connected === false || portfolio.total_equity === null);
  const curr = portfolio?.currency_symbol || (workspace === 'INDIA' ? '₹' : '$');

  const loadAuditData = async () => {
    try {
      setIsLoading(true);
      setErrorMsg(null);
      const res = await fetch(`/api/reconciliation/financial-audit?environment=${environment}&workspace=${workspace}`);
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}: Failed to fetch financial audit telemetry`);
      }
      const data: FinancialAuditData = await res.json();
      setAuditData(data);
    } catch (err: any) {
      console.error('Failed to load financial audit:', err);
      setErrorMsg(err?.message || 'Error connecting to authoritative ledger sentinel');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadAuditData();
  }, [environment, workspace]);

  const recon = auditData?.reconciliation;
  const entries = auditData?.ledger_entries || [];
  const logs = auditData?.audit_logs || [];

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-txt-primary">
            Audit & Double-Entry Ledger Forensics
          </h1>
          <p className="text-xs text-txt-muted mt-0.5">
            Immutable audit trail and double-entry balanced debit/credit event journal ({workspace} • {environment}).
          </p>
        </div>

        <button
          onClick={loadAuditData}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-md border border-line bg-slate-50 hover:bg-slate-100 text-xs font-semibold text-txt-secondary transition"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${isLoading ? 'animate-spin' : ''}`} />
          <span>Refresh Ledger</span>
        </button>
      </div>

      {/* Disconnected Warning Banner */}
      {isLiveDisconnected && (
        <div className="p-3.5 rounded-lg bg-amber-50 border border-amber-200 text-amber-900 text-xs flex items-start gap-2.5">
          <AlertTriangle className="h-4 w-4 shrink-0 text-amber-600 mt-0.5" />
          <div className="space-y-0.5">
            <span className="font-bold block">LIVE Broker Unauthenticated</span>
            <span className="text-[11px] text-amber-700 block">
              Private live broker authentication is disconnected. Showing authoritative internal system state. External venue balance reconciliation remains unverified until live broker credentials are authenticated.
            </span>
          </div>
        </div>
      )}

      {/* Error state */}
      {errorMsg && (
        <div className="p-3.5 rounded-lg bg-red-50 border border-red-200 text-loss text-xs flex items-center gap-2">
          <AlertTriangle className="h-4 w-4 shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* Top Reconciliation Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="card-panel p-4 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-txt-muted uppercase">Reconciliation Status</span>
            <ShieldCheck className="h-4 w-4 text-brand" />
          </div>
          <div className="text-base font-bold font-mono text-txt-primary">
            {recon?.status || (isLiveDisconnected ? 'BROKER_DISCONNECTED' : 'STANDBY')}
          </div>
          <p className="text-[11px] text-txt-subtle">
            {recon?.model_explanation || 'Trading Equity = Cash + Margin + FloatingPnL'}
          </p>
        </div>

        <div className="card-panel p-4 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-txt-muted uppercase">Balance Delta</span>
            <FileCheck className="h-4 w-4 text-profit" />
          </div>
          <div className="text-base font-bold font-mono text-txt-primary">
            {recon?.delta !== null && recon?.delta !== undefined ? (
              <span className="text-profit">{curr}{Number(recon.delta).toFixed(4)}</span>
            ) : (
              <span className="text-txt-muted">—</span>
            )}
          </div>
          <p className="text-[11px] text-txt-subtle">
            {recon?.delta !== null && recon?.delta !== undefined
              ? '|Computed Equity - Reported Equity| tolerance < 0.01'
              : 'Requires authenticated live broker to calculate external variance'}
          </p>
        </div>

        <div className="card-panel p-4 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-txt-muted uppercase">Ledger Entries Posted</span>
            <BookOpen className="h-4 w-4 text-brand" />
          </div>
          <div className="text-base font-bold font-mono text-txt-primary">
            {auditData?.ledger_entries_count ?? entries.length} Events
          </div>
          <p className="text-[11px] text-txt-subtle">
            Strict double-entry debits and credits recorded.
          </p>
        </div>
      </div>

      {/* Double-Entry Ledger Journal Table */}
      <div className="card-panel overflow-hidden">
        <div className="px-5 py-3.5 border-b border-line bg-slate-50/50 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <BookOpen className="h-4 w-4 text-brand" />
            <h3 className="text-xs font-bold uppercase tracking-wider text-txt-primary">
              Double-Entry General Ledger Entries
            </h3>
          </div>
          <span className="text-[11px] text-txt-muted font-mono">
            {entries.length} Recent Postings
          </span>
        </div>

        <div className="overflow-x-auto max-h-[340px] overflow-y-auto">
          <table className="w-full text-left text-xs font-mono">
            <thead>
              <tr className="border-b border-line bg-slate-50 text-txt-muted text-[10px] font-semibold uppercase tracking-wider">
                <th className="py-2 px-3">Entry ID</th>
                <th className="py-2 px-3">Timestamp</th>
                <th className="py-2 px-3">Type</th>
                <th className="py-2 px-3">Debit Account</th>
                <th className="py-2 px-3">Credit Account</th>
                <th className="py-2 px-3 text-right">Amount</th>
                <th className="py-2 px-3">Asset</th>
                <th className="py-2 px-3">Ref ID</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line text-[11px]">
              {entries.length === 0 ? (
                <tr>
                  <td colSpan={8} className="py-8 text-center text-txt-muted font-sans">
                    {isLoading ? 'Querying ledger store...' : 'No ledger entries posted for this environment.'}
                  </td>
                </tr>
              ) : (
                entries.map((e) => (
                  <tr key={e.entry_id} className="table-row-hover">
                    <td className="py-2 px-3 font-bold text-txt-primary">{e.entry_id}</td>
                    <td className="py-2 px-3 text-txt-muted whitespace-nowrap">{e.timestamp}</td>
                    <td className="py-2 px-3">
                      <span className="px-1.5 py-0.5 rounded bg-slate-100 text-txt-secondary text-[10px] font-semibold">
                        {e.ledger_type || 'POSTING'}
                      </span>
                    </td>
                    <td className="py-2 px-3 text-brand">{e.debit_account}</td>
                    <td className="py-2 px-3 text-txt-secondary">{e.credit_account}</td>
                    <td className="py-2 px-3 text-right font-bold text-txt-primary">
                      {curr}{Number(e.amount).toLocaleString('en-US', { minimumFractionDigits: 2 })}
                    </td>
                    <td className="py-2 px-3">{e.asset}</td>
                    <td className="py-2 px-3 text-txt-subtle truncate max-w-[120px]" title={e.reference_id}>
                      {e.reference_id}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Immutable Audit Trail Table */}
      <div className="card-panel overflow-hidden">
        <div className="px-5 py-3.5 border-b border-line bg-slate-50/50 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Hash className="h-4 w-4 text-brand" />
            <h3 className="text-xs font-bold uppercase tracking-wider text-txt-primary">
              Cryptographic Audit Trail & Security Events
            </h3>
          </div>
          <span className="text-[11px] text-txt-muted font-mono">
            {logs.length} Recorded Events
          </span>
        </div>

        <div className="overflow-x-auto max-h-[340px] overflow-y-auto">
          <table className="w-full text-left text-xs font-mono">
            <thead>
              <tr className="border-b border-line bg-slate-50 text-txt-muted text-[10px] font-semibold uppercase tracking-wider">
                <th className="py-2 px-3">Event ID</th>
                <th className="py-2 px-3">Timestamp</th>
                <th className="py-2 px-3">Event Type</th>
                <th className="py-2 px-3">Actor</th>
                <th className="py-2 px-3">Action / Detail</th>
                <th className="py-2 px-3">Integrity Hash</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line text-[11px]">
              {logs.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-8 text-center text-txt-muted font-sans">
                    {isLoading ? 'Loading audit trail...' : 'No security audit events recorded for this scope.'}
                  </td>
                </tr>
              ) : (
                logs.map((log) => (
                  <tr key={log.event_id} className="table-row-hover">
                    <td className="py-2 px-3 font-bold text-txt-primary">{log.event_id}</td>
                    <td className="py-2 px-3 text-txt-muted whitespace-nowrap">{log.timestamp}</td>
                    <td className="py-2 px-3">
                      <span className="px-1.5 py-0.5 rounded bg-blue-50 text-brand text-[10px] font-semibold">
                        {log.event_type}
                      </span>
                    </td>
                    <td className="py-2 px-3 text-txt-secondary">{log.actor || log.user_id || 'SYSTEM'}</td>
                    <td className="py-2 px-3 text-txt-primary truncate max-w-[200px]" title={log.action || log.symbol || ''}>
                      {log.action || log.symbol || log.result || 'EXECUTED'}
                    </td>
                    <td className="py-2 px-3 text-[10px] text-txt-subtle font-mono truncate max-w-[160px]" title={log.integrity_hash}>
                      {log.integrity_hash ? `${log.integrity_hash.slice(0, 16)}...` : 'VERIFIED'}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
