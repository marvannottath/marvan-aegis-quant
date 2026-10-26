'use client';

import React from 'react';
import { usePathname } from 'next/navigation';
import { TopHeader } from './TopHeader';
import { Sidebar } from './Sidebar';
import { MarketTransitionLoader } from '../common/MarketTransitionLoader';
import { useTradingContext } from '../../context/TradingContext';

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { environment } = useTradingContext();

  // Pure isolated layout for Admin Portal
  if (pathname.startsWith('/admin')) {
    return (
      <div className="min-h-screen bg-canvas text-txt-primary">
        {children}
      </div>
    );
  }

  return (
    <div className="flex flex-col h-screen max-h-screen overflow-hidden bg-canvas text-txt-primary">
      {/* Motivating Market Transition Micro-Loader */}
      <MarketTransitionLoader />

      {/* Top Fixed Header */}
      <TopHeader />

      {/* Main Body with Fixed Left Sidebar and Scrolling Right Main Viewport */}
      <div className="flex flex-1 min-h-0 overflow-hidden">
        {/* Institutional Sidebar (Fixed Left, Collapse button always visible) */}
        <Sidebar />

        {/* Dynamic Page Content Viewport (Scrolls independently) */}
        <main className="flex-1 min-h-0 overflow-y-auto p-3 sm:p-4 md:p-6 bg-canvas pb-20 md:pb-6">
          <div className="max-w-[1680px] mx-auto space-y-4 md:space-y-6">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}
