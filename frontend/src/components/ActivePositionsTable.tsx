'use client';

import React from 'react';
import { Layers, XCircle, ArrowUpRight, ArrowDownRight } from 'lucide-react';

interface Position {
  trade_id: string;
  asset: string;
  action: 'BUY' | 'SELL';
  units: number;
  entry_price: number;
  capital_allocated: number;
  leverage?: number;
  timestamp: string;
}

interface ActivePositionsTableProps {
  positions: Position[];
  onClosePosition: (asset: string) => void;
}

export const ActivePositionsTable: React.FC<ActivePositionsTableProps> = ({
  positions,
  onClosePosition,
}) => {
  if (!positions || positions.length === 0) {
    return (
      <div className="bg-darkcard border border-darkborder p-4 rounded-2xl shadow-xl text-center space-y-1.5">
        <Layers className="w-6 h-6 text-gray-500 mx-auto" />
        <h3 className="font-bold text-xs text-gray-300">No Open Positions</h3>
        <p className="text-[11px] text-gray-500">Manual orders or AI automated positions will be listed here.</p>
      </div>
    );
  }

  return (
    <div className="bg-darkcard border border-darkborder p-4 md:p-6 rounded-2xl shadow-xl space-y-4">
      <div className="flex items-center justify-between border-b border-darkborder pb-3">
        <div className="flex items-center space-x-2">
          <Layers className="w-5 h-5 text-blue-400" />
          <h2 className="text-base md:text-lg font-bold text-white">Active Positions ({positions.length})</h2>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="border-b border-gray-800 text-[11px] text-gray-400 uppercase font-semibold">
              <th className="py-2 px-3">Asset</th>
              <th className="py-2 px-3">Action</th>
              <th className="py-2 px-3">Margin</th>
              <th className="py-2 px-3">Leverage</th>
              <th className="py-2 px-3">Entry Price</th>
              <th className="py-2 px-3 text-right">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-800 text-xs font-semibold text-gray-200">
            {positions.map((pos) => {
              const isBuy = pos.action === 'BUY';
              const badgeClass = isBuy
                ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                : 'bg-red-500/10 text-red-400 border-red-500/30';

              return (
                <tr key={pos.trade_id} className="hover:bg-gray-900/60 transition">
                  <td className="py-3 px-3 font-bold text-white">{pos.asset}</td>
                  <td className="py-3 px-3">
                    <span className={`px-2 py-0.5 text-[10px] font-black rounded border flex items-center w-fit ${badgeClass}`}>
                      {isBuy ? <ArrowUpRight className="w-3 h-3 mr-1" /> : <ArrowDownRight className="w-3 h-3 mr-1" />}
                      {pos.action}
                    </span>
                  </td>
                  <td className="py-3 px-3">${pos.capital_allocated.toLocaleString()}</td>
                  <td className="py-3 px-3 text-amber-400 font-bold">{pos.leverage || 1}x</td>
                  <td className="py-3 px-3">${pos.entry_price.toFixed(4)}</td>
                  <td className="py-3 px-3 text-right">
                    <button
                      onClick={() => onClosePosition(pos.asset)}
                      className="bg-red-950/80 hover:bg-red-900 text-red-300 border border-red-500/40 px-2.5 py-1 rounded-lg text-[11px] font-bold transition flex items-center ml-auto"
                    >
                      <XCircle className="w-3.5 h-3.5 mr-1" /> Close
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};
