'use client';

import React, { useState, useEffect } from 'react';
import { useTradingContext, DEFAULT_ACCOUNTS } from '../../context/TradingContext';
import { api } from '../../lib/api';
import { Badge } from '../common/Badge';
import { Send, AlertTriangle, CheckCircle2, Lock, KeyRound } from 'lucide-react';
import { ConnectBrokerModal } from '../common/ConnectBrokerModal';

interface QuickOrderConsoleProps {
  activeSymbol?: string;
  onSymbolChange?: (symbol: string) => void;
}

export function QuickOrderConsole({ activeSymbol, onSymbolChange }: QuickOrderConsoleProps = {}) {
  const { environment, workspace, portfolio, capital, envStatus, refreshData } = useTradingContext();

  const [symbol, setSymbol] = useState<string>(
    activeSymbol || (workspace === 'CRYPTO' ? 'BTCUSDT' : workspace === 'INDIA' ? 'RELIANCE' : 'XAUUSD')
  );
  const [side, setSide] = useState<'BUY' | 'SELL'>('BUY');
  const [orderType, setOrderType] = useState<'MARKET' | 'LIMIT'>('MARKET');
  const [quantity, setQuantity] = useState<string>('0.001');
  const [price, setPrice] = useState<string>('');
  const [product, setProduct] = useState<string>('SPOT');
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [isBrokerModalOpen, setIsBrokerModalOpen] = useState<boolean>(false);
  const [resultMessage, setResultMessage] = useState<{ text: string; success: boolean } | null>(null);

  // Sync symbol when activeSymbol prop changes from parent
  useEffect(() => {
    if (activeSymbol && activeSymbol !== symbol) {
      setSymbol(activeSymbol);
    }
  }, [activeSymbol]);

  // Set defaults when workspace changes
  useEffect(() => {
    if (workspace === 'INDIA') {
      setSymbol('RELIANCE');
      setProduct('MIS');
      setQuantity('1');
    } else if (workspace === 'FOREX_GOLD') {
      setSymbol('XAUUSD');
      setProduct('INTRADAY');
      setQuantity('0.1');
    } else {
      setSymbol('BTCUSDT');
      setProduct('SPOT');
      setQuantity('0.001');
    }
  }, [workspace]);

  const curr = portfolio?.currency_symbol || (workspace === 'INDIA' ? '₹' : '$');
  const isLive = environment === 'LIVE';

  const isLiveDisconnected = isLive && (portfolio?.broker_connected === false || portfolio?.total_equity === null);
  const isLiveLocked = isLive && (envStatus?.live_trading_enabled_flag === false || envStatus?.live_trading !== 'ACTIVE');
  const isKillSwitchActive = envStatus?.kill_switch_active === true;
  const tradeableVal = capital?.tradeable_capital;
  const isTradeableZeroOrNull = tradeableVal === null || tradeableVal === undefined || tradeableVal <= 0;

  const isOrderBlocked = isLiveDisconnected || isKillSwitchActive || isLiveLocked || (isLive && isTradeableZeroOrNull);

  let lockReasonText = '';
  if (isLiveDisconnected) {
    lockReasonText = 'BROKER DISCONNECTED';
  } else if (isKillSwitchActive) {
    lockReasonText = 'KILL SWITCH ACTIVE';
  } else if (isLiveLocked) {
    lockReasonText = 'LIVE TRADING LOCKED';
  } else if (isLive && isTradeableZeroOrNull) {
    lockReasonText = 'NO TRADEABLE CAPITAL';
  }

  // Product options per workspace
  const productOptions =
    workspace === 'INDIA'
      ? [
          { id: 'MIS', label: 'INTRADAY (MIS)' },
          { id: 'CNC', label: 'DELIVERY (CNC)' },
          { id: 'NRML', label: 'F&O (NRML)' },
        ]
      : workspace === 'FOREX_GOLD'
      ? [
          { id: 'INTRADAY', label: 'INTRADAY (DAY)' },
          { id: 'SWING', label: 'SWING (OVERNIGHT)' },
        ]
      : [
          { id: 'SPOT', label: 'SPOT (CASH)' },
          { id: 'USDT_M_FUTURES', label: 'USDT-M PERP' },
        ];

  const handleOrderSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (isOrderBlocked) return;
    setResultMessage(null);

    const qty = parseFloat(quantity);
    if (isNaN(qty) || qty <= 0) {
      setResultMessage({ text: 'Quantity must be positive.', success: false });
      return;
    }

    try {
      setIsSubmitting(true);
      const res = await api.submitOrder({
        symbol,
        side,
        quantity: qty,
        price: price ? parseFloat(price) : undefined,
        order_type: orderType,
        environment: isLive ? 'LIVE' : 'PAPER',
        workspace,
        product,
      });

      if (res.status === 'SUCCESS' || res.status === 'FILLED') {
        setResultMessage({
          text: `Order submitted: ${res.internal_order_id || 'SUCCESS'} (${product})`,
          success: true,
        });
        await refreshData();
      } else {
        setResultMessage({
          text: res.message || 'Order rejected by broker or risk gate.',
          success: false,
        });
      }
    } catch (err: any) {
      setResultMessage({
        text: err?.message || 'Order failed during pre-flight risk checks.',
        success: false,
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="card-panel p-4 flex flex-col justify-between">
      <div>
        <div className="flex items-center justify-between pb-3 border-b border-line">
          <h3 className="text-xs font-bold uppercase tracking-wider text-txt-primary">
            Quick Execution Console
          </h3>
          <Badge variant={isLive ? 'live' : 'demo'} size="sm">
            {environment} • {workspace}
          </Badge>
        </div>

        <form onSubmit={handleOrderSubmit} className="mt-3 space-y-3">
          {/* Side Selector (BUY / SELL) */}
          <div className="grid grid-cols-2 gap-2 p-0.5 bg-slate-100 rounded-md">
            <button
              type="button"
              onClick={() => setSide('BUY')}
              className={`py-1 text-xs font-bold rounded transition cursor-pointer ${
                side === 'BUY'
                  ? 'bg-profit text-white shadow-xs'
                  : 'text-txt-muted hover:text-txt-primary'
              }`}
            >
              BUY / LONG
            </button>
            <button
              type="button"
              onClick={() => setSide('SELL')}
              className={`py-1 text-xs font-bold rounded transition cursor-pointer ${
                side === 'SELL'
                  ? 'bg-loss text-white shadow-xs'
                  : 'text-txt-muted hover:text-txt-primary'
              }`}
            >
              SELL / SHORT
            </button>
          </div>

          {/* Trade Mode / Product Type (Intraday, Delivery, Futures) */}
          <div>
            <label className="block text-[11px] font-semibold text-txt-muted uppercase mb-1">
              Trade Mode / Product
            </label>
            <div className={`grid gap-1.5 p-0.5 bg-slate-100 rounded-md ${productOptions.length === 3 ? 'grid-cols-3' : 'grid-cols-2'}`}>
              {productOptions.map((opt) => (
                <button
                  key={opt.id}
                  type="button"
                  onClick={() => setProduct(opt.id)}
                  className={`py-1 px-1.5 text-[11px] font-bold rounded transition cursor-pointer truncate ${
                    product === opt.id
                      ? 'bg-white text-brand shadow-xs border border-line'
                      : 'text-txt-muted hover:text-txt-primary'
                  }`}
                  title={opt.label}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

          {/* Symbol & Order Type */}
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="block text-[11px] font-semibold text-txt-muted uppercase mb-1">
                Instrument
              </label>
              <input
                type="text"
                value={symbol}
                onChange={(e) => setSymbol(e.target.value.toUpperCase())}
                className="w-full px-2.5 py-1.5 text-xs font-mono font-semibold rounded border border-line bg-white text-txt-primary focus:outline-none focus:ring-1 focus:ring-brand"
              />
            </div>
            <div>
              <label className="block text-[11px] font-semibold text-txt-muted uppercase mb-1">
                Order Type
              </label>
              <select
                value={orderType}
                onChange={(e) => setOrderType(e.target.value as any)}
                className="w-full px-2.5 py-1.5 text-xs font-mono font-semibold rounded border border-line bg-white text-txt-primary focus:outline-none focus:ring-1 focus:ring-brand"
              >
                <option value="MARKET">MARKET</option>
                <option value="LIMIT">LIMIT</option>
              </select>
            </div>
          </div>

          {/* Quantity & Price */}
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="block text-[11px] font-semibold text-txt-muted uppercase mb-1">
                Quantity
              </label>
              <input
                type="number"
                step="any"
                value={quantity}
                onChange={(e) => setQuantity(e.target.value)}
                className="w-full px-2.5 py-1.5 text-xs font-mono rounded border border-line bg-white text-txt-primary focus:outline-none focus:ring-1 focus:ring-brand"
              />
            </div>
            <div>
              <label className="block text-[11px] font-semibold text-txt-muted uppercase mb-1">
                Limit Price ({curr})
              </label>
              <input
                type="number"
                step="any"
                disabled={orderType === 'MARKET'}
                placeholder={orderType === 'MARKET' ? 'Market' : 'Price'}
                value={price}
                onChange={(e) => setPrice(e.target.value)}
                className="w-full px-2.5 py-1.5 text-xs font-mono rounded border border-line bg-white text-txt-primary disabled:bg-slate-100 disabled:text-txt-subtle focus:outline-none focus:ring-1 focus:ring-brand"
              />
            </div>
          </div>

          {/* Execution Guard Banner */}
          {isOrderBlocked && (
            <div className="p-2.5 rounded bg-amber-50 border border-amber-200 text-amber-900 text-xs flex items-start gap-2">
              <Lock className="h-4 w-4 shrink-0 text-amber-600 mt-0.5" />
              <div className="space-y-0.5 leading-tight">
                <span className="font-semibold block">Execution Guard: {lockReasonText}</span>
                <span className="text-[11px] text-amber-700 block">
                  {isLiveDisconnected
                    ? `Live ${DEFAULT_ACCOUNTS[workspace]?.LIVE?.broker || 'broker'} is unauthenticated. Real broker credentials are required before submitting live orders.`
                    : isKillSwitchActive
                    ? 'Emergency kill switch is active across the system. All order submission is halted.'
                    : isLiveLocked
                    ? 'Live trading is locked. Pass SUPER_ADMIN TOTP verification in Settings to enable live execution.'
                    : 'Insufficient tradeable capital. Free cash and margin buffers do not meet minimum order thresholds.'}
                </span>
              </div>
            </div>
          )}

          {/* Feedback banner */}
          {resultMessage && (
            <div
              className={`p-2 rounded text-xs flex items-start gap-1.5 ${
                resultMessage.success
                  ? 'bg-emerald-50 text-profit border border-emerald-200'
                  : 'bg-red-50 text-loss border border-red-200'
              }`}
            >
              {resultMessage.success ? (
                <CheckCircle2 className="h-4 w-4 shrink-0 mt-0.5" />
              ) : (
                <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5" />
              )}
              <span className="leading-tight">{resultMessage.text}</span>
            </div>
          )}

          {/* Submit Button */}
          <button
            type="submit"
            disabled={isSubmitting || isOrderBlocked}
            className={`w-full py-2.5 px-3 text-xs font-bold rounded shadow-xs flex items-center justify-center gap-1.5 transition cursor-pointer ${
              isOrderBlocked
                ? 'bg-slate-200 text-slate-500 cursor-not-allowed border border-slate-300'
                : side === 'BUY'
                ? 'bg-profit hover:bg-profit-dark text-white disabled:opacity-50'
                : 'bg-loss hover:bg-loss-dark text-white disabled:opacity-50'
            }`}
          >
            {isSubmitting ? (
              <span>Submitting Order...</span>
            ) : isOrderBlocked ? (
              <span className="flex items-center gap-1">
                <Lock className="h-3 w-3" />
                <span>Execution Blocked</span>
              </span>
            ) : (
              <span className="flex items-center gap-1">
                <Send className="h-3 w-3" />
                <span>
                  Submit {side} Order ({product})
                </span>
              </span>
            )}
          </button>
        </form>
      </div>

      {/* Connect Broker Modal Trigger (if disconnected) */}
      {isLiveDisconnected && (
        <div className="mt-3 pt-3 border-t border-line">
          <button
            type="button"
            onClick={() => setIsBrokerModalOpen(true)}
            className="w-full py-2 px-3 rounded-md bg-blue-50 hover:bg-blue-100 text-brand text-xs font-bold transition flex items-center justify-center gap-1.5 border border-blue-200 cursor-pointer"
          >
            <KeyRound className="h-3.5 w-3.5" />
            <span>Connect {DEFAULT_ACCOUNTS[workspace]?.LIVE?.broker || 'Live Broker'}</span>
          </button>
        </div>
      )}

      {/* Broker Credentials Modal */}
      <ConnectBrokerModal
        isOpen={isBrokerModalOpen}
        onClose={() => setIsBrokerModalOpen(false)}
        defaultCategory={workspace}
      />
    </div>
  );
}
