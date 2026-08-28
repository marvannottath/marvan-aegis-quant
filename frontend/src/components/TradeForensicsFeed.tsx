'use client';

import React from 'react';
import { Microscope, HelpCircle, GraduationCap } from 'lucide-react';

interface TradeForensic {
  trade_id: string;
  timestamp: string;
  asset: string;
  pnl_usd: number;
  pnl_pct: number;
  result: 'PROFIT' | 'LOSS';
  exit_reason: string;
  root_cause_attribution: string;
  self_learning_update: string;
}

interface TradeForensicsFeedProps {
  forensics: TradeForensic[];
}

export const TradeForensicsFeed: React.FC<TradeForensicsFeedProps> = ({ forensics }) => {
  if (!forensics || forensics.length === 0) {
    return (
      <div className="bg-darkcard border border-darkborder p-6 rounded-2xl shadow-xl text-center space-y-2">
        <Microscope className="w-8 h-8 text-gray-500 mx-auto" />
        <h3 className="font-bold text-sm text-gray-300">No Closed Trades Yet</h3>
        <p className="text-xs text-gray-500">The RL Agent is evaluating price feeds. Diagnostic post-mortems will automatically appear here when trades close.</p>
      </div>
    );
  }

  return (
    <div className="bg-darkcard border border-darkborder p-4 md:p-6 rounded-2xl shadow-xl space-y-4">
      <div className="flex items-center justify-between border-b border-darkborder pb-3.5">
        <div className="flex items-center space-x-2.5">
          <div className="p-2 rounded-lg bg-blue-500/10 text-blue-400">
            <Microscope className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-base md:text-lg font-bold text-white">AI Trade Forensics & Audit Feed</h2>
            <p className="text-[11px] md:text-xs text-gray-400">Root-Cause Analysis & Reinforcement Learning Feedback Loop</p>
          </div>
        </div>
      </div>

      <div className="space-y-3.5 max-h-[500px] overflow-y-auto pr-1">
        {forensics.map((item, idx) => {
          const isProf = item.result === 'PROFIT';
          const pnlColor = isProf ? 'text-emerald-400' : 'text-red-400';
          const badgeStyle = isProf
            ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
            : 'bg-red-500/10 text-red-400 border-red-500/30';

          return (
            <div key={item.trade_id || idx} className="p-3.5 md:p-4 bg-gray-900/80 border border-gray-800 rounded-xl space-y-3 shadow-md">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2.5">
                  <span className={`px-2 py-0.5 text-[10px] md:text-xs font-black rounded-md border ${badgeStyle}`}>
                    {item.result}
                  </span>
                  <span className="font-bold text-xs md:text-sm text-white">{item.asset}</span>
                  <span className="text-[10px] text-gray-500 hidden sm:inline">{item.timestamp}</span>
                </div>
                <span className={`font-black text-xs md:text-sm ${pnlColor}`}>
                  {isProf ? '+' : ''}${item.pnl_usd.toFixed(2)} ({isProf ? '+' : ''}{item.pnl_pct.toFixed(2)}%)
                </span>
              </div>

              {/* Root Cause Attribution Box */}
              <div className="bg-gray-800/50 p-2.5 md:p-3 rounded-lg border border-gray-700/50">
                <div className="text-[11px] md:text-xs font-bold text-gray-300 flex items-center mb-1">
                  <HelpCircle className="w-3.5 h-3.5 text-blue-400 mr-1.5" /> Root Cause & Trade Attribution:
                </div>
                <p className="text-[11px] md:text-xs text-gray-300 leading-relaxed">{item.root_cause_attribution}</p>
              </div>

              {/* RL Self-Learning Update Box */}
              <div className="bg-blue-950/30 p-2.5 md:p-3 rounded-lg border border-blue-800/40">
                <div className="text-[11px] md:text-xs font-bold text-blue-400 flex items-center mb-1">
                  <GraduationCap className="w-3.5 h-3.5 text-indigo-400 mr-1.5" /> RL Self-Learning Feedback Loop:
                </div>
                <p className="text-[11px] md:text-xs text-blue-200 leading-relaxed">{item.self_learning_update}</p>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
