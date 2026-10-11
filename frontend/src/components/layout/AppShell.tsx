'use client';

import React from 'react';
import { usePathname } from 'next/navigation';
import { TopHeader } from './TopHeader';
import { Sidebar } from './Sidebar';
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
    <div className="flex flex-col min-h-screen bg-canvas text-txt-primary">
      {/* Top Fixed Header */}
      <TopHeader />

      {/* Main Body */}
      <div className="flex flex-1 overflow-hidden">
        {/* Institutional Sidebar */}
        <Sidebar />

        {/* Dynamic Page Content Viewport */}
        <main className="flex-1 overflow-y-auto p-3 sm:p-4 md:p-6 bg-canvas pb-20 md:pb-6">
          <div className="max-w-[1680px] mx-auto space-y-4 md:space-y-6">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}
