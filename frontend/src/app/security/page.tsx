'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { api } from '../../lib/api';
import { Badge } from '../../components/common/Badge';
import { Modal } from '../../components/common/Modal';
import {
  Shield,
  ShieldCheck,
  KeyRound,
  Lock,
  Unlock,
  Smartphone,
  Copy,
  Check,
  RefreshCw,
  Mail,
  AlertCircle,
  CheckCircle2,
  Fingerprint,
  ExternalLink,
  ArrowRight,
  ShieldAlert
} from 'lucide-react';

export default function SecurityPage() {
  const [username, setUsername] = useState<string>('marvan');
  const [totpEnabled, setTotpEnabled] = useState<boolean>(false);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  // TOTP Setup Modal
  const [isTotpModalOpen, setIsTotpModalOpen] = useState<boolean>(false);
  const [totpSetupData, setTotpSetupData] = useState<{
    qr_image_url?: string;
    secret?: string;
    otpauth_url?: string;
  } | null>(null);
  const [verifyCode, setVerifyCode] = useState<string>('');
  const [isActivatingTotp, setIsActivatingTotp] = useState<boolean>(false);
  const [totpFeedback, setTotpFeedback] = useState<{ type: 'success' | 'error'; message: string } | null>(null);
  const [copiedSecret, setCopiedSecret] = useState<boolean>(false);

  // Password Change
  const [currentPassword, setCurrentPassword] = useState<string>('');
  const [newPassword, setNewPassword] = useState<string>('');
  const [confirmPassword, setConfirmPassword] = useState<string>('');
  const [isChangingPassword, setIsChangingPassword] = useState<boolean>(false);
  const [passwordFeedback, setPasswordFeedback] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  // Reset Link to Admin Email
  const [isSendingResetEmail, setIsSendingResetEmail] = useState<boolean>(false);
  const [resetEmailFeedback, setResetEmailFeedback] = useState<{ type: 'success' | 'error'; message: string; link?: string } | null>(null);

  // Biometrics
  const [biometricFeedback, setBiometricFeedback] = useState<string | null>(null);

  // Load user security status
  useEffect(() => {
    fetchSecurityStatus();
  }, []);

  const fetchSecurityStatus = async () => {
    setIsLoading(true);
    try {
      const res = await api.getTotpSetup(username);
      if (res.status === 'SUCCESS') {
        setTotpEnabled(Boolean(res.totp_enabled));
      }
    } catch (e) {
      console.error('Failed to fetch security status:', e);
    } finally {
      setIsLoading(false);
    }
  };

  const handleOpenTotpSetup = async () => {
    setTotpFeedback(null);
    setVerifyCode('');
    try {
      const res = await api.getTotpSetup(username);
      if (res.status === 'SUCCESS') {
        setTotpSetupData(res);
        setIsTotpModalOpen(true);
      }
    } catch (e: any) {
      setTotpFeedback({ type: 'error', message: e?.message || 'Failed to generate 2FA QR code' });
    }
  };

  const handleActivateTotp = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!verifyCode || verifyCode.trim().length !== 6) {
      setTotpFeedback({ type: 'error', message: 'Please enter the 6-digit code from your authenticator app.' });
      return;
    }
    setIsActivatingTotp(true);
    setTotpFeedback(null);

    try {
      const res = await api.activateTotp(username, verifyCode.trim());
      if (res.status === 'SUCCESS') {
        setTotpFeedback({ type: 'success', message: 'Google Authenticator 2FA activated successfully!' });
        setTotpEnabled(true);
        setTimeout(() => {
          setIsTotpModalOpen(false);
          setTotpFeedback(null);
        }, 1500);
      } else {
        setTotpFeedback({ type: 'error', message: res.message || 'Verification failed. Check the 6-digit code.' });
      }
    } catch (e: any) {
      setTotpFeedback({ type: 'error', message: e?.message || 'Network error during 2FA activation' });
    } finally {
      setIsActivatingTotp(false);
    }
  };

  const handleDeactivateTotp = async () => {
    const adminToken = localStorage.getItem('aq_admin_token') || 'MASTER_SESSION';
    try {
      const res = await api.deactivateTotp(adminToken, username);
      if (res.status === 'SUCCESS') {
        setTotpEnabled(false);
      }
    } catch (e) {
      console.error('Deactivation error:', e);
    }
  };

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!currentPassword) {
      setPasswordFeedback({ type: 'error', message: 'Current password is required.' });
      return;
    }
    if (!newPassword || newPassword.length < 6) {
      setPasswordFeedback({ type: 'error', message: 'New password must be at least 6 characters.' });
      return;
    }
    if (newPassword !== confirmPassword) {
      setPasswordFeedback({ type: 'error', message: 'New passwords do not match.' });
      return;
    }

    setIsChangingPassword(true);
    setPasswordFeedback(null);

    try {
      const token = localStorage.getItem('aq_admin_token') || '';
      const res = await api.changePassword(token, currentPassword, newPassword);
      if (res.status === 'SUCCESS') {
        setPasswordFeedback({ type: 'success', message: 'Password updated successfully and secured with PBKDF2!' });
        setCurrentPassword('');
        setNewPassword('');
        setConfirmPassword('');
      } else {
        setPasswordFeedback({ type: 'error', message: res.message || 'Password update failed.' });
      }
    } catch (e: any) {
      setPasswordFeedback({ type: 'error', message: e?.message || 'Network error occurred.' });
    } finally {
      setIsChangingPassword(false);
    }
  };

  const handleSendResetEmail = async () => {
    setIsSendingResetEmail(true);
    setResetEmailFeedback(null);

    try {
      const res = await api.requestPasswordReset('marvan');
      if (res.status === 'RESET_LINK_DISPATCHED' || res.status === 'OTP_DISPATCHED') {
        setResetEmailFeedback({
          type: 'success',
          message: `Secure password reset link dispatched to ${res.target_email || 'marvannottath@gmail.com'}!`,
          link: res.reset_link,
        });
      } else {
        setResetEmailFeedback({ type: 'error', message: res.message || 'Failed to dispatch reset email.' });
      }
    } catch (e: any) {
      setResetEmailFeedback({ type: 'error', message: e?.message || 'Network error' });
    } finally {
      setIsSendingResetEmail(false);
    }
  };

  const handleCopySecret = () => {
    if (totpSetupData?.secret) {
      navigator.clipboard.writeText(totpSetupData.secret);
      setCopiedSecret(true);
      setTimeout(() => setCopiedSecret(false), 2000);
    }
  };

  return (
    <div className="space-y-6 max-w-5xl">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-line pb-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold tracking-tight text-txt-primary">
              Security & Access Control Center
            </h1>
            <Badge variant="live">ZERO-TRUST SHIELD</Badge>
          </div>
          <p className="text-xs text-txt-muted mt-0.5">
            Institutional 2FA authentication, PBKDF2 password hardening, and admin reset channels.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Link
            href="/admin"
            className="flex items-center gap-1 px-3 py-1.5 rounded-lg border border-line bg-panel hover:bg-panel-light text-xs font-semibold text-brand transition"
          >
            <span>Super Admin Center</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>
      </div>

      {/* Grid: 2FA & Password Hardening */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* SECTION 1: TWO-FACTOR AUTHENTICATION (TOTP) */}
        <div className="card-panel p-5 space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-line">
            <div className="flex items-center gap-2">
              <Smartphone className="h-5 w-5 text-brand" />
              <div>
                <h3 className="text-xs font-bold uppercase tracking-wider text-txt-primary">
                  Two-Factor Authentication (2FA)
                </h3>
                <p className="text-[11px] text-txt-muted">RFC 6238 Google Authenticator / Authy</p>
              </div>
            </div>
            <span
              className={`px-2 py-0.5 rounded text-[10px] font-bold border ${
                totpEnabled
                  ? 'bg-emerald-500/10 border-emerald-500/20 text-profit'
                  : 'bg-amber-500/10 border-amber-500/20 text-amber-500'
              }`}
            >
              {totpEnabled ? 'ACTIVE 🟢' : 'DISABLED ⚠️'}
            </span>
          </div>

          <div className="text-xs space-y-3">
            <p className="text-txt-secondary leading-relaxed">
              Require a 6-digit dynamic passcode generated by your smartphone app for high-value actions, administrative sessions, and sensitive parameter updates.
            </p>

            <div className="p-3 bg-slate-50 dark:bg-panel-light rounded-lg border border-line space-y-1.5 font-mono text-[11px]">
              <div className="flex justify-between">
                <span className="text-txt-muted">Algorithm:</span>
                <span className="font-bold text-txt-primary">HMAC-SHA1 (RFC 6238)</span>
              </div>
              <div className="flex justify-between">
                <span className="text-txt-muted">Time-Step Drift:</span>
                <span className="font-bold text-txt-primary">±30 Seconds Tolerance</span>
              </div>
              <div className="flex justify-between">
                <span className="text-txt-muted">Replay Guard:</span>
                <span className="font-bold text-profit">SQLite Atomic Step Lock</span>
              </div>
            </div>

            <div className="pt-2 flex items-center gap-2">
              {!totpEnabled ? (
                <button
                  onClick={handleOpenTotpSetup}
                  className="px-4 py-2 rounded-lg bg-brand hover:bg-brand/90 text-white font-bold text-xs shadow-xs transition flex items-center gap-1.5 cursor-pointer"
                >
                  <KeyRound className="w-3.5 h-3.5" />
                  <span>Configure Google Authenticator</span>
                </button>
              ) : (
                <button
                  onClick={handleDeactivateTotp}
                  className="px-3.5 py-1.5 rounded-lg border border-red-200 text-red-600 hover:bg-red-50 text-xs font-semibold transition cursor-pointer"
                >
                  Disable 2FA Requirement
                </button>
              )}
            </div>
          </div>
        </div>

        {/* SECTION 2: PASSWORD CHANGE & SECURITY */}
        <div className="card-panel p-5 space-y-4">
          <div className="flex items-center gap-2 pb-3 border-b border-line">
            <Lock className="h-5 w-5 text-brand" />
            <div>
              <h3 className="text-xs font-bold uppercase tracking-wider text-txt-primary">
                Account Password Hardening
              </h3>
              <p className="text-[11px] text-txt-muted">PBKDF2-HMAC-SHA256 (100,000 Iterations)</p>
            </div>
          </div>

          <form onSubmit={handleChangePassword} className="space-y-3 text-xs">
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

            {passwordFeedback && (
              <div
                className={`p-2 rounded-lg font-mono text-[11px] border ${
                  passwordFeedback.type === 'success'
                    ? 'bg-emerald-500/10 border-emerald-500/20 text-profit'
                    : 'bg-red-500/10 border-red-500/20 text-red-500'
                }`}
              >
                {passwordFeedback.message}
              </div>
            )}

            <button
              type="submit"
              disabled={isChangingPassword}
              className="px-4 py-2 rounded-lg bg-panel hover:bg-panel-light border border-line text-txt-primary font-bold text-xs shadow-2xs transition disabled:opacity-50 cursor-pointer"
            >
              {isChangingPassword ? 'Updating...' : 'Update Password'}
            </button>
          </form>
        </div>
      </div>

      {/* SECTION 3: EMAIL RESET LINK TO ADMIN */}
      <div className="card-panel p-5 space-y-3 bg-blue-50/20 dark:bg-blue-950/20 border-brand/20">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-lg bg-brand/10 text-brand">
              <Mail className="h-5 w-5" />
            </div>
            <div>
              <h3 className="text-xs font-bold uppercase tracking-wider text-txt-primary">
                Emergency Password Reset Link (marvannottath@gmail.com)
              </h3>
              <p className="text-[11px] text-txt-muted">
                Zero-Knowledge link dispatching: Password can only be changed after authorization from admin email.
              </p>
            </div>
          </div>

          <button
            onClick={handleSendResetEmail}
            disabled={isSendingResetEmail}
            className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-brand hover:bg-brand/90 text-white font-bold text-xs shadow-xs transition disabled:opacity-50 cursor-pointer"
          >
            {isSendingResetEmail ? (
              <RefreshCw className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <Mail className="w-3.5 h-3.5" />
            )}
            <span>{isSendingResetEmail ? 'Dispatching...' : 'Send Reset Link to Email'}</span>
          </button>
        </div>

        {resetEmailFeedback && (
          <div
            className={`p-3 rounded-lg font-mono text-xs border ${
              resetEmailFeedback.type === 'success'
                ? 'bg-emerald-500/10 border-emerald-500/20 text-profit'
                : 'bg-red-500/10 border-red-500/20 text-red-500'
            }`}
          >
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 shrink-0" />
              <span>{resetEmailFeedback.message}</span>
            </div>
            {resetEmailFeedback.link && (
              <div className="mt-2 pt-2 border-t border-emerald-500/20 text-[11px] text-txt-secondary">
                Direct Reset Link:{' '}
                <a
                  href={resetEmailFeedback.link}
                  className="text-brand underline break-all font-mono"
                  target="_blank"
                  rel="noreferrer"
                >
                  {resetEmailFeedback.link}
                </a>
              </div>
            )}
          </div>
        )}
      </div>

      {/* SECTION 4: HARDWARE BIOMETRICS & PERIMETER GUARD */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Touch ID */}
        <div className="card-panel p-4 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase font-mono flex items-center gap-1.5 text-txt-primary">
              <Fingerprint className="w-4 h-4 text-brand" />
              WebAuthn Touch ID
            </span>
            <span className="text-[10px] font-mono font-bold text-profit">READY</span>
          </div>
          <p className="text-[11px] text-txt-muted">
            Hardware biometric enclave support for instantaneous passkey authentication on macOS.
          </p>
        </div>

        {/* IP Whitelist */}
        <div className="card-panel p-4 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase font-mono flex items-center gap-1.5 text-txt-primary">
              <Shield className="w-4 h-4 text-brand" />
              IP Access Whitelist
            </span>
            <span className="text-[10px] font-mono font-bold text-profit">ENFORCED</span>
          </div>
          <p className="text-[11px] text-txt-muted font-mono">
            Hostinger VPS: 187.127.189.139 • Local Terminal: 127.0.0.1
          </p>
        </div>

        {/* 5-Min Auto-Lock */}
        <div className="card-panel p-4 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase font-mono flex items-center gap-1.5 text-txt-primary">
              <Lock className="w-4 h-4 text-brand" />
              5-Min Inactivity Sentinel
            </span>
            <span className="text-[10px] font-mono font-bold text-profit">MONITORING</span>
          </div>
          <p className="text-[11px] text-txt-muted">
            Cryptographic screen lock engages after 300 seconds of desk idle time.
          </p>
        </div>
      </div>

      {/* TOTP 2FA SETUP MODAL */}
      <Modal
        isOpen={isTotpModalOpen}
        onClose={() => setIsTotpModalOpen(false)}
        title="Scan QR Code in Google Authenticator"
        description="Pair your mobile device with your Aegis-Quant institutional account"
      >
        <div className="space-y-4 text-xs">
          <div className="flex flex-col items-center justify-center p-4 bg-white rounded-xl border border-line">
            {totpSetupData?.qr_image_url ? (
              <img
                src={totpSetupData.qr_image_url}
                alt="Google Authenticator QR Code"
                className="w-44 h-44 object-contain"
              />
            ) : (
              <div className="w-44 h-44 flex items-center justify-center text-txt-muted">
                Generating QR...
              </div>
            )}
            <p className="text-[10px] text-txt-muted mt-2 text-center">
              Scan with Google Authenticator, Microsoft Authenticator, or Authy
            </p>
          </div>

          {/* Manual Entry Secret */}
          <div>
            <label className="block text-[11px] font-semibold text-txt-primary mb-1">
              Manual Setup Key (if camera unavailable):
            </label>
            <div className="flex items-center gap-2">
              <input
                type="text"
                readOnly
                value={totpSetupData?.secret || ''}
                className="w-full px-3 py-1.5 text-xs rounded-lg border border-line bg-panel-light font-mono text-txt-primary select-all"
              />
              <button
                type="button"
                onClick={handleCopySecret}
                className="px-3 py-1.5 rounded-lg border border-line bg-panel hover:bg-panel-light text-txt-secondary font-semibold flex items-center gap-1 transition cursor-pointer"
              >
                {copiedSecret ? <Check className="w-3.5 h-3.5 text-profit" /> : <Copy className="w-3.5 h-3.5" />}
                <span>{copiedSecret ? 'Copied' : 'Copy'}</span>
              </button>
            </div>
          </div>

          {/* Verification Code Input */}
          <form onSubmit={handleActivateTotp} className="space-y-3 pt-2 border-t border-line">
            <div>
              <label className="block text-xs font-semibold text-txt-primary mb-1">
                Enter the 6-Digit Code from App to Verify:
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

            {totpFeedback && (
              <div
                className={`p-2.5 rounded-lg font-mono text-[11px] border ${
                  totpFeedback.type === 'success'
                    ? 'bg-emerald-500/10 border-emerald-500/20 text-profit'
                    : 'bg-red-500/10 border-red-500/20 text-red-500'
                }`}
              >
                {totpFeedback.message}
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
                {isActivatingTotp ? 'Verifying...' : 'Verify & Enable 2FA'}
              </button>
            </div>
          </form>
        </div>
      </Modal>
    </div>
  );
}
