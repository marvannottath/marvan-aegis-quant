'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { api } from '../../lib/api';
import { Badge } from '../../components/common/Badge';
import { Modal } from '../../components/common/Modal';
import {
  User,
  Shield,
  ShieldCheck,
  KeyRound,
  Lock,
  Smartphone,
  Mail,
  CheckCircle2,
  AlertCircle,
  Copy,
  Check,
  RefreshCw,
  Fingerprint,
  ArrowRight,
  ExternalLink,
  Activity,
  Layers,
  Database
} from 'lucide-react';

export default function ProfilePage() {
  const [username, setUsername] = useState<string>('marvan');
  const [totpEnabled, setTotpEnabled] = useState<boolean>(false);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  // TOTP Modal
  const [isTotpModalOpen, setIsTotpModalOpen] = useState<boolean>(false);
  const [totpData, setTotpData] = useState<any>(null);
  const [verifyCode, setVerifyCode] = useState<string>('');
  const [isActivatingTotp, setIsActivatingTotp] = useState<boolean>(false);
  const [totpMsg, setTotpMsg] = useState<{ type: 'success' | 'error'; message: string } | null>(null);
  const [copiedSecret, setCopiedSecret] = useState<boolean>(false);

  // Password Change Form
  const [currentPassword, setCurrentPassword] = useState<string>('');
  const [newPassword, setNewPassword] = useState<string>('');
  const [confirmPassword, setConfirmPassword] = useState<string>('');
  const [isUpdatingPassword, setIsUpdatingPassword] = useState<boolean>(false);
  const [passwordStatus, setPasswordStatus] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  // Email Reset Link
  const [isSendingReset, setIsSendingReset] = useState<boolean>(false);
  const [resetStatus, setResetStatus] = useState<{ type: 'success' | 'error'; message: string; link?: string } | null>(null);

  useEffect(() => {
    loadProfileSecurity();
  }, []);

  const loadProfileSecurity = async () => {
    setIsLoading(true);
    try {
      const res = await api.getTotpSetup('marvan');
      if (res.status === 'SUCCESS') {
        setTotpEnabled(Boolean(res.totp_enabled));
      }
    } catch (e) {
      console.error('Failed to load profile security:', e);
    } finally {
      setIsLoading(false);
    }
  };

  const handleOpenTotp = async () => {
    setTotpMsg(null);
    setVerifyCode('');
    try {
      const res = await api.getTotpSetup('marvan');
      if (res.status === 'SUCCESS') {
        setTotpData(res);
        setIsTotpModalOpen(true);
      }
    } catch (e: any) {
      setTotpMsg({ type: 'error', message: e?.message || 'Failed to generate 2FA key' });
    }
  };

  const handleActivateTotp = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!verifyCode || verifyCode.trim().length !== 6) {
      setTotpMsg({ type: 'error', message: 'Please enter the 6-digit code from your authenticator app.' });
      return;
    }

    setIsActivatingTotp(true);
    setTotpMsg(null);
    try {
      const res = await api.activateTotp('marvan', verifyCode.trim());
      if (res.status === 'SUCCESS') {
        setTotpMsg({ type: 'success', message: 'Google Authenticator 2FA activated successfully!' });
        setTotpEnabled(true);
        setTimeout(() => {
          setIsTotpModalOpen(false);
          setTotpMsg(null);
        }, 1500);
      } else {
        setTotpMsg({ type: 'error', message: res.message || 'Invalid 6-digit code.' });
      }
    } catch (e: any) {
      setTotpMsg({ type: 'error', message: e?.message || 'Network error' });
    } finally {
      setIsActivatingTotp(false);
    }
  };

  const handlePasswordChange = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!currentPassword) {
      setPasswordStatus({ type: 'error', message: 'Current password is required.' });
      return;
    }
    if (!newPassword || newPassword.length < 6) {
      setPasswordStatus({ type: 'error', message: 'New password must be at least 6 characters.' });
      return;
    }
    if (newPassword !== confirmPassword) {
      setPasswordStatus({ type: 'error', message: 'New passwords do not match.' });
      return;
    }

    setIsUpdatingPassword(true);
    setPasswordStatus(null);
    try {
      const token = localStorage.getItem('aq_admin_token') || '';
      const res = await api.changePassword(token, currentPassword, newPassword);
      if (res.status === 'SUCCESS') {
        setPasswordStatus({ type: 'success', message: 'Password updated successfully and secured with PBKDF2!' });
        setCurrentPassword('');
        setNewPassword('');
        setConfirmPassword('');
      } else {
        setPasswordStatus({ type: 'error', message: res.message || 'Password update failed.' });
      }
    } catch (e: any) {
      setPasswordStatus({ type: 'error', message: e?.message || 'Network error occurred.' });
    } finally {
      setIsUpdatingPassword(false);
    }
  };

  const handleDispatchResetLink = async () => {
    setIsSendingReset(true);
    setResetStatus(null);

    try {
      const res = await api.requestPasswordReset('marvan');
      if (res.status === 'RESET_LINK_DISPATCHED' || res.status === 'OTP_DISPATCHED') {
        setResetStatus({
          type: 'success',
          message: `Secure password reset link and authorization code dispatched to ${res.target_email || 'marvannottath@gmail.com'}!`,
          link: res.reset_link,
        });
      } else {
        setResetStatus({ type: 'error', message: res.message || 'Failed to dispatch reset email.' });
      }
    } catch (e: any) {
      setResetStatus({ type: 'error', message: e?.message || 'Network error' });
    } finally {
      setIsSendingReset(false);
    }
  };

  return (
    <div className="space-y-6 max-w-5xl">
      {/* Profile Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-line pb-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold tracking-tight text-txt-primary">Trader Profile & Account Center</h1>
            <Badge variant="live">SUPER ADMIN</Badge>
          </div>
          <p className="text-xs text-txt-muted mt-0.5">
            Manage your institutional credentials, 2FA security, and multi-tenant ledger parameters.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Link
            href="/admin"
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-line bg-panel hover:bg-panel-light text-xs font-semibold text-brand transition cursor-pointer"
          >
            <span>Super Admin Console</span>
            <ExternalLink className="w-3.5 h-3.5" />
          </Link>
        </div>
      </div>

      {/* Identity Card */}
      <div className="card-panel p-6 flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          <div className="w-16 h-16 rounded-2xl bg-linear-to-tr from-brand to-blue-600 text-white flex items-center justify-center text-xl font-black uppercase shadow-sm">
            M
          </div>
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <h2 className="text-lg font-bold text-txt-primary">Marvan</h2>
              <Badge variant="live" size="sm">TIER-1 PRO</Badge>
            </div>
            <p className="text-xs text-txt-muted font-mono">
              UID: AQ-INST-98214 • Role: Master Super Admin & Quant Desk Lead
            </p>
            <div className="flex items-center gap-3 text-xs font-mono text-txt-secondary pt-0.5">
              <span className="flex items-center gap-1">
                <Mail className="w-3.5 h-3.5 text-brand" />
                marvannottath@gmail.com
              </span>
              <span>•</span>
              <span className="flex items-center gap-1 text-profit">
                <CheckCircle2 className="w-3.5 h-3.5" />
                Ledger Reconciled
              </span>
            </div>
          </div>
        </div>

        <div className="flex flex-col sm:flex-row items-center gap-2 font-mono text-xs">
          <div className="px-3 py-2 rounded-lg border border-line bg-slate-50 dark:bg-panel-light text-center">
            <span className="text-[10px] text-txt-muted block uppercase">Tenant ID</span>
            <span className="font-bold text-txt-primary">TENANT_MARVAN</span>
          </div>
          <div className="px-3 py-2 rounded-lg border border-line bg-slate-50 dark:bg-panel-light text-center">
            <span className="text-[10px] text-txt-muted block uppercase">2FA Guard</span>
            <span className={`font-bold ${totpEnabled ? 'text-profit' : 'text-amber-500'}`}>
              {totpEnabled ? 'ACTIVE 🟢' : 'DISABLED ⚠️'}
            </span>
          </div>
        </div>
      </div>

      {/* Grid: 2FA & Password Management */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* TWO-FACTOR AUTHENTICATION */}
        <div className="card-panel p-5 space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-line">
            <div className="flex items-center gap-2">
              <Smartphone className="w-5 h-5 text-brand" />
              <div>
                <h3 className="text-xs font-bold uppercase tracking-wider text-txt-primary">
                  Google Authenticator (2FA)
                </h3>
                <p className="text-[11px] text-txt-muted">RFC 6238 Time-based One-Time Password</p>
              </div>
            </div>
            <span
              className={`px-2 py-0.5 rounded text-[10px] font-bold border ${
                totpEnabled
                  ? 'bg-emerald-500/10 border-emerald-500/20 text-profit'
                  : 'bg-amber-500/10 border-amber-500/20 text-amber-500'
              }`}
            >
              {totpEnabled ? 'PROTECTED 🟢' : 'SETUP REQUIRED'}
            </span>
          </div>

          <p className="text-xs text-txt-secondary leading-relaxed">
            Link your mobile authenticator app (Google Authenticator, Authy, or Microsoft Authenticator) to require a 6-digit code for sensitive trading actions and administrative commands.
          </p>

          <div className="p-3 bg-slate-50 dark:bg-panel-light rounded-lg border border-line space-y-1 font-mono text-[11px]">
            <div className="flex justify-between">
              <span className="text-txt-muted">Status:</span>
              <span className={totpEnabled ? 'text-profit font-bold' : 'text-amber-500 font-bold'}>
                {totpEnabled ? '2FA Active on Account' : 'Not Activated'}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-txt-muted">Hardware Key:</span>
              <span className="text-txt-primary">HMAC-SHA1 30s Step</span>
            </div>
          </div>

          <div className="pt-2">
            {!totpEnabled ? (
              <button
                onClick={handleOpenTotp}
                className="px-4 py-2 rounded-lg bg-brand hover:bg-brand/90 text-white font-bold text-xs shadow-xs transition flex items-center gap-1.5 cursor-pointer"
              >
                <KeyRound className="w-3.5 h-3.5" />
                <span>Configure 2FA Authenticator</span>
              </button>
            ) : (
              <button
                onClick={handleOpenTotp}
                className="px-3.5 py-1.5 rounded-lg border border-line bg-panel hover:bg-panel-light text-xs font-semibold text-txt-primary transition cursor-pointer"
              >
                View / Re-pair Authenticator QR
              </button>
            )}
          </div>
        </div>

        {/* PASSWORD HARDENING & UPDATE */}
        <div className="card-panel p-5 space-y-4">
          <div className="flex items-center gap-2 pb-3 border-b border-line">
            <Lock className="w-5 h-5 text-brand" />
            <div>
              <h3 className="text-xs font-bold uppercase tracking-wider text-txt-primary">
                Update Account Password
              </h3>
              <p className="text-[11px] text-txt-muted">PBKDF2-HMAC-SHA256 Cryptographic Hash</p>
            </div>
          </div>

          <form onSubmit={handlePasswordChange} className="space-y-3 text-xs">
            <div>
              <label className="block font-semibold text-txt-primary mb-1">Current Password:</label>
              <input
                type="password"
                required
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                placeholder="••••••••••••"
                className="w-full px-3 py-1.5 text-xs rounded-lg border border-line bg-panel-light text-txt-primary font-mono focus:outline-none focus:ring-2 focus:ring-brand"
              />
            </div>

            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="block font-semibold text-txt-primary mb-1">New Password:</label>
                <input
                  type="password"
                  required
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  placeholder="Min 6 characters"
                  className="w-full px-3 py-1.5 text-xs rounded-lg border border-line bg-panel-light text-txt-primary font-mono focus:outline-none focus:ring-2 focus:ring-brand"
                />
              </div>
              <div>
                <label className="block font-semibold text-txt-primary mb-1">Confirm New:</label>
                <input
                  type="password"
                  required
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="Confirm password"
                  className="w-full px-3 py-1.5 text-xs rounded-lg border border-line bg-panel-light text-txt-primary font-mono focus:outline-none focus:ring-2 focus:ring-brand"
                />
              </div>
            </div>

            {passwordStatus && (
              <div
                className={`p-2 rounded-lg font-mono text-[11px] border ${
                  passwordStatus.type === 'success'
                    ? 'bg-emerald-500/10 border-emerald-500/20 text-profit'
                    : 'bg-red-500/10 border-red-500/20 text-red-500'
                }`}
              >
                {passwordStatus.message}
              </div>
            )}

            <button
              type="submit"
              disabled={isUpdatingPassword}
              className="px-4 py-2 rounded-lg bg-panel hover:bg-panel-light border border-line text-txt-primary font-bold text-xs shadow-2xs transition disabled:opacity-50 cursor-pointer"
            >
              {isUpdatingPassword ? 'Updating...' : 'Update Password'}
            </button>
          </form>
        </div>
      </div>

      {/* DISPATCH RESET LINK TO MARVANNOTTATH@GMAIL.COM */}
      <div className="card-panel p-5 space-y-3 bg-blue-50/20 dark:bg-blue-950/20 border-brand/20">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-lg bg-brand/10 text-brand">
              <Mail className="h-5 w-5" />
            </div>
            <div>
              <h3 className="text-xs font-bold uppercase tracking-wider text-txt-primary">
                Email Password Reset Link (marvannottath@gmail.com)
              </h3>
              <p className="text-[11px] text-txt-muted">
                Generates a secure cryptographic reset token link dispatched strictly to your verified email.
              </p>
            </div>
          </div>

          <button
            onClick={handleDispatchResetLink}
            disabled={isSendingReset}
            className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-brand hover:bg-brand/90 text-white font-bold text-xs shadow-xs transition disabled:opacity-50 cursor-pointer"
          >
            {isSendingReset ? (
              <RefreshCw className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <Mail className="w-3.5 h-3.5" />
            )}
            <span>{isSendingReset ? 'Dispatching...' : 'Send Reset Link to marvannottath@gmail.com'}</span>
          </button>
        </div>

        {resetStatus && (
          <div
            className={`p-3 rounded-lg font-mono text-xs border ${
              resetStatus.type === 'success'
                ? 'bg-emerald-500/10 border-emerald-500/20 text-profit'
                : 'bg-red-500/10 border-red-500/20 text-red-500'
            }`}
          >
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 shrink-0" />
              <span>{resetStatus.message}</span>
            </div>
            {resetStatus.link && (
              <div className="mt-2 pt-2 border-t border-emerald-500/20 text-[11px] text-txt-secondary">
                Direct Reset Link:{' '}
                <a
                  href={resetStatus.link}
                  className="text-brand underline break-all font-mono"
                  target="_blank"
                  rel="noreferrer"
                >
                  {resetStatus.link}
                </a>
              </div>
            )}
          </div>
        )}
      </div>

      {/* TOTP MODAL */}
      <Modal
        isOpen={isTotpModalOpen}
        onClose={() => setIsTotpModalOpen(false)}
        title="Pair Google Authenticator App"
        description="Scan the offline QR code with your mobile authenticator app"
      >
        <div className="space-y-4 text-xs">
          <div className="flex flex-col items-center justify-center p-4 bg-white rounded-xl border border-line">
            {totpData?.qr_image_url ? (
              <img
                src={totpData.qr_image_url}
                alt="Google Authenticator QR Code"
                className="w-44 h-44 object-contain"
              />
            ) : (
              <div className="w-44 h-44 flex items-center justify-center text-txt-muted">
                Generating QR...
              </div>
            )}
            <p className="text-[10px] text-txt-muted mt-2 text-center">
              Scan with Google Authenticator, Authy, or Microsoft Authenticator
            </p>
          </div>

          <div>
            <label className="block text-[11px] font-semibold text-txt-primary mb-1">
              Manual Setup Key:
            </label>
            <div className="flex items-center gap-2">
              <input
                type="text"
                readOnly
                value={totpData?.secret || ''}
                className="w-full px-3 py-1.5 text-xs rounded-lg border border-line bg-panel-light font-mono text-txt-primary select-all"
              />
              <button
                type="button"
                onClick={() => {
                  if (totpData?.secret) {
                    navigator.clipboard.writeText(totpData.secret);
                    setCopiedSecret(true);
                    setTimeout(() => setCopiedSecret(false), 2000);
                  }
                }}
                className="px-3 py-1.5 rounded-lg border border-line bg-panel hover:bg-panel-light text-txt-secondary font-semibold flex items-center gap-1 transition cursor-pointer"
              >
                {copiedSecret ? <Check className="w-3.5 h-3.5 text-profit" /> : <Copy className="w-3.5 h-3.5" />}
                <span>{copiedSecret ? 'Copied' : 'Copy'}</span>
              </button>
            </div>
          </div>

          <form onSubmit={handleActivateTotp} className="space-y-3 pt-2 border-t border-line">
            <div>
              <label className="block text-xs font-semibold text-txt-primary mb-1">
                Enter 6-Digit App Code to Verify:
              </label>
              <input
                type="text"
                maxLength={6}
                required
                placeholder="000000"
                value={verifyCode}
                onChange={(e) => setVerifyCode(e.target.value)}
                className="w-full px-3 py-2 text-center text-lg tracking-widest font-mono font-bold rounded-lg border border-line bg-panel-light text-txt-primary focus:outline-none focus:ring-2 focus:ring-brand"
              />
            </div>

            {totpMsg && (
              <div
                className={`p-2.5 rounded-lg font-mono text-[11px] border ${
                  totpMsg.type === 'success'
                    ? 'bg-emerald-500/10 border-emerald-500/20 text-profit'
                    : 'bg-red-500/10 border-red-500/20 text-red-500'
                }`}
              >
                {totpMsg.message}
              </div>
            )}

            <div className="flex items-center justify-end gap-2 pt-1">
              <button
                type="button"
                onClick={() => setIsTotpModalOpen(false)}
                className="px-3 py-1.5 rounded-md border border-line bg-panel hover:bg-panel-light text-txt-secondary"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isActivatingTotp}
                className="px-4 py-1.5 rounded-md bg-brand hover:bg-brand/90 text-white font-bold transition disabled:opacity-50 cursor-pointer"
              >
                {isActivatingTotp ? 'Verifying...' : 'Verify & Activate 2FA'}
              </button>
            </div>
          </form>
        </div>
      </Modal>
    </div>
  );
}
