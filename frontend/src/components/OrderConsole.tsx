'use client';

import React, { useState } from 'react';
import { ArrowUpRight, ArrowDownRight, ShieldAlert, Zap, CheckCircle2 } from 'lucide-react';

interface OrderConsoleProps {
  selectedAsset: string;
  virtualCash: number;
  onPlaceOrder: (order: {
    asset: string;
    action: 'BUY' | 'SELL';
    amount: number;
    leverage: number;
    stopLoss: number;
    takeProfit: number;
  }) => void;
}

export const OrderConsole: React.FC<OrderConsoleProps> = ({
  selectedAsset,
  virtualCash,
  onPlaceOrder,
}) => {
  const [action, setAction] = useState<'BUY' | 'SELL'>('BUY');
  const [amount, setAmount] = useState<string>('1000');
  const [leverage, setLeverage] = useState<number>(10);
  const [stopLoss, setStopLoss] = useState<number>(1.5);
  const [takeProfit, setTakeProfit] = useState<number>(3.5);
  const [msg, setMsg] = useState<string>('');

  const leveragePresets = [1, 5, 10, 25, 50];

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const val = float(amount);
    if (!isNaN(val) && val > 0) {
      onPlaceOrder({
        asset: selectedAsset,
        action,
        amount: val,
        leverage,
        stopLoss,
        takeProfit,
      });
      setMsg(`${action} Order Executed for ${selectedAsset} ($${val * leverage} Position)`);
      setTimeout(() => setMsg(''), 4000);
    }
  };

  function float(str: string) {
    return parseFloat(str) || 0;
  }

  const isBuy = action === 'BUY';

  return (
    <div className="bg-darkcard border border-darkborder p-4 md:p-6 rounded-2xl shadow-xl space-y-4">
      {/* Top Tab Header (BUY / SELL Toggle) */}
      <div className="grid grid-cols-2 gap-2 bg-gray-950 p-1.5 rounded-xl border border-gray-800">
        <button
          onClick={() => setAction('BUY')}
          className={`py-2.5 rounded-lg text-xs md:text-sm font-black transition flex items-center justify-center ${
            isBuy
              ? 'bg-emerald-600 text-white shadow-lg shadow-emerald-600/30'
              : 'text-gray-400 hover:text-white'
          }`}
        >
          <ArrowUpRight className="w-4 h-4 mr-1" /> BUY (Long)
        </button>
        <button
          onClick={() => setAction('SELL')}
          className={`py-2.5 rounded-lg text-xs md:text-sm font-black transition flex items-center justify-center ${
            !isBuy
              ? 'bg-red-600 text-white shadow-lg shadow-red-600/30'
              : 'text-gray-400 hover:text-white'
          }`}
        >
          <ArrowDownRight className="w-4 h-4 mr-1" /> SELL (Short)
        </button>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Order Amount Input */}
        <div>
          <div className="flex justify-between text-xs text-gray-400 font-semibold mb-1.5">
            <span>Order Amount (USD)</span>
            <span>Available: ${virtualCash.toLocaleString()}</span>
          </div>
          <div className="relative">
            <span className="absolute inset-y-0 left-0 pl-3 flex items-center text-gray-400 font-bold">$</span>
            <input
              type="number"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              className="w-full bg-gray-900 border border-gray-700 rounded-xl pl-8 pr-4 py-2 text-xs md:text-sm text-white focus:outline-none focus:border-blue-500 font-bold"
              placeholder="1000"
            />
          </div>
        </div>

        {/* Leverage Selector */}
        <div>
          <div className="flex justify-between text-xs text-gray-400 font-semibold mb-1.5">
            <span className="flex items-center"><Zap className="w-3.5 h-3.5 text-amber-400 mr-1" /> Leverage</span>
            <span className="font-bold text-amber-400">{leverage}x</span>
          </div>
          <div className="flex gap-1.5">
            {leveragePresets.map((lev) => (
              <button
                type="button"
                key={lev}
                onClick={() => setLeverage(lev)}
                className={`flex-1 py-1.5 rounded-lg text-xs font-bold border transition ${
                  leverage === lev
                    ? 'bg-amber-500 text-black border-amber-400 font-black shadow-md'
                    : 'bg-gray-900 border-gray-800 text-gray-400 hover:text-white'
                }`}
              >
                {lev}x
              </button>
            ))}
          </div>
        </div>

        {/* Stop Loss & Take Profit % */}
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-[11px] font-semibold text-gray-400">Stop Loss (%)</label>
            <input
              type="number"
              step="0.5"
              value={stopLoss}
              onChange={(e) => setStopLoss(parseFloat(e.target.value))}
              className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-1.5 text-xs text-red-400 font-bold focus:outline-none"
            />
          </div>
          <div>
            <label className="text-[11px] font-semibold text-gray-400">Take Profit (%)</label>
            <input
              type="number"
              step="0.5"
              value={takeProfit}
              onChange={(e) => setTakeProfit(parseFloat(e.target.value))}
              className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-1.5 text-xs text-emerald-400 font-bold focus:outline-none"
            />
          </div>
        </div>

        {/* Action Button */}
        <button
          type="submit"
          className={`w-full py-3 rounded-xl text-sm font-black transition flex items-center justify-center shadow-xl ${
            isBuy
              ? 'bg-emerald-600 hover:bg-emerald-500 text-white shadow-emerald-600/30'
              : 'bg-red-600 hover:bg-red-500 text-white shadow-red-600/30'
          }`}
        >
          {isBuy ? 'PLACE BUY ORDER' : 'PLACE SELL ORDER'}
        </button>

        {msg && (
          <div className="text-xs text-emerald-400 font-medium flex items-center justify-center pt-1 animate-pulse">
            <CheckCircle2 className="w-3.5 h-3.5 mr-1" /> {msg}
          </div>
        )}
      </form>
    </div>
  );
};
