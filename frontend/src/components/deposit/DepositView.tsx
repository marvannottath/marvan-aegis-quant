'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { useTradingContext } from '../../context/TradingContext';
import { Badge } from '../common/Badge';
import {
  CreditCard,
  ArrowDownToLine,
  CheckCircle2,
  Clock,
  ExternalLink,
  Copy,
  RefreshCw,
  ShieldCheck,
  Zap,
  Smartphone,
  QrCode,
  DollarSign,
  ChevronLeft,
  ChevronRight,
  ChevronsLeft,
  ChevronsRight,
} from 'lucide-react';

interface PaymentRecord {
  payment_id: string;
  user_id?: string;
  amount: number;
  currency: string;
  status: string;
  mode?: string;
  created_at: string;
  confirmed_at?: string;
  allocation_split?: {
    trading_capital: number;
    risk_reserve: number;
    vault_reserve: number;
  };
  link_id?: string;
}

export function DepositView() {
  const { environment, workspace, portfolio, refreshData } = useTradingContext();

  const [depositAmount, setDepositAmount] = useState('1000');
  const [depositCurrency, setDepositCurrency] = useState(workspace === 'INDIA' ? 'INR' : 'USDT');
  const [selectedMethod, setSelectedMethod] = useState('ALL');
  const [isGenerating, setIsGenerating] = useState(false);
  const [activeCreatedLink, setActiveCreatedLink] = useState<any>(null);

  // Transaction history state
  const [transactions, setTransactions] = useState<PaymentRecord[]>([]);
  const [isLoadingHistory, setIsLoadingHistory] = useState(true);
  const [filterStatus, setFilterStatus] = useState('ALL');
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);

  const curr = portfolio?.currency_symbol || '$';

  // Load unified transaction history
  const loadTransactions = useCallback(async () => {
    try {
      setIsLoadingHistory(true);
      const [histRes, linksRes] = await Promise.allSettled([
        fetch('/api/payments/history').then((r) => r.ok ? r.json() : []),
        fetch('/api/pay/links').then((r) => r.ok ? r.json() : { links: [] }),
      ]);

      const list: PaymentRecord[] = [];
      const seenIds = new Set<string>();

      if (histRes.status === 'fulfilled') {
        const rawPayments = Array.isArray(histRes.value) ? histRes.value : (histRes.value?.data || []);
        rawPayments.forEach((p: any) => {
          const id = p.payment_id || p.id;
          if (id && !seenIds.has(id)) {
            seenIds.add(id);
            list.push({
              payment_id: id,
              user_id: p.user_id,
              amount: parseFloat(p.amount) || 0,
              currency: p.currency || 'USDT',
              status: p.status || 'SUCCEEDED',
              mode: p.mode || 'UNIVERSAL_GATEWAY',
              created_at: p.created_at || 'Recently',
              confirmed_at: p.confirmed_at,
              allocation_split: p.allocation_split,
            });
          }
        });
      }

      if (linksRes.status === 'fulfilled' && linksRes.value?.links) {
        linksRes.value.links.forEach((l: any) => {
          const id = l.link_id;
          if (id && !seenIds.has(id)) {
            seenIds.add(id);
            list.push({
              payment_id: id,
              link_id: l.link_id,
              user_id: l.customer_name || 'Trader',
              amount: parseFloat(l.amount) || 0,
              currency: l.currency || 'INR',
              status: l.status === 'PAID' ? 'SUCCEEDED' : (l.status || 'PENDING'),
              mode: l.payment_method || 'HOSTED_CHECKOUT',
              created_at: l.created_at || 'Recently',
              confirmed_at: l.paid_at,
            });
          }
        });
      }

      // Sort newest first
      list.sort((a, b) => (b.created_at > a.created_at ? 1 : -1));
      setTransactions(list);
    } catch (e) {
      console.error('Failed to load transaction history', e);
    } finally {
      setIsLoadingHistory(false);
    }
  }, []);

  useEffect(() => {
    loadTransactions();
  }, [loadTransactions]);

  const handleCreateDepositLink = async () => {
    try {
      setIsGenerating(true);
      const res = await fetch('/api/pay/create-link', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          amount: parseFloat(depositAmount) || 1000,
          currency: depositCurrency,
          target_broker: workspace === 'INDIA' ? 'KOTAK_NEO_LIVE' : 'BINANCE_LIVE',
          title: `Aegis Quant Deposit (${depositCurrency})`,
          description: `Direct automated trading pool funding`,
        }),
      });
      const data = await res.json();
      if (data.status === 'SUCCESS' && data.link) {
        setActiveCreatedLink(data.link);
        await loadTransactions();
        await refreshData();
      } else {
        alert(data.message || 'Error generating link');
      }
    } catch (e: any) {
      alert(e.message || 'Error generating link');
    } finally {
      setIsGenerating(false);
    }
  };

  // Filtered & Paginated Transactions
  const filtered = transactions.filter((t) => {
    if (filterStatus === 'ALL') return true;
    if (filterStatus === 'SUCCEEDED') return t.status === 'SUCCEEDED' || t.status === 'PAID';
    if (filterStatus === 'PENDING') return t.status === 'PENDING' || t.status === 'INITIAL';
    return t.status === filterStatus;
  });

  const totalPages = Math.max(1, Math.ceil(filtered.length / pageSize));
  const paginated = filtered.slice((currentPage - 1) * pageSize, currentPage * pageSize);
  const startIndex = filtered.length === 0 ? 0 : (currentPage - 1) * pageSize + 1;
  const endIndex = Math.min(filtered.length, currentPage * pageSize);

  const presetAmounts = depositCurrency === 'INR' ? ['500', '1000', '2500', '5000', '10000'] : ['20', '50', '100', '250', '500'];

  return (
    <div className="space-y-6">
      {/* ── TOP BANNER: ACCOUNT SETTLED BALANCES & GATEWAYS ── */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-panel border border-line rounded-xl p-5 shadow-2xs flex flex-col justify-between">
          <div>
            <div className="text-xs font-semibold text-txt-muted uppercase tracking-wider">
              Settled Working Capital
            </div>
            <div className="text-2xl font-bold font-mono text-txt-primary mt-1">
              {curr}{portfolio?.total_equity?.toFixed(2) || '0.00'}
            </div>
          </div>
          <div className="mt-3 pt-3 border-t border-line text-xs text-txt-muted flex items-center justify-between">
            <span>Broker Destination:</span>
            <span className="font-semibold text-txt-primary">
              {workspace === 'INDIA' ? 'Kotak Neo (16MT6)' : workspace === 'CRYPTO' ? 'Binance Real Spot' : 'MT5 Broker'}
            </span>
          </div>
        </div>

        <div className="bg-panel border border-line rounded-xl p-5 shadow-2xs flex flex-col justify-between">
          <div>
            <div className="text-xs font-semibold text-txt-muted uppercase tracking-wider">
              Universal Payment Gateways
            </div>
            <div className="flex flex-wrap gap-1.5 mt-2">
              <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-blue-500/10 text-blue-500 border border-blue-500/20">
                Cards (Visa/MC)
              </span>
              <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-emerald-500/10 text-emerald-500 border border-emerald-500/20">
                UPI / NetBanking
              </span>
              <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-purple-500/10 text-purple-500 border border-purple-500/20">
                Apple Pay / GPay
              </span>
              <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-amber-500/10 text-amber-500 border border-amber-500/20">
                Binance Pay / Crypto
              </span>
            </div>
          </div>
          <div className="mt-3 pt-3 border-t border-line text-xs text-txt-muted flex items-center gap-1.5 text-emerald-500 font-semibold">
            <ShieldCheck className="h-4 w-4" /> 256-Bit Encrypted & Double-Entry Ledger Linked
          </div>
        </div>

        <div className="bg-panel border border-line rounded-xl p-5 shadow-2xs flex flex-col justify-between">
          <div>
            <div className="text-xs font-semibold text-txt-muted uppercase tracking-wider">
              Automatic Capital Allocation
            </div>
            <div className="space-y-1.5 mt-2 text-xs">
              <div className="flex justify-between">
                <span className="text-txt-muted">Trading Pool (85%):</span>
                <span className="font-mono font-semibold text-txt-primary">Direct Algorithmic Margin</span>
              </div>
              <div className="flex justify-between">
                <span className="text-txt-muted">Risk Reserve (10%):</span>
                <span className="font-mono font-semibold text-amber-500">Drawdown Cushion</span>
              </div>
              <div className="flex justify-between">
                <span className="text-txt-muted">Secured Vault (5%):</span>
                <span className="font-mono font-semibold text-purple-400">Lock-Profit Quarantine</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* ── SECTION 1: INSTANT DEPOSIT & CHECKOUT LINK GENERATOR ── */}
      <div className="bg-panel border border-line rounded-xl p-6 shadow-2xs">
        <div className="flex items-center gap-2 mb-4 pb-3 border-b border-line">
          <ArrowDownToLine className="h-5 w-5 text-brand" />
          <h2 className="text-sm font-bold text-txt-primary uppercase tracking-wide">
            Instant Deposit & Funding Hub
          </h2>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Deposit Form */}
          <div className="lg:col-span-2 space-y-4">
            <div>
              <label className="text-xs font-semibold text-txt-secondary block mb-1.5">
                Select Currency & Target Market
              </label>
              <div className="grid grid-cols-3 gap-2">
                <button
                  type="button"
                  onClick={() => setDepositCurrency('INR')}
                  className={`py-2 px-3 rounded-lg border text-xs font-bold transition cursor-pointer flex items-center justify-center gap-1.5 ${
                    depositCurrency === 'INR'
                      ? 'border-emerald-500 bg-emerald-500/10 text-emerald-500'
                      : 'border-line bg-panel-light text-txt-secondary hover:bg-slate-100 dark:hover:bg-panel'
                  }`}
                >
                  <span>🇮🇳 INR (₹)</span>
                  <span className="text-[10px] text-txt-muted">UPI/Card</span>
                </button>
                <button
                  type="button"
                  onClick={() => setDepositCurrency('USDT')}
                  className={`py-2 px-3 rounded-lg border text-xs font-bold transition cursor-pointer flex items-center justify-center gap-1.5 ${
                    depositCurrency === 'USDT'
                      ? 'border-brand bg-brand/10 text-brand'
                      : 'border-line bg-panel-light text-txt-secondary hover:bg-slate-100 dark:hover:bg-panel'
                  }`}
                >
                  <span>🪙 USDT ($)</span>
                  <span className="text-[10px] text-txt-muted">Crypto</span>
                </button>
                <button
                  type="button"
                  onClick={() => setDepositCurrency('USD')}
                  className={`py-2 px-3 rounded-lg border text-xs font-bold transition cursor-pointer flex items-center justify-center gap-1.5 ${
                    depositCurrency === 'USD'
                      ? 'border-blue-500 bg-blue-500/10 text-blue-500'
                      : 'border-line bg-panel-light text-txt-secondary hover:bg-slate-100 dark:hover:bg-panel'
                  }`}
                >
                  <span>🌐 USD ($)</span>
                  <span className="text-[10px] text-txt-muted">Cards/Pay</span>
                </button>
              </div>
            </div>

            <div>
              <label className="text-xs font-semibold text-txt-secondary block mb-1.5">
                Deposit Amount
              </label>
              <div className="flex gap-2 mb-2">
                {presetAmounts.map((amt) => (
                  <button
                    key={amt}
                    type="button"
                    onClick={() => setDepositAmount(amt)}
                    className={`flex-1 py-1 px-2 rounded-lg border text-xs font-mono font-semibold transition cursor-pointer ${
                      depositAmount === amt
                        ? 'border-brand bg-brand text-white'
                        : 'border-line bg-panel-light text-txt-secondary hover:border-txt-muted'
                    }`}
                  >
                    {depositCurrency === 'INR' ? `₹${amt}` : `$${amt}`}
                  </button>
                ))}
              </div>
              <input
                type="number"
                value={depositAmount}
                onChange={(e) => setDepositAmount(e.target.value)}
                className="w-full bg-panel-light border border-line rounded-lg px-3 py-2.5 text-base font-mono font-bold text-txt-primary focus:outline-none focus:border-brand"
                placeholder="Enter custom amount"
              />
            </div>

            <button
              onClick={handleCreateDepositLink}
              disabled={isGenerating}
              className="w-full py-3 rounded-xl bg-brand hover:bg-brand/90 text-white font-bold text-xs transition cursor-pointer flex items-center justify-center gap-2 shadow-sm"
            >
              {isGenerating ? (
                <RefreshCw className="h-4 w-4 animate-spin" />
              ) : (
                <Zap className="h-4 w-4" />
              )}
              <span>Generate 1-Click Hosted Checkout Link</span>
            </button>
          </div>

          {/* Active Checkout Card */}
          <div className="bg-panel-light/60 border border-line rounded-xl p-4 flex flex-col justify-between">
            {activeCreatedLink ? (
              <div className="space-y-3">
                <div className="flex items-center gap-2 text-emerald-500 text-xs font-bold">
                  <CheckCircle2 className="h-4 w-4" />
                  <span>Hosted Checkout Ready</span>
                </div>
                <div className="p-3 bg-panel border border-line rounded-lg space-y-1">
                  <div className="text-[11px] text-txt-muted">Amount to Pay:</div>
                  <div className="text-lg font-bold font-mono text-txt-primary">
                    {activeCreatedLink.currency === 'INR' ? '₹' : '$'}
                    {activeCreatedLink.amount}
                  </div>
                  <div className="text-[11px] font-mono text-txt-muted truncate">
                    ID: {activeCreatedLink.link_id}
                  </div>
                </div>

                <div className="space-y-2 pt-2">
                  <a
                    href={`/pay/${activeCreatedLink.link_id}`}
                    target="_blank"
                    rel="noreferrer"
                    className="w-full py-2.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs transition flex items-center justify-center gap-1.5 shadow-xs"
                  >
                    <span>Open Checkout Page</span>
                    <ExternalLink className="h-3.5 w-3.5" />
                  </a>

                  <button
                    onClick={() => {
                      navigator.clipboard.writeText(`${window.location.origin}/pay/${activeCreatedLink.link_id}`);
                      alert('Checkout URL copied to clipboard!');
                    }}
                    className="w-full py-2 rounded-lg bg-panel border border-line text-txt-primary hover:bg-slate-100 dark:hover:bg-panel font-semibold text-xs transition flex items-center justify-center gap-1.5 cursor-pointer"
                  >
                    <Copy className="h-3.5 w-3.5" />
                    <span>Copy Link URL</span>
                  </button>
                </div>
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center text-center p-6 space-y-3 h-full">
                <div className="p-3 bg-panel border border-line rounded-full text-txt-muted">
                  <CreditCard className="h-6 w-6" />
                </div>
                <div className="text-xs font-bold text-txt-primary">No Active Checkout</div>
                <p className="text-[11px] text-txt-muted leading-relaxed">
                  Enter an amount and click generate to launch a hosted checkout page with QR code, Card, Apple/Google Pay and UPI.
                </p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* ── SECTION 2: DETAILED TRANSACTION HISTORY TABLE ── */}
      <div className="card-panel overflow-hidden flex flex-col border border-line rounded-xl bg-panel shadow-2xs">
        {/* Table Header & Status Filter Tabs */}
        <div className="flex flex-wrap items-center justify-between gap-3 px-4 py-3 border-b border-line bg-slate-50/50 dark:bg-panel-light/30">
          <div className="flex items-center gap-2">
            <CreditCard className="h-4 w-4 text-brand" />
            <h3 className="text-xs font-bold uppercase tracking-wider text-txt-primary">
              Deposit & Funding Transaction Ledger
            </h3>
            <span className="text-xs font-mono font-semibold text-brand px-1.5 py-0.5 bg-blue-50 dark:bg-blue-950/40 border border-brand/20 rounded">
              {filtered.length} Recorded
            </span>
          </div>

          <div className="flex items-center gap-2 flex-wrap">
            <div className="flex items-center gap-1 bg-white dark:bg-panel p-0.5 rounded-lg border border-line">
              {['ALL', 'SUCCEEDED', 'PENDING'].map((st) => (
                <button
                  key={st}
                  onClick={() => {
                    setFilterStatus(st);
                    setCurrentPage(1);
                  }}
                  className={`px-2.5 py-0.5 text-[11px] font-semibold rounded transition cursor-pointer ${
                    filterStatus === st
                      ? 'bg-slate-900 dark:bg-brand text-white shadow-xs'
                      : 'text-txt-muted hover:text-txt-primary'
                  }`}
                >
                  {st}
                </button>
              ))}
            </div>

            <button
              onClick={() => loadTransactions()}
              disabled={isLoadingHistory}
              className="p-1.5 text-txt-muted hover:text-txt-primary hover:bg-slate-100 dark:hover:bg-panel rounded-lg border border-line transition cursor-pointer"
              title="Refresh transaction history"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${isLoadingHistory ? 'animate-spin' : ''}`} />
            </button>
          </div>
        </div>

        {/* Transactions Table */}
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-line bg-slate-50 dark:bg-panel-light/50 text-txt-muted text-[11px] font-semibold uppercase tracking-wider">
                <th className="py-2.5 px-3">Date & Time</th>
                <th className="py-2.5 px-3">Transaction ID</th>
                <th className="py-2.5 px-3">Gateway / Method</th>
                <th className="py-2.5 px-3 text-right">Amount</th>
                <th className="py-2.5 px-3 text-right">Trading Capital (85%)</th>
                <th className="py-2.5 px-3 text-right">Vault Reserve (5%)</th>
                <th className="py-2.5 px-3 text-center">Status</th>
                <th className="py-2.5 px-3 text-center">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {paginated.length === 0 ? (
                <tr>
                  <td colSpan={8} className="py-12 text-center text-txt-muted">
                    <div className="flex flex-col items-center justify-center gap-2 max-w-sm mx-auto">
                      <Clock className="h-8 w-8 text-txt-subtle stroke-[1.5]" />
                      <span className="font-bold text-xs text-txt-primary">No transactions found</span>
                      <span className="text-[11px] text-txt-muted">
                        All incoming Stripe, Binance Pay, UPI, and checkout funding events will appear here in real-time.
                      </span>
                    </div>
                  </td>
                </tr>
              ) : (
                paginated.map((tx) => {
                  const isSucceeded = tx.status === 'SUCCEEDED' || tx.status === 'PAID';
                  const sym = tx.currency === 'INR' ? '₹' : '$';
                  return (
                    <tr key={tx.payment_id} className="hover:bg-slate-50/60 dark:hover:bg-panel-light/40 transition">
                      <td className="py-2 px-3 font-mono text-[11px] text-txt-muted">
                        {tx.created_at}
                      </td>
                      <td className="py-2 px-3 font-mono text-[11px] font-semibold text-txt-primary">
                        {tx.payment_id}
                      </td>
                      <td className="py-2 px-3">
                        <span className="px-2 py-0.5 rounded text-[10px] font-mono font-semibold bg-panel-light border border-line text-txt-secondary">
                          {tx.mode || 'UNIVERSAL_GATEWAY'}
                        </span>
                      </td>
                      <td className="py-2 px-3 text-right font-mono font-bold text-txt-primary">
                        {sym}{tx.amount.toFixed(2)}
                      </td>
                      <td className="py-2 px-3 text-right font-mono text-txt-secondary">
                        {sym}{(tx.allocation_split?.trading_capital ?? (tx.amount * 0.85)).toFixed(2)}
                      </td>
                      <td className="py-2 px-3 text-right font-mono text-purple-400 font-semibold">
                        {sym}{(tx.allocation_split?.vault_reserve ?? (tx.amount * 0.05)).toFixed(2)}
                      </td>
                      <td className="py-2 px-3 text-center">
                        <Badge variant={isSucceeded ? 'success' : 'warning'} size="sm">
                          {tx.status}
                        </Badge>
                      </td>
                      <td className="py-2 px-3 text-center">
                        {tx.link_id ? (
                          <a
                            href={`/pay/${tx.link_id}`}
                            target="_blank"
                            rel="noreferrer"
                            className="text-brand hover:underline font-semibold text-[11px] flex items-center justify-center gap-1"
                          >
                            <span>Checkout</span>
                            <ExternalLink className="h-3 w-3" />
                          </a>
                        ) : (
                          <span className="text-[11px] text-txt-muted">Settled</span>
                        )}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        {/* ── PAGINATION BAR ── */}
        <div className="flex flex-wrap items-center justify-between gap-3 px-4 py-3 border-t border-line bg-slate-50/40 dark:bg-panel-light/20 text-xs">
          <div className="text-txt-muted">
            Showing <strong className="text-txt-primary">{startIndex}</strong> -{' '}
            <strong className="text-txt-primary">{endIndex}</strong> of{' '}
            <strong className="text-txt-primary">{filtered.length}</strong> transactions
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setCurrentPage(1)}
              disabled={currentPage <= 1}
              className="p-1 rounded border border-line bg-panel text-txt-muted hover:text-txt-primary disabled:opacity-40 transition"
              title="First Page"
            >
              <ChevronsLeft className="h-4 w-4" />
            </button>
            <button
              onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
              disabled={currentPage <= 1}
              className="p-1 rounded border border-line bg-panel text-txt-muted hover:text-txt-primary disabled:opacity-40 transition"
              title="Previous Page"
            >
              <ChevronLeft className="h-4 w-4" />
            </button>
            <span className="px-2 py-0.5 font-mono text-xs font-semibold text-txt-primary bg-panel border border-line rounded">
              {currentPage} / {totalPages}
            </span>
            <button
              onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
              disabled={currentPage >= totalPages}
              className="p-1 rounded border border-line bg-panel text-txt-muted hover:text-txt-primary disabled:opacity-40 transition"
              title="Next Page"
            >
              <ChevronRight className="h-4 w-4" />
            </button>
            <button
              onClick={() => setCurrentPage(totalPages)}
              disabled={currentPage >= totalPages}
              className="p-1 rounded border border-line bg-panel text-txt-muted hover:text-txt-primary disabled:opacity-40 transition"
              title="Last Page"
            >
              <ChevronsRight className="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
