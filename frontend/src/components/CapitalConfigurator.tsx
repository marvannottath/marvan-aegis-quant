'use client';

import React, { useState } from 'react';
import { DollarSign, Play, Pause, Layers, CheckCircle2 } from 'lucide-react';

interface CapitalConfiguratorProps {
  initialCapital: number;
  aiActive: boolean;
  onSetCapital: (amount: number) => void;
  onToggleAI: (active: boolean) => void;
}

export const CapitalConfigurator: React.FC<CapitalConfiguratorProps> = ({
  initialCapital,
  aiActive,
  onSetCapital,
  onToggleAI,
}) => {
  const [customAmount, setCustomAmount] = useState<string>(initialCapital ? initialCapital.toString() : '100000');
  const [statusMsg, setStatusMsg] = useState<string>('');

  const presets = [10000, 50000, 100000, 500000];

  const handleApply = (amountVal?: number) => {
    const val = amountVal !== undefined ? amountVal : parseFloat(customAmount);
    if (!isNaN(val) && val > 0) {
      onSetCapital(val);
      setCustomAmount(val.toString());
      setStatusMsg(`Capital Bundle set to $${val.toLocaleString()}`);
      setTimeout(() => setStatusMsg(''), 4000);
    }
  };

  return (
    <div className="bg-darkcard border border-darkborder p-4 md:p-6 rounded-2xl shadow-xl space-y-4">
      <div className="flex items-center justify-between border-b border-darkborder pb-3.5">
        <div className="flex items-center space-x-2.5">
          <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400">
            <Layers className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-base md:text-lg font-bold text-white">AI Capital Bundle & Execution Control</h2>
            <p className="text-[11px] md:text-xs text-gray-400">Set Custom Trading Funds & Toggle Autonomous AI Trading Engine</p>
          </div>
        </div>

        {/* AI Engine Start / Pause Button */}
        <button
          onClick={() => onToggleAI(!aiActive)}
          className={`px-4 py-2 rounded-xl text-xs font-bold transition flex items-center shadow-lg ${
            aiActive
              ? 'bg-emerald-600 hover:bg-emerald-500 text-white shadow-emerald-600/30'
              : 'bg-amber-600 hover:bg-amber-500 text-white shadow-amber-600/30'
          }`}
        >
          {aiActive ? (
            <>
              <Pause className="w-4 h-4 mr-1.5" /> AI Engine ACTIVE
            </>
          ) : (
            <>
              <Play className="w-4 h-4 mr-1.5" /> Start AI Engine
            </>
          )}
        </button>
      </div>

      {/* Preset Amount Buttons */}
      <div className="space-y-3">
        <label className="text-xs font-semibold text-gray-300">Select Quick Bundle Presets or Enter Custom Amount:</label>
        <div className="flex flex-wrap gap-2">
          {presets.map((preset) => (
            <button
              key={preset}
              onClick={() => handleApply(preset)}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold border transition ${
                initialCapital === preset
                  ? 'bg-blue-600 text-white border-blue-500 shadow-md shadow-blue-500/20'
                  : 'bg-gray-800 text-gray-300 border-gray-700 hover:bg-gray-700'
              }`}
            >
              ${(preset / 1000).toFixed(0)}k Bundle
            </button>
          ))}
        </div>

        {/* Custom Input */}
        <div className="flex items-center space-x-2 pt-1">
          <div className="relative flex-1">
            <span className="absolute inset-y-0 left-0 pl-3 flex items-center text-gray-400 font-bold">$</span>
            <input
              type="number"
              value={customAmount}
              onChange={(e) => setCustomAmount(e.target.value)}
              placeholder="Enter bundle amount (e.g. 50000)"
              className="w-full bg-gray-900 border border-gray-700 rounded-xl pl-8 pr-4 py-2 text-xs md:text-sm text-white focus:outline-none focus:border-blue-500"
            />
          </div>
          <button
            onClick={() => handleApply()}
            className="bg-blue-600 hover:bg-blue-500 active:scale-95 text-white px-4 py-2 rounded-xl text-xs font-bold transition shadow-lg shadow-blue-600/30"
          >
            Deposit & Reset
          </button>
        </div>

        {statusMsg && (
          <div className="text-xs text-emerald-400 font-medium flex items-center pt-1 animate-pulse">
            <CheckCircle2 className="w-3.5 h-3.5 mr-1" /> {statusMsg}
          </div>
        )}
      </div>
    </div>
  );
};
