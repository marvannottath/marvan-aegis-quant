import type { Metadata, Viewport } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'Marvan Aegis-Quant AI | Autonomous Trading Console',
  description: 'Marvan\'s Autonomous AI Quant Trading System & Trade Forensics Console',
  manifest: '/manifest.json',
  appleWebApp: {
    capable: true,
    statusBarStyle: 'black-translucent',
    title: 'Marvan Aegis-Quant',
  },
};

export const viewport: Viewport = {
  themeColor: '#0B0F19',
  width: 'device-width',
  initialScale: 1,
  maximumScale: 1,
  userScalable: false,
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-darkbg text-gray-100 pb-20 md:pb-8">
        {children}
      </body>
    </html>
  );
}
