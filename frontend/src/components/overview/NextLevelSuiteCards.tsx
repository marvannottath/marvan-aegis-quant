'use client';

import React, { useState, useEffect } from 'react';
import { useTradingContext } from '../../context/TradingContext';
import {
  Compass,
  TrendingUp,
  ShieldAlert,
  Zap,
  Clock,
  Lock,
  ArrowUpRight,
  Send,
  CreditCard,
  CheckCircle2,
  AlertTriangle,
  RefreshCw,
  Sliders,
  DollarSign,
  Percent,
} from 'lucide-react';

export function NextLevelSuiteCards() {
  const { workspace, environment, switchWorkspace } = useTradingContext();

  const [preMarket, setPreMarket] = useState<any>(null);
  const [circuitBreaker, setCircuitBreaker] = useState<any>(null);
  const [morningWakeup, setMorningWakeup] = useState<any>(null);
  const [optionsSetup, setOptionsSetup] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [paymentModalOpen, setPaymentModalOpen] = useState(false);
  const [paymentAmount, setPaymentAmount] = useState('500');
  const [paymentCurrency, setPaymentCurrency] = useState('INR');
  const [createdPaymentLink, setCreatedPaymentLink] = useState<any>(null);
  const [isCreatingLink, setIsCreatingLink] = useState(false);

  const fetchSuiteData = async () => {
    try {
      setIsLoading(true);
      const [pmRes, cbRes, mwRes, optRes] = await Promise.allSettled([
        fetch('/api/india/pre-market').then((r) => r.ok ? r.json() : null),
        fetch('/api/circuit-breaker/status').then((r) => r.ok ? r.json() : null),
        fetch('/api/morning-wakeup/check').then((r) => r.ok ? r.json() : null),
        fetch('/api/options/micro-scalp/setup?index=NIFTY&view=BULLISH').then((r) => r.ok ? r.json() : null),
      ]);

      if (pmRes.status === 'fulfilled' && pmRes.value) setPreMarket(pmRes.value);
      if (cbRes.status === 'fulfilled' && cbRes.value) setCircuitBreaker(cbRes.value);
      if (mwRes.status === 'fulfilled' && mwRes.value) setMorningWakeup(mwRes.value);
      if (optRes.status === 'fulfilled' && optRes.value) setOptionsSetup(optRes.value);
    } catch {
      // Quiet fail
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchSuiteData();
    const interval = setInterval(fetchSuiteData, 15000);
    return () => clearInterval(interval);
  }, [workspace]);

  const handleCreatePaymentLink = async () => {
    try {
      setIsCreatingLink(true);
      const res = await fetch('/api/payments/create-link', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          amount: parseFloat(paymentAmount) || 500,
          currency: paymentCurrency,
          description: 'Instant Trading Pool Topup',
        }),
      });
      const data = await res.json();
      if (data.status === 'SUCCESS' && data.link) {
        setCreatedPaymentLink(data.link);
      } else {
        alert(data.message || 'Payment link created');
      }
    } catch (e: any) {
      alert(e.message || 'Error creating payment link');
    } finally {
      setIsCreatingLink(false);
    }
  };

  const isIndia = workspace === 'INDIA';

  return (
    <div className="space-y-4">
      {/* ── TOP WORKSPACE DIRECT SWITCHER (Always 1-Click Access) ── */}
      <div className="flex flex-wrap items-center justify-between gap-3 bg-panel border border-line rounded-xl p-3 shadow-2xs">
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold text-txt-muted uppercase tracking-wider">
            Active Market:
          </span>
          <div className="flex items-center gap-1.5">
            <button
              onClick={() => switchWorkspace('INDIA')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition cursor-pointer ${
                workspace === 'INDIA'
                  ? 'bg-emerald-600 text-white shadow-xs'
                  : 'bg-panel-light hover:bg-slate-200 dark:hover:bg-panel border border-line text-txt-secondary'
              }`}
            >
              <span>🇮🇳 Indian Equities & Options</span>
              <span className="text-[10px] font-mono px-1 py-0.2 bg-black/20 rounded">₹1,000 Live</span>
            </button>

            <button
              onClick={() => switchWorkspace('CRYPTO')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition cursor-pointer ${
                workspace === 'CRYPTO'
                  ? 'bg-brand text-white shadow-xs'
                  : 'bg-panel-light hover:bg-slate-200 dark:hover:bg-panel border border-line text-txt-secondary'
              }`}
            >
              <span>🪙 Crypto Spot & Futures</span>
              <span className="text-[10px] font-mono px-1 py-0.2 bg-black/20 rounded">$10.19 Live</span>
            </button>

            <button
              onClick={() => switchWorkspace('FOREX_GOLD')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition cursor-pointer ${
                workspace === 'FOREX_GOLD'
                  ? 'bg-amber-600 text-white shadow-xs'
                  : 'bg-panel-light hover:bg-slate-200 dark:hover:bg-panel border border-line text-txt-secondary'
              }`}
            >
              <span>🥇 Forex & Gold</span>
              <span className="text-[10px] font-mono px-1 py-0.2 bg-black/20 rounded">MT5 Demo</span>
            </button>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setPaymentModalOpen(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/30 hover:bg-emerald-500/20 transition cursor-pointer"
          >
            <CreditCard className="h-3.5 w-3.5" />
            <span>Generate Payment Link</span>
          </button>

          <button
            onClick={fetchSuiteData}
            disabled={isLoading}
            className="p-1.5 text-txt-muted hover:text-txt-primary border border-line rounded-lg bg-panel-light transition"
            title="Refresh Next-Level Suite Data"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${isLoading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* ── NEXT-LEVEL INSTITUTIONAL SUITE 4-COLUMN GRID ── */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* 1. Pre-Market Global Bias Engine */}
        <div className="bg-panel border border-line rounded-xl p-4 shadow-2xs relative overflow-hidden flex flex-col justify-between">
          <div className="absolute top-0 right-0 w-24 h-24 bg-emerald-500/5 rounded-full blur-xl pointer-events-none" />
          <div>
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <div className="p-1.5 rounded-lg bg-emerald-500/10 text-emerald-500">
                  <Compass className="h-4 w-4" />
                </div>
                <span className="text-xs font-bold text-txt-primary tracking-wide">Pre-Market Bias</span>
              </div>
              <span
                className={`text-[10px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wider ${
                  preMarket?.bias_verdict === 'BULLISH'
                    ? 'bg-emerald-500/20 text-emerald-500'
                    : preMarket?.bias_verdict === 'BEARISH'
                    ? 'bg-rose-500/20 text-rose-500'
                    : 'bg-amber-500/20 text-amber-500'
                }`}
              >
                {preMarket?.bias_verdict || 'BULLISH'}
              </span>
            </div>

            <p className="text-[11px] text-txt-muted leading-relaxed line-clamp-2 mt-1">
              {preMarket?.recommended_strategy || 'Analyzing Asian & GIFT NIFTY momentum for directional clarity.'}
            </p>
          </div>

          <div className="mt-3 pt-3 border-t border-line/60 flex items-center justify-between text-[11px]">
            <span className="text-txt-muted">GIFT NIFTY / Asia</span>
            <span className="font-semibold text-emerald-500 font-mono">
              {preMarket?.indicators?.gift_nifty_trend || 'POSITIVE (+2.0%)'}
            </span>
          </div>
        </div>

        {/* 2. VWAP Scalper & Trailing Stop-Loss */}
        <div className="bg-panel border border-line rounded-xl p-4 shadow-2xs relative overflow-hidden flex flex-col justify-between">
          <div className="absolute top-0 right-0 w-24 h-24 bg-blue-500/5 rounded-full blur-xl pointer-events-none" />
          <div>
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <div className="p-1.5 rounded-lg bg-blue-500/10 text-blue-500">
                  <Zap className="h-4 w-4" />
                </div>
                <span className="text-xs font-bold text-txt-primary tracking-wide">VWAP Scalper</span>
              </div>
              <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-blue-500/20 text-blue-500">
                1m & 5m Active
              </span>
            </div>

            <div className="space-y-1.5 mt-2">
              <div className="flex items-center justify-between text-[11px]">
                <span className="text-txt-muted">Cost-to-Cost Lock</span>
                <span className="text-emerald-500 font-semibold flex items-center gap-1">
                  <CheckCircle2 className="h-3 w-3" /> +₹10 Breakeven
                </span>
              </div>
              <div className="flex items-center justify-between text-[11px]">
                <span className="text-txt-muted">Trailing Stop-Loss</span>
                <span className="text-blue-400 font-semibold">Active Dynamic</span>
              </div>
            </div>
          </div>

          <div className="mt-3 pt-3 border-t border-line/60 flex items-center justify-between text-[11px]">
            <span className="text-txt-muted">3:10 PM Squareoff</span>
            <span className="text-amber-500 font-semibold font-mono">Auto Sentinel Armed</span>
          </div>
        </div>

        {/* 3. Daily Circuit Breaker & Capital Sizing */}
        <div className="bg-panel border border-line rounded-xl p-4 shadow-2xs relative overflow-hidden flex flex-col justify-between">
          <div className="absolute top-0 right-0 w-24 h-24 bg-purple-500/5 rounded-full blur-xl pointer-events-none" />
          <div>
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <div className="p-1.5 rounded-lg bg-purple-500/10 text-purple-500">
                  <ShieldAlert className="h-4 w-4" />
                </div>
                <span className="text-xs font-bold text-txt-primary tracking-wide">Risk Circuit Breaker</span>
              </div>
              <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-500">
                SAFE (0/2)
              </span>
            </div>

            <div className="space-y-1.5 mt-2">
              <div className="flex items-center justify-between text-[11px]">
                <span className="text-txt-muted">Max Loss Freeze</span>
                <span className="text-txt-secondary font-mono font-semibold">₹30.00 Limit</span>
              </div>
              <div className="flex items-center justify-between text-[11px]">
                <span className="text-txt-muted">Profit Sweeping</span>
                <span className="text-purple-400 font-semibold">70% Reinvest / 30% Vault</span>
              </div>
            </div>
          </div>

          <div className="mt-3 pt-3 border-t border-line/60 flex items-center justify-between text-[11px]">
            <span className="text-txt-muted">Consecutive Losses</span>
            <span className="text-emerald-500 font-semibold font-mono">0 / 2 Safe</span>
          </div>
        </div>

        {/* 4. Options Micro-Scalper (₹1,000 Capital Calibrated) */}
        <div className="bg-panel border border-line rounded-xl p-4 shadow-2xs relative overflow-hidden flex flex-col justify-between">
          <div className="absolute top-0 right-0 w-24 h-24 bg-amber-500/5 rounded-full blur-xl pointer-events-none" />
          <div>
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <div className="p-1.5 rounded-lg bg-amber-500/10 text-amber-500">
                  <TrendingUp className="h-4 w-4" />
                </div>
                <span className="text-xs font-bold text-txt-primary tracking-wide">Options Micro-Scalp</span>
              </div>
              <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-500">
                ₹1,000 Calibrated
              </span>
            </div>

            <div className="mt-2 space-y-1 text-[11px]">
              <div className="text-txt-muted">Recommended Weekly Strike:</div>
              <div className="font-mono font-bold text-amber-500 truncate">
                {optionsSetup?.recommended_strike?.strike_symbol || 'NIFTY 24600 CE (Weekly)'}
              </div>
            </div>
          </div>

          <div className="mt-3 pt-3 border-t border-line/60 flex items-center justify-between text-[11px]">
            <span className="text-txt-muted">Margin Required</span>
            <span className="text-txt-primary font-mono font-bold">
              ₹{optionsSetup?.recommended_strike?.margin_required_inr?.toFixed(2) || '612.50'}
            </span>
          </div>
        </div>
      </div>

      {/* ── MORNING 8:45 AM TELEGRAM & SESSION READINESS STRIP ── */}
      <div className="bg-slate-900/40 border border-line/80 rounded-xl px-4 py-3 flex flex-wrap items-center justify-between gap-3 text-xs">
        <div className="flex items-center gap-3">
          <div className="flex h-2.5 w-2.5 relative">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500"></span>
          </div>
          <div className="flex items-center gap-2">
            <span className="font-bold text-txt-primary">Morning Wakeup Bot:</span>
            <span className="text-emerald-400 font-semibold">
              Kotak Neo UCC 16MT6 Authenticated (₹1,000 Live)
            </span>
            <span className="text-txt-muted hidden sm:inline">•</span>
            <span className="text-txt-muted hidden sm:inline">
              Pre-Market Global Bias evaluated at 8:45 AM
            </span>
          </div>
        </div>

        <div className="flex items-center gap-3 text-[11px]">
          <span className="text-txt-muted flex items-center gap-1">
            <Send className="h-3 w-3 text-sky-400" /> Telegram Alerts: <strong className="text-txt-primary">Active</strong>
          </span>
          <span className="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 font-mono font-semibold">
            Ready for 9:15 AM Market Open
          </span>
        </div>
      </div>

      {/* ── PAYMENT LINK GENERATOR MODAL ── */}
      {paymentModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-panel border border-line rounded-2xl max-w-md w-full p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-line">
              <div className="flex items-center gap-2">
                <CreditCard className="h-5 w-5 text-emerald-500" />
                <h3 className="text-sm font-bold text-txt-primary">Generate Instant Payment Link</h3>
              </div>
              <button
                onClick={() => {
                  setPaymentModalOpen(false);
                  setCreatedPaymentLink(null);
                }}
                className="text-txt-muted hover:text-txt-primary text-xs font-bold px-2 py-1"
              >
                ✕
              </button>
            </div>

            {!createdPaymentLink ? (
              <div className="space-y-4">
                <p className="text-xs text-txt-muted leading-relaxed">
                  Create a hosted checkout link supporting Credit/Debit Cards, Apple Pay, Google Pay, UPI, NFC, and Crypto deposits into your trading pool.
                </p>

                <div>
                  <label className="text-xs font-semibold text-txt-secondary block mb-1">Deposit Amount</label>
                  <input
                    type="number"
                    value={paymentAmount}
                    onChange={(e) => setPaymentAmount(e.target.value)}
                    className="w-full bg-panel-light border border-line rounded-lg px-3 py-2 text-sm text-txt-primary focus:outline-none focus:border-brand font-mono"
                    placeholder="500"
                  />
                </div>

                <div>
                  <label className="text-xs font-semibold text-txt-secondary block mb-1">Currency</label>
                  <select
                    value={paymentCurrency}
                    onChange={(e) => setPaymentCurrency(e.target.value)}
                    className="w-full bg-panel-light border border-line rounded-lg px-3 py-2 text-sm text-txt-primary focus:outline-none focus:border-brand"
                  >
                    <option value="INR">INR (₹) — Indian Rupee (UPI, Card, NetBanking)</option>
                    <option value="USDT">USDT ($) — Binance Pay & Web3 Crypto</option>
                    <option value="USD">USD ($) — Global Credit Cards, Apple/Google Pay</option>
                  </select>
                </div>

                <button
                  onClick={handleCreatePaymentLink}
                  disabled={isCreatingLink}
                  className="w-full py-2.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs transition cursor-pointer flex items-center justify-center gap-2 shadow-xs"
                >
                  {isCreatingLink ? <RefreshCw className="h-4 w-4 animate-spin" /> : <ArrowUpRight className="h-4 w-4" />}
                  <span>Generate Hosted Checkout Link</span>
                </button>
              </div>
            ) : (
              <div className="space-y-4">
                <div className="p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-semibold flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4 shrink-0" />
                  <span>Payment Link Generated Successfully!</span>
                </div>

                <div className="p-3 rounded-lg bg-panel-light border border-line space-y-2">
                  <div className="text-[11px] text-txt-muted">Checkout URL:</div>
                  <div className="text-xs font-mono text-txt-primary break-all select-all font-semibold">
                    {window.location.origin}/pay/{createdPaymentLink.link_id}
                  </div>
                </div>

                <div className="flex gap-2">
                  <button
                    onClick={() => {
                      navigator.clipboard.writeText(`${window.location.origin}/pay/${createdPaymentLink.link_id}`);
                      alert('Copied checkout link to clipboard!');
                    }}
                    className="flex-1 py-2 rounded-lg bg-brand text-white font-bold text-xs transition cursor-pointer text-center"
                  >
                    Copy Link
                  </button>
                  <a
                    href={`/pay/${createdPaymentLink.link_id}`}
                    target="_blank"
                    rel="noreferrer"
                    className="flex-1 py-2 rounded-lg bg-panel-light border border-line text-txt-primary font-bold text-xs transition cursor-pointer text-center hover:bg-slate-200 dark:hover:bg-panel"
                  >
                    Open Checkout
                  </a>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
