import React from 'react';
import type { Metadata } from 'next';
import './globals.css';
import { TradingProvider } from '../context/TradingContext';
import { AppShell } from '../components/layout/AppShell';

export const metadata: Metadata = {
  title: 'AEGIS QUANT — Institutional Trading Platform',
  description: 'High-frequency algorithmic trading terminal and portfolio management engine',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="h-full">
      <body className="h-full bg-canvas text-txt-primary">
        <TradingProvider>
          <AppShell>{children}</AppShell>
        </TradingProvider>
      </body>
    </html>
  );
}
