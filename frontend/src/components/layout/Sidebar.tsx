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
  Server,
  FileCheck,
  Lock,
  FileText,
  Settings,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';

export function Sidebar() {
  const pathname = usePathname();
  const { environment, workspace } = useTradingContext();
  const [isCollapsed, setIsCollapsed] = useState(false);

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

  const secondaryNav = [
    {
      name: 'System Health',
      href: `${prefix}/system`,
      icon: Server,
    },
    {
      name: 'Audit & Forensic',
      href: `${prefix}/audit`,
      icon: FileCheck,
    },
    {
      name: 'Security & 2FA',
      href: `${prefix}/security`,
      icon: Lock,
    },
    {
      name: 'Reports & CSV',
      href: `${prefix}/reports`,
      icon: FileText,
    },
    {
      name: 'Settings',
      href: `${prefix}/settings`,
      icon: Settings,
    },
  ];

  const isLinkActive = (href: string) => {
    if (href === '/' || href === '/demo') {
      return pathname === href;
    }
    return pathname === href || pathname.startsWith(`${href}/`);
  };

  return (
    <aside
      className={`relative z-30 flex flex-col border-r border-line bg-panel transition-all duration-200 select-none ${
        isCollapsed ? 'w-14' : 'w-56'
      }`}
    >
      {/* Primary Navigation Section */}
      <div className="flex-1 py-3 px-2 overflow-y-auto space-y-6">
        <div>
          {!isCollapsed && (
            <div className="px-2.5 pb-2 text-[10px] font-bold uppercase tracking-wider text-txt-subtle">
              Terminal
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
                      ? 'bg-blue-50 text-brand font-semibold shadow-xs'
                      : 'text-txt-secondary hover:bg-slate-50 hover:text-txt-primary'
                  }`}
                >
                  <Icon className={`h-4 w-4 shrink-0 ${active ? 'text-brand' : 'text-txt-muted'}`} />
                  {!isCollapsed && <span className="truncate">{item.name}</span>}
                </Link>
              );
            })}
          </nav>
        </div>

        {/* Secondary Navigation Section */}
        <div>
          {!isCollapsed && (
            <div className="px-2.5 pb-2 text-[10px] font-bold uppercase tracking-wider text-txt-subtle">
              Governance & Admin
            </div>
          )}
          <nav className="space-y-0.5">
            {secondaryNav.map((item) => {
              const active = isLinkActive(item.href);
              const Icon = item.icon;
              return (
                <Link
                  key={item.name}
                  href={item.href}
                  title={isCollapsed ? item.name : undefined}
                  className={`flex items-center gap-2.5 px-2.5 py-1.5 rounded-md text-xs font-medium transition ${
                    active
                      ? 'bg-blue-50 text-brand font-semibold shadow-xs'
                      : 'text-txt-secondary hover:bg-slate-50 hover:text-txt-primary'
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
      <div className="p-2 border-t border-line bg-slate-50 flex items-center justify-between">
        <button
          onClick={() => setIsCollapsed(!isCollapsed)}
          className="w-full flex items-center justify-center p-1 rounded-md text-txt-muted hover:bg-slate-200 hover:text-txt-primary transition text-xs gap-1 font-medium"
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
  );
}
