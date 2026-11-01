import React from 'react';
import type { Metadata, Viewport } from 'next';
import './globals.css';
import { TradingProvider } from '../context/TradingContext';
import { AppShell } from '../components/layout/AppShell';
import { PwaRegistrar } from '../components/common/PwaRegistrar';

export const dynamic = 'force-dynamic';
export const revalidate = 0;

export const viewport: Viewport = {
  themeColor: '#0B0F19',
  width: 'device-width',
  initialScale: 1,
  maximumScale: 1,
  userScalable: false,
};

export const metadata: Metadata = {
  title: 'AEGIS QUANT — Institutional Trading Platform',
  description: 'High-frequency algorithmic trading terminal and portfolio management engine',
  manifest: '/manifest.json',
  icons: {
    icon: '/favicon.png',
    shortcut: '/favicon.png',
    apple: '/apple-touch-icon.png',
  },
  appleWebApp: {
    capable: true,
    statusBarStyle: 'black-translucent',
    title: 'Aegis Quant',
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="h-full">
      <head>
        <link rel="manifest" href="/manifest.json" />
        <link rel="apple-touch-icon" href="/apple-touch-icon.png" />
        <meta name="mobile-web-app-capable" content="yes" />
        <meta name="apple-mobile-web-app-capable" content="yes" />
        <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent" />
        <meta name="apple-mobile-web-app-title" content="Aegis Quant" />
      </head>
      <body className="h-full bg-canvas text-txt-primary">
        <TradingProvider>
          <PwaRegistrar />
          <AppShell>{children}</AppShell>
        </TradingProvider>
      </body>
    </html>
  );
}
