import React from 'react';

interface BadgeProps {
  children: React.ReactNode;
  variant?: 'live' | 'demo' | 'success' | 'danger' | 'warning' | 'info' | 'neutral';
  size?: 'sm' | 'md' | 'lg';
  className?: string;
  dot?: boolean;
}

export function Badge({
  children,
  variant = 'neutral',
  size = 'md',
  className = '',
  dot = false,
}: BadgeProps) {
  const sizeStyles = {
    sm: 'px-1.5 py-0.5 text-[11px] font-medium tracking-tight',
    md: 'px-2 py-0.5 text-xs font-semibold tracking-wide',
    lg: 'px-2.5 py-1 text-sm font-semibold tracking-wide',
  }[size];

  const variantStyles = {
    live: 'bg-red-50 text-loss-dark border border-loss/20 ring-1 ring-loss/10',
    demo: 'bg-amber-50 text-warn border border-warn/20 ring-1 ring-warn/10',
    success: 'bg-emerald-50 text-profit-dark border border-profit/20',
    danger: 'bg-red-50 text-loss-dark border border-loss/20',
    warning: 'bg-amber-50 text-warn border border-warn/20',
    info: 'bg-blue-50 text-brand border border-brand/20',
    neutral: 'bg-slate-100 text-txt-secondary border border-line',
  }[variant];

  const dotStyles = {
    live: 'bg-loss animate-pulse',
    demo: 'bg-warn',
    success: 'bg-profit',
    danger: 'bg-loss',
    warning: 'bg-warn',
    info: 'bg-brand',
    neutral: 'bg-slate-400',
  }[variant];

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full ${sizeStyles} ${variantStyles} ${className}`}
    >
      {dot && <span className={`h-1.5 w-1.5 rounded-full ${dotStyles}`} />}
      {children}
    </span>
  );
}
