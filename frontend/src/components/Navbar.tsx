'use client';

import React from 'react';
import { Cpu, RefreshCw } from 'lucide-react';

interface NavbarProps {
  onSync: () => void;
  status: string;
}

export const Navbar: React.FC<NavbarProps> = ({ onSync, status }) => {
  return (
    <header className="border-b border-darkborder bg-darkcard/80 backdrop-blur sticky top-0 z-40 px-4 md:px-6 py-3.5 flex items-center justify-between">
      <div className="flex items-center space-x-3">
        <div className="w-9 h-9 md:w-10 md:h-10 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-500 flex items-center justify-center font-bold text-white shadow-lg shadow-blue-500/20">
          <Cpu className="w-5 h-5" />
        </div>
        <div>
          <h1 className="text-lg md:text-xl font-bold tracking-wide text-white">Marvan Aegis-Quant</h1>
          <p className="text-[10px] md:text-xs text-blue-400 font-medium">Marvan's AI Trading Console</p>
        </div>
      </div>

      <div className="flex items-center space-x-3">
        <div className="hidden sm:flex items-center bg-gray-800/80 px-3 py-1.5 rounded-lg border border-gray-700/50">
          <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse mr-2"></span>
          <span className="text-xs font-semibold text-gray-300">{status}</span>
        </div>

        <button
          onClick={onSync}
          className="bg-blue-600 hover:bg-blue-500 active:scale-95 text-white px-3.5 py-1.5 rounded-lg text-xs font-semibold transition flex items-center shadow-lg shadow-blue-600/30"
        >
          <RefreshCw className="w-3.5 h-3.5 mr-1.5" />
          <span className="hidden xs:inline">Sync</span> Sentiment
        </button>
      </div>
    </header>
  );
};
