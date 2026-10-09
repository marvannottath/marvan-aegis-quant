'use client';

import React, { useState } from 'react';
import { useTradingContext } from '../../context/TradingContext';
import { api } from '../../lib/api';
import { Badge } from '../common/Badge';
import { Send, AlertTriangle, CheckCircle2 } from 'lucide-react';

export function QuickOrderConsole() {
  const { environment, workspace, portfolio, capital, refreshData } = useTradingContext();

  const [symbol, setSymbol] = useState<string>(
    workspace === 'CRYPTO' ? 'BTCUSDT' : workspace === 'INDIA' ? 'RELIANCE' : 'XAUUSD'
  );
  const [side, setSide] = useState<'BUY' | 'SELL'>('BUY');
  const [orderType, setOrderType] = useState<'MARKET' | 'LIMIT'>('MARKET');
  const [quantity, setQuantity] = useState<string>('0.001');
  const [price, setPrice] = useState<string>('');
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [resultMessage, setResultMessage] = useState<{ text: string; success: boolean } | null>(null);

  const curr = portfolio?.currency_symbol || '$';
  const isLive = environment === 'LIVE';

  const handleOrderSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
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
        environment: isLive ? 'BINANCE_LIVE' : 'BINANCE_TESTNET',
        workspace,
      });

      if (res.status === 'SUCCESS' || res.status === 'FILLED') {
        setResultMessage({
          text: `Order submitted: ${res.internal_order_id || 'SUCCESS'}`,
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
              className={`py-1 text-xs font-bold rounded transition ${
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
              className={`py-1 text-xs font-bold rounded transition ${
                side === 'SELL'
                  ? 'bg-loss text-white shadow-xs'
                  : 'text-txt-muted hover:text-txt-primary'
              }`}
            >
              SELL / SHORT
            </button>
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
            disabled={isSubmitting}
            className={`w-full py-2 px-3 text-xs font-bold rounded shadow-xs flex items-center justify-center gap-1.5 text-white transition disabled:opacity-50 ${
              side === 'BUY'
                ? 'bg-profit hover:bg-profit-dark'
                : 'bg-loss hover:bg-loss-dark'
            }`}
          >
            <Send className="h-3.5 w-3.5" />
            <span>
              {isSubmitting
                ? 'Validating Risk Gates...'
                : `Submit ${side} Order`}
            </span>
          </button>
        </form>
      </div>

      <div className="mt-3 pt-3 border-t border-line text-[11px] text-txt-subtle font-mono flex items-center justify-between">
        <span>Avail: {curr}{Number(capital?.available_cash ?? portfolio?.free_cash ?? 0).toFixed(2)}</span>
        <span>Tradeable: {curr}{Number(capital?.tradeable_capital ?? 0).toFixed(2)}</span>
      </div>
    </div>
  );
}
