'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useTradingContext } from '../../context/TradingContext';
import {
  LayoutDashboard,
  TrendingUp,
  Cpu,
  BarChart3,
  Layers,
  ShieldAlert,
  Wallet,
  Zap,
  LineChart,
  ChevronLeft,
  ChevronRight,
  Menu,
  X,
} from 'lucide-react';

export function Sidebar() {
  const pathname = usePathname();
  const { environment, workspace } = useTradingContext();
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [isMobileDrawerOpen, setIsMobileDrawerOpen] = useState(false);

  const prefix = environment === 'DEMO' ? '/demo' : '';

  const primaryNav = [
    {
      name: 'Overview',
      href: prefix === '' ? (workspace === 'CRYPTO' ? '/crypto' : workspace === 'INDIA' ? '/india' : '/forex-gold') : `${prefix}/${workspace.toLowerCase().replace('_', '-')}`,
      icon: LayoutDashboard,
      matchExact: true,
    },
    {
      name: 'Markets',
      href: `${prefix}/markets`,
      icon: TrendingUp,
    },
    {
      name: 'Signals',
      href: `${prefix}/signals`,
      icon: Cpu,
    },
    {
      name: 'Positions',
      href: `${prefix}/positions`,
      icon: Layers,
    },
    {
      name: 'Orders',
      href: `${prefix}/orders`,
      icon: BarChart3,
    },
    {
      name: 'Risk Center',
      href: `${prefix}/risk`,
      icon: ShieldAlert,
    },
    {
      name: 'Portfolio & Vault',
      href: `${prefix}/portfolio`,
      icon: Wallet,
    },
    {
      name: 'Execution',
      href: `${prefix}/execution`,
      icon: Zap,
    },
    {
      name: 'Analytics',
      href: `${prefix}/analytics`,
      icon: LineChart,
    },
  ];

  const isLinkActive = (href: string) => {
    if (href === '/' || href === '/demo') {
      return pathname === href;
    }
    return pathname === href || pathname.startsWith(`${href}/`);
  };

  const mobileBottomTabs = [
    {
      name: 'Overview',
      href: prefix === '' ? (workspace === 'CRYPTO' ? '/crypto' : workspace === 'INDIA' ? '/india' : '/forex-gold') : `${prefix}/${workspace.toLowerCase().replace('_', '-')}`,
      icon: LayoutDashboard,
    },
    {
      name: 'Signals',
      href: `${prefix}/signals`,
      icon: Cpu,
    },
    {
      name: 'Portfolio',
      href: `${prefix}/portfolio`,
      icon: Wallet,
    },
    {
      name: 'Analytics',
      href: `${prefix}/analytics`,
      icon: LineChart,
    },
  ];

  return (
    <>
      {/* 1. Desktop & Tablet Sidebar (Hidden on mobile < md) */}
      <aside
        className={`hidden md:flex relative z-30 flex-col border-r border-line bg-panel transition-all duration-200 select-none ${
          isCollapsed ? 'w-14' : 'w-56'
        }`}
      >
        {/* Primary Navigation Section */}
        <div className="flex-1 py-3 px-2 overflow-y-auto space-y-6">
          <div>
            {!isCollapsed && (
              <div className="px-2.5 pb-2 text-[10px] font-bold uppercase tracking-wider text-txt-subtle">
                Trading Terminal
              </div>
            )}
            <nav className="space-y-0.5">
              {primaryNav.map((item) => {
                const active = isLinkActive(item.href);
                const Icon = item.icon;
                return (
                  <Link
                    key={item.name}
                    href={item.href}
                    title={isCollapsed ? item.name : undefined}
                    className={`flex items-center gap-2.5 px-2.5 py-1.5 rounded-md text-xs font-medium transition ${
                      active
                        ? 'bg-blue-50 dark:bg-blue-950/40 text-brand font-semibold shadow-xs'
                        : 'text-txt-secondary hover:bg-slate-50 dark:hover:bg-panel-light hover:text-txt-primary'
                    }`}
                  >
                    <Icon className={`h-4 w-4 shrink-0 ${active ? 'text-brand' : 'text-txt-muted'}`} />
                    {!isCollapsed && <span className="truncate">{item.name}</span>}
                  </Link>
                );
              })}
            </nav>
          </div>
        </div>

        {/* Collapse/Expand Toggle Footer */}
        <div className="p-2 border-t border-line bg-slate-50 dark:bg-panel-light/30 flex items-center justify-between">
          <button
            onClick={() => setIsCollapsed(!isCollapsed)}
            className="w-full flex items-center justify-center p-1 rounded-md text-txt-muted hover:bg-slate-200 dark:hover:bg-panel-light hover:text-txt-primary transition text-xs gap-1 font-medium"
            title={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            {isCollapsed ? (
              <ChevronRight className="h-4 w-4" />
            ) : (
              <>
                <ChevronLeft className="h-4 w-4" />
                <span className="text-[11px] text-txt-muted">Collapse</span>
              </>
            )}
          </button>
        </div>
      </aside>

      {/* 2. Mobile Bottom Navigation Bar (Visible strictly on mobile < md) */}
      <div className="md:hidden fixed bottom-0 left-0 right-0 z-40 bg-panel/95 backdrop-blur-md border-t border-line px-3 py-2 flex items-center justify-around shadow-lg">
        {mobileBottomTabs.map((tab) => {
          const active = isLinkActive(tab.href);
          const Icon = tab.icon;
          return (
            <Link
              key={tab.name}
              href={tab.href}
              className={`flex flex-col items-center gap-1 text-[10px] font-semibold transition ${
                active ? 'text-brand' : 'text-txt-muted hover:text-txt-primary'
              }`}
            >
              <Icon className="h-5 w-5" />
              <span>{tab.name}</span>
            </Link>
          );
        })}

        {/* Mobile Menu Drawer Toggle Button */}
        <button
          onClick={() => setIsMobileDrawerOpen(true)}
          className={`flex flex-col items-center gap-1 text-[10px] font-semibold transition ${
            isMobileDrawerOpen ? 'text-brand' : 'text-txt-muted hover:text-txt-primary'
          }`}
        >
          <Menu className="h-5 w-5" />
          <span>Menu</span>
        </button>
      </div>

      {/* 3. Mobile Slide-Over Navigation Drawer */}
      {isMobileDrawerOpen && (
        <div className="md:hidden fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex justify-end animate-in fade-in duration-200">
          <div className="w-72 h-full bg-panel border-l border-line p-5 flex flex-col justify-between shadow-2xl animate-in slide-in-from-right duration-200">
            <div className="space-y-6 overflow-y-auto">
              <div className="flex items-center justify-between border-b border-line pb-3">
                <div className="flex items-center gap-2">
                  <div className="h-7 w-7 rounded bg-brand text-white flex items-center justify-center font-bold text-xs">
                    AQ
                  </div>
                  <span className="font-bold text-xs uppercase tracking-wider text-txt-primary">
                    Aegis Quant Desk
                  </span>
                </div>
                <button
                  onClick={() => setIsMobileDrawerOpen(false)}
                  className="p-1.5 rounded-lg text-txt-muted hover:text-txt-primary hover:bg-panel-light"
                >
                  <X className="h-5 w-5" />
                </button>
              </div>

              {/* Mobile Primary Navigation */}
              <div>
                <span className="text-[10px] font-bold uppercase tracking-wider text-txt-subtle block mb-2">
                  Trading Terminal
                </span>
                <nav className="space-y-1">
                  {primaryNav.map((item) => {
                    const active = isLinkActive(item.href);
                    const Icon = item.icon;
                    return (
                      <Link
                        key={item.name}
                        href={item.href}
                        onClick={() => setIsMobileDrawerOpen(false)}
                        className={`flex items-center gap-2.5 px-3 py-2 rounded-lg text-xs font-semibold transition ${
                          active
                            ? 'bg-brand/10 text-brand'
                            : 'text-txt-secondary hover:bg-panel-light hover:text-txt-primary'
                        }`}
                      >
                        <Icon className="h-4 w-4" />
                        <span>{item.name}</span>
                      </Link>
                    );
                  })}
                </nav>
              </div>
            </div>

            <div className="pt-4 border-t border-line text-[11px] text-txt-subtle font-mono text-center">
              Institutional Terminal v6.0 Mobile
            </div>
          </div>
        </div>
      )}
    </>
  );
}
