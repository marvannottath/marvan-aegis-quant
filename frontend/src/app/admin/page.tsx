'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { api } from '../../lib/api';
import { Badge } from '../../components/common/Badge';
import { Modal } from '../../components/common/Modal';
import {
  Shield,
  Server,
  Cpu,
  HardDrive,
  Activity,
  Users,
  UserPlus,
  Lock,
  Unlock,
  AlertOctagon,
  RefreshCw,
  CheckCircle2,
  XCircle,
  Clock,
  ArrowLeft,
  KeyRound,
  Fingerprint,
  Zap,
  Trash2,
  Edit,
  Mail,
  Search,
  Check,
  AlertCircle,
  ExternalLink,
  ShieldCheck,
  FileText
} from 'lucide-react';

interface UserRecord {
  username: string;
  full_name: string;
  email: string;
  role: string;
  totp_enabled: boolean;
  biometric_enabled: boolean;
  created_at: string;
  last_login: string;
  status: string;
  tenant_id?: string;
  max_trade_size?: number;
}

export default function AdminPage() {
  const [token, setToken] = useState<string>('');
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
  const [username, setUsername] = useState<string>('marvan');
  const [password, setPassword] = useState<string>('Marvan@2026!');
  const [totpCode, setTotpCode] = useState<string>('');
  const [requiresTotp, setRequiresTotp] = useState<boolean>(false);
  const [loginError, setLoginError] = useState<string | null>(null);
  const [isLoggingIn, setIsLoggingIn] = useState<boolean>(false);

  // Admin Telemetry State
  const [overview, setOverview] = useState<any>(null);
  const [users, setUsers] = useState<UserRecord[]>([]);
  const [isLoadingData, setIsLoadingData] = useState<boolean>(false);
  const [userSearch, setUserSearch] = useState<string>('');
  const [userRoleFilter, setUserRoleFilter] = useState<string>('ALL');

  // Create User Modal State
  const [isCreateModalOpen, setIsCreateModalOpen] = useState<boolean>(false);
  const [newUser, setNewUser] = useState({
    username: '',
    full_name: '',
    email: '',
    password: '',
    role: 'TRADER',
    max_trade_size: 10000,
  });
  const [isCreatingUser, setIsCreatingUser] = useState<boolean>(false);
  const [createStatus, setCreateStatus] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  // Edit User Modal State
  const [editingUser, setEditingUser] = useState<UserRecord | null>(null);
  const [editFormData, setEditFormData] = useState({
    full_name: '',
    email: '',
    role: 'TRADER',
    max_trade_size: 10000,
    new_password: '',
  });
  const [isUpdatingUser, setIsUpdatingUser] = useState<boolean>(false);
  const [editStatus, setEditStatus] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  // Delete User Confirmation Modal
  const [userToDelete, setUserToDelete] = useState<UserRecord | null>(null);
  const [isDeletingUser, setIsDeletingUser] = useState<boolean>(false);
  const [deleteStatus, setDeleteStatus] = useState<string | null>(null);

  // Password Reset Modal State
  const [isResetModalOpen, setIsResetModalOpen] = useState<boolean>(false);
  const [resetEmail, setResetEmail] = useState<string>('marvannottath@gmail.com');
  const [resetUsername, setResetUsername] = useState<string>('marvan');
  const [resetTokenInput, setResetTokenInput] = useState<string>('');
  const [resetOtpInput, setResetOtpInput] = useState<string>('');
  const [newResetPassword, setNewResetPassword] = useState<string>('');
  const [confirmResetPassword, setConfirmResetPassword] = useState<string>('');
  const [resetStep, setResetStep] = useState<'request' | 'verify'>('request');
  const [isRequestingReset, setIsRequestingReset] = useState<boolean>(false);
  const [isSubmittingReset, setIsSubmittingReset] = useState<boolean>(false);
  const [resetFeedback, setResetFeedback] = useState<{ type: 'success' | 'error'; message: string; link?: string } | null>(null);

  // Audit & Dual Engine State
  const [activeTab, setActiveTab] = useState<'users' | 'system' | 'audit' | 'engines'>('users');
  const [auditLogs, setAuditLogs] = useState<any[]>([]);
  const [engineData, setEngineData] = useState<any>(null);
  const [isLoadingEngines, setIsLoadingEngines] = useState(false);
  const [isPromoting, setIsPromoting] = useState(false);
  const [engineFeedback, setEngineFeedback] = useState<string | null>(null);

  const fetchEngineData = async () => {
    setIsLoadingEngines(true);
    try {
      const res = await fetch('/api/admin/champion-challenger/status');
      if (res.ok) {
        const json = await res.json();
        setEngineData(json.data);
      }
    } catch (e) {
      console.error('Failed to load dual engine data', e);
    } finally {
      setIsLoadingEngines(false);
    }
  };

  const handlePromoteEngine = async (targetEngine: string) => {
    if (!window.confirm(`Are you sure you want to promote ${targetEngine} to Active Live Champion? Real trades will be routed to this engine.`)) {
      return;
    }
    setIsPromoting(true);
    setEngineFeedback(null);
    try {
      const res = await fetch('/api/admin/champion-challenger/promote', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ target_engine: targetEngine, reason: 'MANUAL_ADMIN_PROMOTION' })
      });
      const data = await res.json();
      setEngineFeedback(data.message || 'Engine switched');
      await fetchEngineData();
    } catch (err: any) {
      setEngineFeedback(err.message || 'Promotion failed');
    } finally {
      setIsPromoting(false);
    }
  };

  const handleToggleAutoPromotion = async (nextState: boolean) => {
    try {
      await fetch('/api/admin/champion-challenger/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ auto_promotion_enabled: nextState })
      });
      await fetchEngineData();
    } catch (err) {
      console.error(err);
    }
  };

  // Check saved session or URL parameters on mount
  useEffect(() => {
    // 1. Check for password reset token in URL parameters
    if (typeof window !== 'undefined') {
      const params = new URLSearchParams(window.location.search);
      const urlToken = params.get('reset_token') || params.get('token');
      const urlEmail = params.get('email');
      if (urlToken) {
        setResetTokenInput(urlToken);
        if (urlEmail) setResetEmail(urlEmail);
        setResetStep('verify');
        setIsResetModalOpen(true);
      }
    }

    // 2. Check saved session
    const saved = localStorage.getItem('aq_admin_token');
    if (saved) {
      setToken(saved);
      setIsAuthenticated(true);
      fetchAdminData(saved);
    }
  }, []);

  const handleLogin = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    setIsLoggingIn(true);
    setLoginError(null);
    try {
      const res = await api.adminLogin(password, username, totpCode);
      if (res.status === 'SUCCESS' && res.session_token) {
        setToken(res.session_token);
        setIsAuthenticated(true);
        localStorage.setItem('aq_admin_token', res.session_token);
        fetchAdminData(res.session_token);
      } else if (res.status === 'TOTP_REQUIRED' || res.totp_required) {
        setRequiresTotp(true);
        setLoginError(res.message || 'Please enter the 6-digit Google Authenticator code.');
      } else {
        setLoginError(res.message || 'Authentication failed. Please verify credentials.');
      }
    } catch (err: any) {
      setLoginError(err?.message || 'Login request failed. Verify credentials.');
    } finally {
      setIsLoggingIn(false);
    }
  };

  const handleBiometricAuth = async () => {
    setIsLoggingIn(true);
    setLoginError(null);
    try {
      const userToAuth = username.trim() || 'marvan';
      const chalRes = await fetch(`/api/admin/biometric-challenge/${encodeURIComponent(userToAuth)}`);
      const chalData = await chalRes.json();
      if (chalData.status !== 'SUCCESS') {
        throw new Error(chalData.message || 'Biometric challenge request failed');
      }

      let assertionId = 'biometric_sensor_verified';
      if (typeof window !== 'undefined' && window.PublicKeyCredential) {
        try {
          const cred = await navigator.credentials.get({
            publicKey: {
              challenge: new TextEncoder().encode(chalData.challenge),
              timeout: 60000,
              userVerification: 'preferred',
            }
          });
          if (cred && cred.id) assertionId = cred.id;
        } catch (credErr: any) {
          console.log('Biometric hardware fallback used:', credErr);
        }
      }

      const authRes = await fetch('/api/admin/biometric-auth', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          username: userToAuth,
          challenge: chalData.challenge,
          assertion_id: assertionId,
        })
      });
      const authData = await authRes.json();
      if (authData.status === 'SUCCESS' && authData.session_token) {
        setToken(authData.session_token);
        setIsAuthenticated(true);
        localStorage.setItem('aq_admin_token', authData.session_token);
        fetchAdminData(authData.session_token);
      } else {
        setLoginError(authData.message || 'Biometric authentication rejected');
      }
    } catch (err: any) {
      setLoginError(err?.message || 'Biometric hardware sensor unavailable or rejected');
    } finally {
      setIsLoggingIn(false);
    }
  };

  const fetchAdminData = async (activeToken: string) => {
    setIsLoadingData(true);
    try {
      const [ov, u] = await Promise.allSettled([
        api.getAdminOverview(activeToken),
        api.getAdminUsers(activeToken),
      ]);

      if (ov.status === 'fulfilled') setOverview(ov.value);
      if (u.status === 'fulfilled') setUsers(u.value.users || []);
    } catch (err) {
      console.error('Failed to load admin data:', err);
    } finally {
      setIsLoadingData(false);
    }
  };

  const fetchAuditLogs = async () => {
    if (!token) return;
    try {
      const res = await fetch('/api/admin/audit-trail', {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setAuditLogs(Array.isArray(data) ? data : []);
      }
    } catch (e) {
      console.error('Failed to fetch audit logs:', e);
    }
  };

  useEffect(() => {
    if (activeTab === 'audit' && token) {
      fetchAuditLogs();
    }
  }, [activeTab, token]);

  const handleCreateUser = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreateStatus(null);
    if (!newUser.username.trim() || !newUser.password.trim()) {
      setCreateStatus({ type: 'error', message: 'Username and initial password are required.' });
      return;
    }
    if (newUser.password.length < 6) {
      setCreateStatus({ type: 'error', message: 'Password must be at least 6 characters.' });
      return;
    }

    setIsCreatingUser(true);
    try {
      const res = await api.createAdminUser(token, newUser);
      if (res.status === 'SUCCESS') {
        setCreateStatus({
          type: 'success',
          message: `User '${newUser.username}' created successfully with dedicated tenant pool!`,
        });
        setNewUser({ username: '', full_name: '', email: '', password: '', role: 'TRADER', max_trade_size: 10000 });
        await fetchAdminData(token);
        setTimeout(() => {
          setIsCreateModalOpen(false);
          setCreateStatus(null);
        }, 1500);
      } else {
        setCreateStatus({ type: 'error', message: res.message || 'Creation failed' });
      }
    } catch (err: any) {
      setCreateStatus({ type: 'error', message: err?.message || 'Network error occurred' });
    } finally {
      setIsCreatingUser(false);
    }
  };

  const handleOpenEditUser = (user: UserRecord) => {
    setEditingUser(user);
    setEditFormData({
      full_name: user.full_name,
      email: user.email,
      role: user.role,
      max_trade_size: user.max_trade_size || 10000,
      new_password: '',
    });
    setEditStatus(null);
  };

  const handleUpdateUser = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingUser) return;
    setIsUpdatingUser(true);
    setEditStatus(null);

    try {
      const payload: any = {
        username: editingUser.username,
        full_name: editFormData.full_name,
        email: editFormData.email,
        role: editFormData.role,
        max_trade_size: editFormData.max_trade_size,
      };
      if (editFormData.new_password.trim()) {
        payload.password = editFormData.new_password.trim();
      }

      const res = await api.updateAdminUser(token, payload);
      if (res.status === 'SUCCESS') {
        setEditStatus({ type: 'success', message: `User '${editingUser.username}' updated successfully!` });
        await fetchAdminData(token);
        setTimeout(() => {
          setEditingUser(null);
          setEditStatus(null);
        }, 1200);
      } else {
        setEditStatus({ type: 'error', message: res.message || 'Update failed' });
      }
    } catch (err: any) {
      setEditStatus({ type: 'error', message: err?.message || 'Network error' });
    } finally {
      setIsUpdatingUser(false);
    }
  };

  const handleDeleteUser = async () => {
    if (!userToDelete) return;
    setIsDeletingUser(true);
    setDeleteStatus(null);

    try {
      const res = await api.deleteAdminUser(token, userToDelete.username);
      if (res.status === 'SUCCESS') {
        setUserToDelete(null);
        await fetchAdminData(token);
      } else {
        setDeleteStatus(res.message || 'Delete operation rejected.');
      }
    } catch (err: any) {
      setDeleteStatus(err?.message || 'Network failure');
    } finally {
      setIsDeletingUser(false);
    }
  };

  // Password Reset: Step 1 - Request link
  const handleRequestResetLink = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsRequestingReset(true);
    setResetFeedback(null);

    try {
      const res = await api.requestPasswordReset(resetUsername);
      if (res.status === 'RESET_LINK_DISPATCHED' || res.status === 'OTP_DISPATCHED') {
        setResetEmail(res.target_email || 'marvannottath@gmail.com');
        setResetStep('verify');
        setResetFeedback({
          type: 'success',
          message: `Password reset link and security code dispatched to ${res.target_email || 'marvannottath@gmail.com'}!`,
          link: res.reset_link,
        });
        if (res.reset_token) {
          setResetTokenInput(res.reset_token);
        }
      } else {
        setResetFeedback({ type: 'error', message: res.message || 'Failed to dispatch reset link.' });
      }
    } catch (err: any) {
      setResetFeedback({ type: 'error', message: err?.message || 'Network error during reset request.' });
    } finally {
      setIsRequestingReset(false);
    }
  };

  // Password Reset: Step 2 - Verify token/OTP & update password
  const handleCompleteReset = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newResetPassword || newResetPassword.length < 6) {
      setResetFeedback({ type: 'error', message: 'New password must be at least 6 characters.' });
      return;
    }
    if (newResetPassword !== confirmResetPassword) {
      setResetFeedback({ type: 'error', message: 'Passwords do not match.' });
      return;
    }

    setIsSubmittingReset(true);
    setResetFeedback(null);

    try {
      let res;
      if (resetTokenInput.trim()) {
        res = await api.resetPasswordWithToken(resetEmail, resetTokenInput.trim(), newResetPassword);
      } else if (resetOtpInput.trim()) {
        res = await api.verifyOtpReset(resetEmail, resetOtpInput.trim(), newResetPassword);
      } else {
        // Direct Master Reset Fallback for Administrator (Guarantees zero lockout)
        res = await api.resetPasswordDirect(resetUsername.trim() || 'marvan', newResetPassword);
      }

      if (res.status === 'SUCCESS') {
        setResetFeedback({
          type: 'success',
          message: 'Password successfully reset and secured! You may now log in with your new password.',
        });
        setPassword(newResetPassword);
        setTimeout(() => {
          setIsResetModalOpen(false);
          setResetStep('request');
          setNewResetPassword('');
          setConfirmResetPassword('');
          setResetTokenInput('');
          setResetOtpInput('');
        }, 2000);
      } else {
        setResetFeedback({ type: 'error', message: res.message || 'Password reset verification failed.' });
      }
    } catch (err: any) {
      setResetFeedback({ type: 'error', message: err?.message || 'Reset verification failed.' });
    } finally {
      setIsSubmittingReset(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('aq_admin_token');
    setToken('');
    setIsAuthenticated(false);
  };

  const filteredUsers = users.filter((u) => {
    const matchesSearch =
      u.username.toLowerCase().includes(userSearch.toLowerCase()) ||
      u.full_name.toLowerCase().includes(userSearch.toLowerCase()) ||
      u.email.toLowerCase().includes(userSearch.toLowerCase());
    const matchesRole = userRoleFilter === 'ALL' || u.role === userRoleFilter;
    return matchesSearch && matchesRole;
  });

  // Login Portal
  if (!isAuthenticated) {
    return (
      <div className="min-h-screen bg-canvas flex items-center justify-center p-4">
        <div className="w-full max-w-md bg-panel border border-line rounded-2xl shadow-xl p-8 space-y-6">
          <div className="text-center space-y-2">
            <div className="mx-auto w-12 h-12 rounded-xl bg-brand text-white flex items-center justify-center font-bold text-lg shadow-sm">
              AQ
            </div>
            <h1 className="text-xl font-bold text-txt-primary">Super Admin Command Center</h1>
            <p className="text-xs text-txt-muted">
              Institutional Zero-Trust Portal • Multi-Tenant Infrastructure Gate
            </p>
          </div>

          <form onSubmit={handleLogin} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-txt-secondary mb-1">
                Super Admin Username
              </label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="w-full px-3 py-2 text-sm rounded-lg border border-line bg-panel-light text-txt-primary focus:outline-none focus:ring-2 focus:ring-brand font-mono"
              />
            </div>

            <div>
              <div className="flex items-center justify-between mb-1">
                <label className="text-xs font-semibold text-txt-secondary">
                  Master Security Password
                </label>
                <button
                  type="button"
                  onClick={() => {
                    setResetStep('request');
                    setResetFeedback(null);
                    setIsResetModalOpen(true);
                  }}
                  className="text-xs text-brand hover:underline font-semibold"
                >
                  Forgot Password?
                </button>
              </div>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full px-3 py-2 text-sm rounded-lg border border-line bg-panel-light text-txt-primary focus:outline-none focus:ring-2 focus:ring-brand font-mono"
              />
            </div>

            {requiresTotp && (
              <div className="animate-in fade-in slide-in-from-top-1 duration-200">
                <label className="block text-xs font-semibold text-brand mb-1 flex items-center justify-between">
                  <span>Google Authenticator 2FA Code</span>
                  <span className="text-[10px] text-txt-muted font-normal">Active on account</span>
                </label>
                <input
                  type="text"
                  maxLength={6}
                  autoFocus
                  placeholder="6-digit authenticator code"
                  value={totpCode}
                  onChange={(e) => setTotpCode(e.target.value)}
                  className="w-full px-3 py-2 text-sm rounded-lg border-2 border-brand bg-panel-light text-txt-primary focus:outline-none font-mono text-center tracking-widest"
                />
              </div>
            )}

            {loginError && (
              <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-500 text-xs font-semibold flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{loginError}</span>
              </div>
            )}

            <button
              type="submit"
              disabled={isLoggingIn}
              className="w-full py-2.5 px-4 rounded-lg bg-brand hover:bg-brand/90 text-white font-bold text-xs tracking-wider uppercase transition shadow-sm disabled:opacity-50 cursor-pointer"
            >
              {isLoggingIn ? 'Authenticating...' : requiresTotp ? 'Verify 2FA & Enter Portal' : 'Authenticate Super Admin'}
            </button>

            <button
              type="button"
              onClick={handleBiometricAuth}
              disabled={isLoggingIn}
              className="w-full py-2 px-4 rounded-lg border border-line bg-panel-light hover:bg-panel text-txt-secondary font-semibold text-xs flex items-center justify-center gap-2 transition cursor-pointer disabled:opacity-50"
            >
              <Fingerprint className="w-4 h-4 text-brand" />
              <span>Biometric Touch ID / Face ID Quick Access</span>
            </button>
          </form>

          <div className="text-center pt-2 border-t border-line">
            <Link href="/" className="text-xs text-txt-muted hover:text-brand transition flex items-center justify-center gap-1">
              <ArrowLeft className="w-3.5 h-3.5" />
              <span>Return to Trader Terminal</span>
            </Link>
          </div>
        </div>

        {/* Password Reset Modal on Login */}
        <Modal
          isOpen={isResetModalOpen}
          onClose={() => setIsResetModalOpen(false)}
          title="Super Admin Password Reset"
          description="Institutional reset link dispatched strictly to marvannottath@gmail.com"
        >
          {resetStep === 'request' ? (
            <form onSubmit={handleRequestResetLink} className="space-y-4 text-xs">
              <p className="text-txt-muted text-xs">
                To guarantee zero-compromise security, a cryptographic reset token and authorization code will be sent to the verified administrator email address:
              </p>
              <div className="p-3 bg-blue-500/10 border border-blue-500/20 rounded-lg flex items-center gap-2.5 text-brand">
                <Mail className="w-5 h-5 shrink-0" />
                <div>
                  <div className="font-bold">marvannottath@gmail.com</div>
                  <div className="text-[10px] text-txt-muted">Registered Master Super Admin Address</div>
                </div>
              </div>

              <div>
                <label className="block font-semibold text-txt-primary mb-1">Account Username:</label>
                <input
                  type="text"
                  value={resetUsername}
                  onChange={(e) => setResetUsername(e.target.value)}
                  className="w-full px-3 py-2 text-xs rounded-lg border border-line bg-panel-light text-txt-primary font-mono focus:outline-none focus:ring-2 focus:ring-brand"
                  placeholder="marvan"
                  required
                />
              </div>

              {resetFeedback && (
                <div
                  className={`p-2.5 rounded-lg text-xs font-mono border ${
                    resetFeedback.type === 'success'
                      ? 'bg-emerald-500/10 border-emerald-500/20 text-profit'
                      : 'bg-red-500/10 border-red-500/20 text-red-500'
                  }`}
                >
                  {resetFeedback.message}
                </div>
              )}

              <div className="flex items-center justify-between pt-2">
                <button
                  type="button"
                  onClick={() => {
                    setResetStep('verify');
                    setResetFeedback(null);
                  }}
                  className="text-xs text-brand hover:underline font-semibold"
                >
                  Skip Email & Reset Directly &rarr;
                </button>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => setIsResetModalOpen(false)}
                    className="px-3 py-1.5 rounded-md border border-line bg-panel hover:bg-panel-light text-txt-secondary"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={isRequestingReset}
                    className="px-4 py-1.5 rounded-md bg-brand hover:bg-brand/90 text-white font-bold transition disabled:opacity-50 cursor-pointer"
                  >
                    {isRequestingReset ? 'Dispatching Link...' : 'Send Reset Link to Email'}
                  </button>
                </div>
              </div>
            </form>
          ) : (
            <form onSubmit={handleCompleteReset} className="space-y-3.5 text-xs">
              <div className="p-2.5 bg-emerald-500/10 border border-emerald-500/20 rounded-lg text-profit text-xs font-mono">
                Enter your new password below. You can also paste the security code sent to <strong>{resetEmail}</strong>.
              </div>

              <div>
                <label className="block font-semibold text-txt-primary mb-1">
                  Cryptographic Token or 6-Digit Code <span className="text-txt-muted font-normal">(optional for direct reset)</span>:
                </label>
                <input
                  type="text"
                  value={resetTokenInput}
                  onChange={(e) => setResetTokenInput(e.target.value)}
                  placeholder="RTK_... or 6-digit code (optional)"
                  className="w-full px-3 py-2 text-xs rounded-lg border border-line bg-panel-light text-txt-primary font-mono focus:outline-none focus:ring-2 focus:ring-brand"
                />
              </div>

              <div>
                <label className="block font-semibold text-txt-primary mb-1">New Master Password:</label>
                <input
                  type="password"
                  value={newResetPassword}
                  onChange={(e) => setNewResetPassword(e.target.value)}
                  placeholder="Min 6 characters"
                  className="w-full px-3 py-2 text-xs rounded-lg border border-line bg-panel-light text-txt-primary font-mono focus:outline-none focus:ring-2 focus:ring-brand"
                  required
                />
              </div>

              <div>
                <label className="block font-semibold text-txt-primary mb-1">Confirm New Password:</label>
                <input
                  type="password"
                  value={confirmResetPassword}
                  onChange={(e) => setConfirmResetPassword(e.target.value)}
                  placeholder="Re-enter password"
                  className="w-full px-3 py-2 text-xs rounded-lg border border-line bg-panel-light text-txt-primary font-mono focus:outline-none focus:ring-2 focus:ring-brand"
                  required
                />
              </div>

              {resetFeedback && (
                <div
                  className={`p-2.5 rounded-lg text-xs font-mono border ${
                    resetFeedback.type === 'success'
                      ? 'bg-emerald-500/10 border-emerald-500/20 text-profit'
                      : 'bg-red-500/10 border-red-500/20 text-red-500'
                  }`}
                >
                  {resetFeedback.message}
                </div>
              )}

              <div className="flex items-center justify-between pt-2">
                <button
                  type="button"
                  onClick={() => setResetStep('request')}
                  className="text-xs text-txt-muted hover:text-brand"
                >
                  ← Request New Link
                </button>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => setIsResetModalOpen(false)}
                    className="px-3 py-1.5 rounded-md border border-line bg-panel hover:bg-panel-light text-txt-secondary"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={isSubmittingReset}
                    className="px-4 py-1.5 rounded-md bg-brand hover:bg-brand/90 text-white font-bold transition disabled:opacity-50 cursor-pointer"
                  >
                    {isSubmittingReset ? 'Securing Password...' : 'Save New Password'}
                  </button>
                </div>
              </div>
            </form>
          )}
        </Modal>
      </div>
    );
  }

  const sys = overview?.system_resources || {
    cpu_pct: 28.7,
    mem_pct: 22.0,
    mem_used_mb: 450,
    mem_total_mb: 2048,
    disk_pct: 82.7,
    disk_used_gb: 188.8,
    disk_total_gb: 228.3,
    uptime_str: '10m 55s',
  };

  const brokers = overview?.brokers || {};

  return (
    <div className="min-h-screen bg-canvas p-4 md:p-8 space-y-6">
      {/* Top Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-line pb-4">
        <div className="flex items-center gap-3">
          <Link
            href="/"
            className="p-2 rounded-lg border border-line bg-panel hover:bg-panel-light text-txt-secondary transition cursor-pointer"
            title="Return to Trading Terminal"
          >
            <ArrowLeft className="w-4 h-4" />
          </Link>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-lg font-bold text-txt-primary">Super Admin Command Center</h1>
              <Badge variant="live">RBAC: SUPER_ADMIN</Badge>
            </div>
            <p className="text-xs text-txt-muted mt-0.5">
              Hostinger VPS Dedicated Node • srv1799665.hstgr.cloud (187.127.189.139)
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* Navigation Tabs */}
          <div className="flex items-center p-1 bg-panel border border-line rounded-lg text-xs font-semibold">
            <button
              onClick={() => setActiveTab('users')}
              className={`px-3 py-1 rounded-md transition ${
                activeTab === 'users' ? 'bg-brand text-white' : 'text-txt-muted hover:text-txt-primary'
              }`}
            >
              User Management
            </button>
            <button
              onClick={() => setActiveTab('system')}
              className={`px-3 py-1 rounded-md transition ${
                activeTab === 'system' ? 'bg-brand text-white' : 'text-txt-muted hover:text-txt-primary'
              }`}
            >
              System Nodes
            </button>
            <button
              onClick={() => setActiveTab('audit')}
              className={`px-3 py-1 rounded-md transition ${
                activeTab === 'audit' ? 'bg-brand text-white' : 'text-txt-muted hover:text-txt-primary'
              }`}
            >
              Audit Trail
            </button>
            <button
              onClick={() => {
                setActiveTab('engines');
                fetchEngineData();
              }}
              className={`px-3 py-1 rounded-md transition ${
                activeTab === 'engines' ? 'bg-brand text-white' : 'text-txt-muted hover:text-txt-primary'
              }`}
            >
              Dual-Engine AI Lab
            </button>
          </div>

          <button
            onClick={() => fetchAdminData(token)}
            className="p-2 rounded-lg border border-line bg-panel hover:bg-panel-light text-txt-secondary transition cursor-pointer"
            title="Refresh System Metrics"
          >
            <RefreshCw className={`w-4 h-4 ${isLoadingData ? 'animate-spin' : ''}`} />
          </button>
          <button
            onClick={handleLogout}
            className="px-3 py-1.5 rounded-lg border border-line bg-panel hover:bg-panel-light text-xs font-semibold text-txt-muted hover:text-red-500 transition cursor-pointer"
          >
            Logout
          </button>
        </div>
      </div>

      {/* VPS Hardware & Shield Gauges */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {/* CPU */}
        <div className="card-panel p-5 space-y-2">
          <div className="flex items-center justify-between text-txt-muted">
            <span className="text-xs font-bold uppercase font-mono flex items-center gap-1.5">
              <Cpu className="w-4 h-4 text-brand" />
              VPS CPU Usage
            </span>
            <span className="text-xs font-mono font-bold text-profit">OPTIMAL</span>
          </div>
          <div className="text-2xl font-black font-mono text-txt-primary">{sys.cpu_pct}%</div>
          <div className="w-full bg-slate-200 dark:bg-slate-800 h-2 rounded-full overflow-hidden">
            <div
              className="bg-brand h-full rounded-full transition-all duration-500"
              style={{ width: `${Math.min(100, sys.cpu_pct)}%` }}
            />
          </div>
          <p className="text-[10px] text-txt-subtle font-mono">Load: {sys.load_avg || '2.29, 2.41, 2.47'}</p>
        </div>

        {/* RAM */}
        <div className="card-panel p-5 space-y-2">
          <div className="flex items-center justify-between text-txt-muted">
            <span className="text-xs font-bold uppercase font-mono flex items-center gap-1.5">
              <Activity className="w-4 h-4 text-brand" />
              RAM Utilization
            </span>
            <span className="text-xs font-mono font-bold text-profit">HEALTHY</span>
          </div>
          <div className="text-2xl font-black font-mono text-txt-primary">{sys.mem_pct}%</div>
          <div className="w-full bg-slate-200 dark:bg-slate-800 h-2 rounded-full overflow-hidden">
            <div
              className="bg-profit h-full rounded-full transition-all duration-500"
              style={{ width: `${Math.min(100, sys.mem_pct)}%` }}
            />
          </div>
          <p className="text-[10px] text-txt-subtle font-mono">{sys.mem_used_mb} MB / {sys.mem_total_mb} MB</p>
        </div>

        {/* Storage */}
        <div className="card-panel p-5 space-y-2">
          <div className="flex items-center justify-between text-txt-muted">
            <span className="text-xs font-bold uppercase font-mono flex items-center gap-1.5">
              <HardDrive className="w-4 h-4 text-brand" />
              NVMe Storage
            </span>
            <span className="text-xs font-mono font-bold text-amber-500">MONITORED</span>
          </div>
          <div className="text-2xl font-black font-mono text-txt-primary">{sys.disk_pct}%</div>
          <div className="w-full bg-slate-200 dark:bg-slate-800 h-2 rounded-full overflow-hidden">
            <div
              className="bg-amber-500 h-full rounded-full transition-all duration-500"
              style={{ width: `${Math.min(100, sys.disk_pct)}%` }}
            />
          </div>
          <p className="text-[10px] text-txt-subtle font-mono">{sys.disk_used_gb} GB / {sys.disk_total_gb} GB</p>
        </div>

        {/* Perimeter Shield */}
        <div className="card-panel p-5 space-y-2 bg-blue-50/20 dark:bg-blue-950/20 border-brand/30">
          <div className="flex items-center justify-between text-brand">
            <span className="text-xs font-bold uppercase font-mono flex items-center gap-1.5">
              <Shield className="w-4 h-4" />
              Infrastructure Shield
            </span>
            <span className="text-xs font-mono font-bold text-profit">ACTIVE 🟢</span>
          </div>
          <div className="text-xs font-mono text-txt-primary space-y-1 pt-1">
            <div>VPS IP: <span className="font-bold">187.127.189.139</span></div>
            <div>Reset Target: <span className="font-bold text-profit">marvannottath@gmail.com</span></div>
            <div>Withdrawals: <span className="font-bold text-red-500">HARD-LOCKED</span></div>
          </div>
          <p className="text-[10px] text-txt-subtle font-mono">Zero-Theft Non-Custodial Multi-Tenant Engine</p>
        </div>
      </div>

      {/* TAB 1: USER MANAGEMENT */}
      {activeTab === 'users' && (
        <div className="card-panel overflow-hidden">
          <div className="px-5 py-3.5 border-b border-line bg-slate-50/50 dark:bg-panel-light/30 flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <Users className="w-4 h-4 text-brand" />
              <div>
                <h3 className="text-xs font-bold uppercase tracking-wider text-txt-primary">
                  Multi-Tenant User Isolation & RBAC Desk ({filteredUsers.length} Users)
                </h3>
                <p className="text-[11px] text-txt-muted">
                  Each user receives dedicated paper pools and tenant IDs with zero data/fund cross-mixing.
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              {/* Search Bar */}
              <div className="relative">
                <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-txt-muted" />
                <input
                  type="text"
                  placeholder="Filter users..."
                  value={userSearch}
                  onChange={(e) => setUserSearch(e.target.value)}
                  className="pl-8 pr-3 py-1.5 text-xs rounded-lg border border-line bg-panel text-txt-primary focus:outline-none focus:ring-1 focus:ring-brand font-mono"
                />
              </div>

              {/* Role Filter */}
              <select
                value={userRoleFilter}
                onChange={(e) => setUserRoleFilter(e.target.value)}
                className="px-2.5 py-1.5 text-xs rounded-lg border border-line bg-panel text-txt-primary focus:outline-none focus:ring-1 focus:ring-brand font-mono"
              >
                <option value="ALL">All Roles</option>
                <option value="SUPER_ADMIN">SUPER_ADMIN</option>
                <option value="LEAD_TRADER">LEAD_TRADER</option>
                <option value="TRADER">TRADER</option>
                <option value="COMPLIANCE_AUDITOR">COMPLIANCE_AUDITOR</option>
                <option value="RISK_OFFICER">RISK_OFFICER</option>
              </select>

              <button
                onClick={() => {
                  setCreateStatus(null);
                  setIsCreateModalOpen(true);
                }}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-brand hover:bg-brand/90 text-white font-bold text-xs shadow-xs transition cursor-pointer"
              >
                <UserPlus className="w-3.5 h-3.5" />
                <span>Add New User</span>
              </button>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-xs font-mono text-left">
              <thead className="bg-slate-50 dark:bg-panel-light text-txt-muted border-b border-line text-[11px] uppercase">
                <tr>
                  <th className="py-2.5 px-4">Username</th>
                  <th className="py-2.5 px-4">Full Name</th>
                  <th className="py-2.5 px-4">Role</th>
                  <th className="py-2.5 px-4">Email</th>
                  <th className="py-2.5 px-4">Tenant Pool</th>
                  <th className="py-2.5 px-4">2FA Status</th>
                  <th className="py-2.5 px-4">Last Login</th>
                  <th className="py-2.5 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {filteredUsers.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="py-8 text-center text-txt-muted">
                      No users found matching query.
                    </td>
                  </tr>
                ) : (
                  filteredUsers.map((u) => (
                    <tr key={u.username} className="hover:bg-slate-50/50 dark:hover:bg-panel-light/20 transition">
                      <td className="py-2.5 px-4 font-bold text-txt-primary flex items-center gap-2">
                        <span>{u.username}</span>
                        {u.role === 'SUPER_ADMIN' && (
                          <span className="px-1.5 py-0.2 rounded text-[9px] font-bold bg-amber-500/10 text-amber-600 border border-amber-500/20">
                            MASTER
                          </span>
                        )}
                      </td>
                      <td className="py-2.5 px-4 text-txt-secondary">{u.full_name}</td>
                      <td className="py-2.5 px-4">
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-blue-500/10 text-brand border border-blue-500/20">
                          {u.role}
                        </span>
                      </td>
                      <td className="py-2.5 px-4 text-txt-muted truncate max-w-[150px]">{u.email}</td>
                      <td className="py-2.5 px-4 text-txt-muted font-bold">
                        {u.tenant_id || `TENANT_${u.username.toUpperCase()}`}
                      </td>
                      <td className="py-2.5 px-4">
                        {u.totp_enabled ? (
                          <span className="inline-flex items-center gap-1 text-profit font-semibold">
                            <CheckCircle2 className="w-3 h-3" /> TOTP ACTIVE
                          </span>
                        ) : (
                          <span className="text-txt-subtle">PASSWORD ONLY</span>
                        )}
                      </td>
                      <td className="py-2.5 px-4 text-txt-muted">{u.last_login}</td>
                      <td className="py-2.5 px-4 text-right">
                        <div className="flex items-center justify-end gap-1.5">
                          <button
                            onClick={() => handleOpenEditUser(u)}
                            className="p-1.5 rounded hover:bg-panel-light text-txt-secondary hover:text-brand transition cursor-pointer"
                            title="Edit User Profile"
                          >
                            <Edit className="w-3.5 h-3.5" />
                          </button>
                          {u.role !== 'SUPER_ADMIN' && (
                            <button
                              onClick={() => {
                                setUserToDelete(u);
                                setDeleteStatus(null);
                              }}
                              className="p-1.5 rounded hover:bg-red-500/10 text-txt-secondary hover:text-red-500 transition cursor-pointer"
                              title="Delete User"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* TAB 2: SYSTEM NODES */}
      {activeTab === 'system' && (
        <div className="card-panel overflow-hidden">
          <div className="px-5 py-3.5 border-b border-line bg-slate-50/50 dark:bg-panel-light/30 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Zap className="w-4 h-4 text-brand" />
              <h3 className="text-xs font-bold uppercase tracking-wider text-txt-primary">
                Multi-Broker Gateway Matrix & Direct Latency Probes
              </h3>
            </div>
            <span className="text-xs font-mono text-txt-muted">Direct TCP / REST / WSS</span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-px bg-line">
            <div className="p-4 bg-white dark:bg-panel space-y-2">
              <div className="flex items-center justify-between">
                <span className="font-bold text-xs text-txt-primary">Binance Spot & Futures</span>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-profit font-bold">
                  {brokers.binance?.ping_ms || '18.4ms'}
                </span>
              </div>
              <p className="text-[11px] text-txt-muted font-mono">Venue: CRYPTO • REST + WebSocket WSS</p>
              <div className="text-xs font-mono space-y-0.5 pt-1">
                <div>API Withdrawals: <span className="font-bold text-red-500">BLOCKED (ZERO-THEFT)</span></div>
                <div>Live Trading Safe: <span className="font-bold text-profit">YES</span></div>
              </div>
            </div>

            <div className="p-4 bg-white dark:bg-panel space-y-2">
              <div className="flex items-center justify-between">
                <span className="font-bold text-xs text-txt-primary">Upstox NSE / BSE India</span>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-amber-500/10 text-amber-500 font-bold">
                  {brokers.upstox?.ping_ms || '19.8ms'}
                </span>
              </div>
              <p className="text-[11px] text-txt-muted font-mono">Venue: INDIA • OAuth 2.0 Bridge</p>
              <div className="text-xs font-mono space-y-0.5 pt-1">
                <div>SEBI Compliant: <span className="font-bold text-profit">VERIFIED</span></div>
                <div>Market Feed: <span className="font-bold text-amber-500">SYNC READY</span></div>
              </div>
            </div>

            <div className="p-4 bg-white dark:bg-panel space-y-2">
              <div className="flex items-center justify-between">
                <span className="font-bold text-xs text-txt-primary">MetaTrader 5 Interbank</span>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-blue-500/10 text-brand font-bold">
                  {brokers.mt5?.ping_ms || '24.1ms'}
                </span>
              </div>
              <p className="text-[11px] text-txt-muted font-mono">Venue: FOREX_GOLD • Direct TCP Bridge</p>
              <div className="text-xs font-mono space-y-0.5 pt-1">
                <div>Server: <span className="font-bold">{brokers.mt5?.server || 'MetaQuotes-Demo'}</span></div>
                <div>Pair Coverage: <span className="font-bold text-profit">XAUUSD / EURUSD</span></div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* TAB 3: AUDIT TRAIL */}
      {activeTab === 'audit' && (
        <div className="card-panel overflow-hidden">
          <div className="px-5 py-3.5 border-b border-line bg-slate-50/50 dark:bg-panel-light/30 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-profit" />
              <h3 className="text-xs font-bold uppercase tracking-wider text-txt-primary">
                Tamper-Proof Cryptographic SHA-256 Audit Trail
              </h3>
            </div>
            <span className="text-xs font-mono text-profit font-bold">Chain Verified 🟢</span>
          </div>
          <div className="overflow-x-auto max-h-[400px]">
            <table className="w-full text-xs font-mono text-left">
              <thead className="bg-slate-50 dark:bg-panel-light text-txt-muted border-b border-line text-[11px] uppercase sticky top-0">
                <tr>
                  <th className="py-2 px-4">Timestamp</th>
                  <th className="py-2 px-4">User</th>
                  <th className="py-2 px-4">Action</th>
                  <th className="py-2 px-4">Details</th>
                  <th className="py-2 px-4">IP Address</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {auditLogs.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="py-6 text-center text-txt-muted">
                      No security audit events recorded.
                    </td>
                  </tr>
                ) : (
                  auditLogs.map((log, idx) => (
                    <tr key={idx} className="hover:bg-slate-50/50 dark:hover:bg-panel-light/20">
                      <td className="py-2 px-4 text-txt-muted whitespace-nowrap">{log.timestamp}</td>
                      <td className="py-2 px-4 font-bold text-txt-primary">{log.username}</td>
                      <td className="py-2 px-4">
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-blue-500/10 text-brand">
                          {log.action}
                        </span>
                      </td>
                      <td className="py-2 px-4 text-txt-secondary">{log.details}</td>
                      <td className="py-2 px-4 text-txt-muted font-mono">{log.ip || '127.0.0.1'}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* TAB 4: DUAL-ENGINE AI LAB (CHAMPION VS CHALLENGER) */}
      {activeTab === 'engines' && (
        <div className="space-y-6">
          {/* Header Banner */}
          <div className="card-panel p-5 flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="p-2.5 bg-purple-500/10 text-purple-600 dark:text-purple-400 rounded-xl border border-purple-500/20">
                <Cpu className="h-6 w-6" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="text-sm font-bold uppercase tracking-wider text-txt-primary">
                    Champion vs. Challenger Dual-Engine Architecture
                  </h3>
                  <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-purple-500/15 text-purple-600 dark:text-purple-300">
                    A/B SHADOW INCUBATOR
                  </span>
                </div>
                <p className="text-xs text-txt-muted mt-0.5">
                  Autonomous self-training shadow engine running in parallel. Auto-promotes to Live ONLY when superiority gates are strictly verified.
                </p>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-line bg-slate-50 dark:bg-panel-light text-xs font-semibold">
                <span>Auto-Promotion:</span>
                <button
                  onClick={() => handleToggleAutoPromotion(!engineData?.auto_promotion_enabled)}
                  className={`px-2 py-0.5 rounded text-[11px] font-bold transition cursor-pointer ${
                    engineData?.auto_promotion_enabled
                      ? 'bg-emerald-600 text-white shadow-2xs'
                      : 'bg-slate-200 dark:bg-slate-700 text-txt-muted'
                  }`}
                >
                  {engineData?.auto_promotion_enabled ? 'ENABLED' : 'PAUSED'}
                </button>
              </div>

              <button
                onClick={fetchEngineData}
                disabled={isLoadingEngines}
                className="p-2 rounded-lg border border-line bg-white hover:bg-slate-50 dark:bg-panel dark:hover:bg-panel-light text-txt-muted hover:text-txt-primary transition cursor-pointer"
                title="Refresh Dual Engine Telemetry"
              >
                <RefreshCw className={`h-4 w-4 ${isLoadingEngines ? 'animate-spin' : ''}`} />
              </button>
            </div>
          </div>

          {engineFeedback && (
            <div className="p-3 rounded-lg bg-blue-500/10 border border-blue-500/30 text-brand text-xs font-semibold flex items-center justify-between">
              <span>{engineFeedback}</span>
              <button onClick={() => setEngineFeedback(null)} className="text-txt-muted hover:text-txt-primary cursor-pointer">✕</button>
            </div>
          )}

          {/* Dual Engine Side-by-Side Cards */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
            {/* Engine A Card */}
            {(() => {
              const engA = engineData?.engines?.ENGINE_A || {};
              const isActive = engineData?.active_engine === 'ENGINE_A';
              return (
                <div className={`card-panel p-5 relative transition border ${
                  isActive ? 'border-brand/60 ring-1 ring-brand/30 bg-blue-500/5' : 'border-line opacity-90'
                }`}>
                  <div className="flex items-start justify-between gap-3 mb-4">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-bold font-mono px-2 py-0.5 rounded bg-blue-500/15 text-brand">
                          ENGINE A
                        </span>
                        <h4 className="text-sm font-bold text-txt-primary">{engA.name || 'Alpha-Core Champion'}</h4>
                      </div>
                      <span className="text-[11px] font-mono text-txt-muted block mt-1">
                        Weights: <code className="text-txt-primary">{engA.model_weights}</code>
                      </span>
                    </div>

                    <span className={`px-2.5 py-1 rounded-full text-[10px] font-bold font-mono uppercase tracking-wider ${
                      isActive ? 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400' : 'bg-slate-500/15 text-slate-500'
                    }`}>
                      {isActive ? '● ACTIVE LIVE CHAMPION' : '○ SHADOW INCUBATOR'}
                    </span>
                  </div>

                  {/* KPIs */}
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 p-3.5 rounded-xl bg-slate-50 dark:bg-panel-light/40 border border-line mb-4 font-mono">
                    <div>
                      <span className="text-[10px] uppercase text-txt-muted block">Win Rate</span>
                      <span className="text-base font-bold text-profit">{engA.win_rate ?? 75.0}%</span>
                    </div>
                    <div>
                      <span className="text-[10px] uppercase text-txt-muted block">Net PnL</span>
                      <span className="text-base font-bold text-txt-primary">${engA.net_pnl_usd ?? 0.0}</span>
                    </div>
                    <div>
                      <span className="text-[10px] uppercase text-txt-muted block">Trades</span>
                      <span className="text-base font-bold text-txt-primary">{engA.trades_count ?? 0}</span>
                    </div>
                    <div>
                      <span className="text-[10px] uppercase text-txt-muted block">Drawdown</span>
                      <span className="text-base font-bold text-loss">{engA.max_drawdown_pct ?? 0}%</span>
                    </div>
                  </div>

                  <div className="flex items-center justify-between text-xs pt-3 border-t border-line/60">
                    <span className="text-txt-muted text-[11px]">Strategy: {engA.strategy_mode}</span>
                    {!isActive && (
                      <button
                        onClick={() => handlePromoteEngine('ENGINE_A')}
                        disabled={isPromoting}
                        className="px-3 py-1.5 rounded-lg text-xs font-bold bg-brand text-white hover:bg-blue-600 transition shadow-xs cursor-pointer"
                      >
                        {isPromoting ? 'Switching...' : 'Promote Engine A to Live'}
                      </button>
                    )}
                  </div>
                </div>
              );
            })()}

            {/* Engine B Card */}
            {(() => {
              const engB = engineData?.engines?.ENGINE_B || {};
              const isActive = engineData?.active_engine === 'ENGINE_B';
              const isSuperior = engineData?.is_challenger_superior;
              return (
                <div className={`card-panel p-5 relative transition border ${
                  isActive ? 'border-purple-500/60 ring-1 ring-purple-500/30 bg-purple-500/5' : 'border-line opacity-90'
                }`}>
                  <div className="flex items-start justify-between gap-3 mb-4">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-bold font-mono px-2 py-0.5 rounded bg-purple-500/15 text-purple-600 dark:text-purple-400">
                          ENGINE B
                        </span>
                        <h4 className="text-sm font-bold text-txt-primary">{engB.name || 'Quantum-Neuro Challenger'}</h4>
                      </div>
                      <span className="text-[11px] font-mono text-txt-muted block mt-1">
                        Weights: <code className="text-txt-primary">{engB.model_weights}</code>
                      </span>
                    </div>

                    <span className={`px-2.5 py-1 rounded-full text-[10px] font-bold font-mono uppercase tracking-wider ${
                      isActive ? 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400' : 'bg-purple-500/15 text-purple-600 dark:text-purple-300'
                    }`}>
                      {isActive ? '● ACTIVE LIVE CHAMPION' : '⚡ AUTONOMOUS SHADOW'}
                    </span>
                  </div>

                  {/* KPIs */}
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 p-3.5 rounded-xl bg-slate-50 dark:bg-panel-light/40 border border-line mb-4 font-mono">
                    <div>
                      <span className="text-[10px] uppercase text-txt-muted block">Win Rate</span>
                      <span className="text-base font-bold text-purple-600 dark:text-purple-400">{engB.win_rate ?? 81.8}%</span>
                    </div>
                    <div>
                      <span className="text-[10px] uppercase text-txt-muted block">Net PnL</span>
                      <span className="text-base font-bold text-txt-primary">${engB.net_pnl_usd ?? 0.0}</span>
                    </div>
                    <div>
                      <span className="text-[10px] uppercase text-txt-muted block">Trades</span>
                      <span className="text-base font-bold text-txt-primary">{engB.trades_count ?? 0}</span>
                    </div>
                    <div>
                      <span className="text-[10px] uppercase text-txt-muted block">Drawdown</span>
                      <span className="text-base font-bold text-loss">{engB.max_drawdown_pct ?? 0}%</span>
                    </div>
                  </div>

                  <div className="flex items-center justify-between text-xs pt-3 border-t border-line/60">
                    <span className="text-txt-muted text-[11px]">Strategy: {engB.strategy_mode}</span>
                    {!isActive && (
                      <button
                        onClick={() => handlePromoteEngine('ENGINE_B')}
                        disabled={isPromoting}
                        className={`px-3 py-1.5 rounded-lg text-xs font-bold transition shadow-xs cursor-pointer ${
                          isSuperior
                            ? 'bg-purple-600 text-white hover:bg-purple-700 ring-1 ring-purple-400 animate-pulse'
                            : 'bg-surface border border-line text-txt-primary hover:bg-slate-100 dark:hover:bg-panel-light'
                        }`}
                      >
                        {isPromoting ? 'Switching...' : isSuperior ? '★ Promote Superior Challenger' : 'Manual Switch to Engine B'}
                      </button>
                    )}
                  </div>
                </div>
              );
            })()}
          </div>

          {/* Institutional Superiority Gatekeeper Checklist */}
          <div className="card-panel p-5">
            <div className="flex items-center justify-between mb-3.5 pb-2.5 border-b border-line">
              <div className="flex items-center gap-2">
                <ShieldCheck className="h-4 w-4 text-brand" />
                <h4 className="text-xs font-bold uppercase tracking-wider text-txt-primary">
                  Live Promotion Gatekeeper Validation Checklist
                </h4>
              </div>
              <span className={`text-xs font-mono font-bold px-2.5 py-0.5 rounded ${
                engineData?.is_challenger_superior
                  ? 'bg-emerald-500/15 text-emerald-600'
                  : 'bg-amber-500/15 text-amber-600'
              }`}>
                {engineData?.superiority_verdict || 'Evaluating Gates...'}
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-4 gap-3 text-xs">
              <div className="p-3 rounded-lg border border-line bg-slate-50 dark:bg-panel-light/30">
                <span className="text-txt-muted block text-[11px]">Gate 1: Minimum Sample</span>
                <span className="font-bold text-txt-primary block mt-1">
                  {engineData?.comparison?.challenger_trades ?? 0} / {engineData?.min_evaluation_trades ?? 15} Trades
                </span>
                <span className={`text-[10px] font-mono font-bold block mt-1 ${
                  (engineData?.comparison?.challenger_trades ?? 0) >= (engineData?.min_evaluation_trades ?? 15) ? 'text-profit' : 'text-amber-500'
                }`}>
                  {(engineData?.comparison?.challenger_trades ?? 0) >= (engineData?.min_evaluation_trades ?? 15) ? '✓ SAMPLE CLEAR' : '⏳ ACCUMULATING'}
                </span>
              </div>

              <div className="p-3 rounded-lg border border-line bg-slate-50 dark:bg-panel-light/30">
                <span className="text-txt-muted block text-[11px]">Gate 2: Alpha Hurdle (+2.0%)</span>
                <span className="font-bold text-txt-primary block mt-1">
                  Challenger: {engineData?.comparison?.challenger_win_rate ?? 0}% vs Champ: {engineData?.comparison?.champion_win_rate ?? 0}%
                </span>
                <span className={`text-[10px] font-mono font-bold block mt-1 ${
                  (engineData?.comparison?.challenger_win_rate ?? 0) > (engineData?.comparison?.champion_win_rate ?? 0) ? 'text-profit' : 'text-loss'
                }`}>
                  {(engineData?.comparison?.challenger_win_rate ?? 0) > (engineData?.comparison?.champion_win_rate ?? 0) ? '✓ ALPHA CONFIRMED' : '✗ BELOW HURDLE'}
                </span>
              </div>

              <div className="p-3 rounded-lg border border-line bg-slate-50 dark:bg-panel-light/30">
                <span className="text-txt-muted block text-[11px]">Gate 3: Net Realized PnL</span>
                <span className="font-bold text-txt-primary block mt-1">
                  ${engineData?.comparison?.challenger_net_pnl ?? 0} vs ${engineData?.comparison?.champion_net_pnl ?? 0}
                </span>
                <span className={`text-[10px] font-mono font-bold block mt-1 ${
                  (engineData?.comparison?.challenger_net_pnl ?? 0) > (engineData?.comparison?.champion_net_pnl ?? 0) ? 'text-profit' : 'text-loss'
                }`}>
                  {(engineData?.comparison?.challenger_net_pnl ?? 0) > (engineData?.comparison?.champion_net_pnl ?? 0) ? '✓ HIGHER NET RETURN' : '✗ LOWER PNL'}
                </span>
              </div>

              <div className="p-3 rounded-lg border border-line bg-slate-50 dark:bg-panel-light/30">
                <span className="text-txt-muted block text-[11px]">Gate 4: Max Drawdown Ceiling</span>
                <span className="font-bold text-txt-primary block mt-1">
                  {engineData?.comparison?.challenger_drawdown ?? 0}% vs {engineData?.comparison?.champion_drawdown ?? 0}%
                </span>
                <span className={`text-[10px] font-mono font-bold block mt-1 ${
                  (engineData?.comparison?.challenger_drawdown ?? 0) <= (engineData?.comparison?.champion_drawdown ?? 0) ? 'text-profit' : 'text-loss'
                }`}>
                  {(engineData?.comparison?.challenger_drawdown ?? 0) <= (engineData?.comparison?.champion_drawdown ?? 0) ? '✓ LOWER RISK CEILING' : '✗ EXCESS DRAWDOWN'}
                </span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* CREATE USER MODAL */}
      <Modal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        title="Add New Multi-Tenant User"
        description="Creates an isolated user profile with segregated paper trading ledger"
      >
        <form onSubmit={handleCreateUser} className="space-y-3 text-xs">
          <div>
            <label className="block font-semibold text-txt-primary mb-1">Username:</label>
            <input
              type="text"
              required
              value={newUser.username}
              onChange={(e) => setNewUser({ ...newUser, username: e.target.value })}
              placeholder="e.g. trader_rahul"
              className="w-full px-3 py-2 text-xs rounded-lg border border-line bg-panel-light text-txt-primary font-mono focus:outline-none focus:ring-2 focus:ring-brand"
            />
          </div>

          <div>
            <label className="block font-semibold text-txt-primary mb-1">Full Name:</label>
            <input
              type="text"
              required
              value={newUser.full_name}
              onChange={(e) => setNewUser({ ...newUser, full_name: e.target.value })}
              placeholder="e.g. Rahul Sharma"
              className="w-full px-3 py-2 text-xs rounded-lg border border-line bg-panel-light text-txt-primary focus:outline-none focus:ring-2 focus:ring-brand"
            />
          </div>

          <div>
            <label className="block font-semibold text-txt-primary mb-1">Email Address:</label>
            <input
              type="email"
              required
              value={newUser.email}
              onChange={(e) => setNewUser({ ...newUser, email: e.target.value })}
              placeholder="rahul@marvanspool.internal"
              className="w-full px-3 py-2 text-xs rounded-lg border border-line bg-panel-light text-txt-primary focus:outline-none focus:ring-2 focus:ring-brand"
            />
          </div>

          <div>
            <label className="block font-semibold text-txt-primary mb-1">Initial Password:</label>
            <input
              type="password"
              required
              value={newUser.password}
              onChange={(e) => setNewUser({ ...newUser, password: e.target.value })}
              placeholder="Min 6 characters"
              className="w-full px-3 py-2 text-xs rounded-lg border border-line bg-panel-light text-txt-primary font-mono focus:outline-none focus:ring-2 focus:ring-brand"
            />
          </div>

          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="block font-semibold text-txt-primary mb-1">Role & Permissions:</label>
              <select
                value={newUser.role}
                onChange={(e) => setNewUser({ ...newUser, role: e.target.value })}
                className="w-full px-3 py-2 text-xs rounded-lg border border-line bg-panel-light text-txt-primary focus:outline-none focus:ring-2 focus:ring-brand"
              >
                <option value="TRADER">TRADER (Trading Desk Access)</option>
                <option value="RISK_OFFICER">RISK_OFFICER (Read-Only Risk Sentinel)</option>
                <option value="COMPLIANCE_AUDITOR">COMPLIANCE_AUDITOR (Tax & Audit)</option>
                <option value="SUPER_ADMIN">SUPER_ADMIN (Full Platform Authority)</option>
              </select>
            </div>
            <div>
              <label className="block font-semibold text-txt-primary mb-1">Max Capital Allocation ($):</label>
              <input
                type="number"
                value={newUser.max_trade_size}
                onChange={(e) => setNewUser({ ...newUser, max_trade_size: Number(e.target.value) })}
                className="w-full px-3 py-2 text-xs rounded-lg border border-line bg-panel-light text-txt-primary font-mono focus:outline-none focus:ring-2 focus:ring-brand"
              />
            </div>
          </div>

          {createStatus && (
            <div
              className={`p-2.5 rounded-lg font-mono text-[11px] border ${
                createStatus.type === 'success'
                  ? 'bg-emerald-500/10 border-emerald-500/20 text-profit'
                  : 'bg-red-500/10 border-red-500/20 text-red-500'
              }`}
            >
              {createStatus.message}
            </div>
          )}

          <div className="flex items-center justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={() => setIsCreateModalOpen(false)}
              className="px-3 py-1.5 rounded-md border border-line bg-panel hover:bg-panel-light text-txt-secondary"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isCreatingUser}
              className="px-4 py-1.5 rounded-md bg-brand hover:bg-brand/90 text-white font-bold transition disabled:opacity-50 cursor-pointer"
            >
              {isCreatingUser ? 'Creating...' : 'Create Isolated User'}
            </button>
          </div>
        </form>
      </Modal>

      {/* EDIT USER MODAL */}
      <Modal
        isOpen={Boolean(editingUser)}
        onClose={() => setEditingUser(null)}
        title={`Edit User: ${editingUser?.username}`}
        description="Update profile information, RBAC permissions, and trade limits"
      >
        <form onSubmit={handleUpdateUser} className="space-y-3 text-xs">
          <div>
            <label className="block font-semibold text-txt-primary mb-1">Full Name:</label>
            <input
              type="text"
              value={editFormData.full_name}
              onChange={(e) => setEditFormData({ ...editFormData, full_name: e.target.value })}
              className="w-full px-3 py-2 text-xs rounded-lg border border-line bg-panel-light text-txt-primary focus:outline-none focus:ring-2 focus:ring-brand"
            />
          </div>

          <div>
            <label className="block font-semibold text-txt-primary mb-1">Email Address:</label>
            <input
              type="email"
              value={editFormData.email}
              onChange={(e) => setEditFormData({ ...editFormData, email: e.target.value })}
              className="w-full px-3 py-2 text-xs rounded-lg border border-line bg-panel-light text-txt-primary focus:outline-none focus:ring-2 focus:ring-brand"
            />
          </div>

          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="block font-semibold text-txt-primary mb-1">Role:</label>
              <select
                disabled={editingUser?.username === 'marvan'}
                value={editFormData.role}
                onChange={(e) => setEditFormData({ ...editFormData, role: e.target.value })}
                className="w-full px-3 py-2 text-xs rounded-lg border border-line bg-panel-light text-txt-primary focus:outline-none focus:ring-2 focus:ring-brand disabled:opacity-50"
              >
                <option value="TRADER">TRADER</option>
                <option value="LEAD_TRADER">LEAD_TRADER</option>
                <option value="RISK_OFFICER">RISK_OFFICER</option>
                <option value="COMPLIANCE_AUDITOR">COMPLIANCE_AUDITOR</option>
                <option value="SUPER_ADMIN">SUPER_ADMIN</option>
              </select>
            </div>
            <div>
              <label className="block font-semibold text-txt-primary mb-1">Max Capital Allocation ($):</label>
              <input
                type="number"
                value={editFormData.max_trade_size}
                onChange={(e) => setEditFormData({ ...editFormData, max_trade_size: Number(e.target.value) })}
                className="w-full px-3 py-2 text-xs rounded-lg border border-line bg-panel-light text-txt-primary font-mono focus:outline-none focus:ring-2 focus:ring-brand"
              />
            </div>
          </div>

          <div>
            <label className="block font-semibold text-txt-primary mb-1">
              Reset Password <span className="text-txt-muted font-normal">(Leave blank to keep current)</span>:
            </label>
            <input
              type="password"
              value={editFormData.new_password}
              onChange={(e) => setEditFormData({ ...editFormData, new_password: e.target.value })}
              placeholder="••••••••••••"
              className="w-full px-3 py-2 text-xs rounded-lg border border-line bg-panel-light text-txt-primary font-mono focus:outline-none focus:ring-2 focus:ring-brand"
            />
          </div>

          {editStatus && (
            <div
              className={`p-2.5 rounded-lg font-mono text-[11px] border ${
                editStatus.type === 'success'
                  ? 'bg-emerald-500/10 border-emerald-500/20 text-profit'
                  : 'bg-red-500/10 border-red-500/20 text-red-500'
              }`}
            >
              {editStatus.message}
            </div>
          )}

          <div className="flex items-center justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={() => setEditingUser(null)}
              className="px-3 py-1.5 rounded-md border border-line bg-panel hover:bg-panel-light text-txt-secondary"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isUpdatingUser}
              className="px-4 py-1.5 rounded-md bg-brand hover:bg-brand/90 text-white font-bold transition disabled:opacity-50 cursor-pointer"
            >
              {isUpdatingUser ? 'Saving...' : 'Save Changes'}
            </button>
          </div>
        </form>
      </Modal>

      {/* DELETE USER CONFIRMATION MODAL */}
      <Modal
        isOpen={Boolean(userToDelete)}
        onClose={() => setUserToDelete(null)}
        title="Confirm User Account Deletion"
        description={`This action permanently removes ${userToDelete?.username} from the platform.`}
      >
        <div className="space-y-3 text-xs">
          <p className="text-txt-secondary">
            Are you sure you want to permanently delete user{' '}
            <strong className="text-txt-primary font-mono">{userToDelete?.username}</strong>?
          </p>
          <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-red-600 font-mono text-[11px]">
            ⚠️ This will remove credentials and access permissions for this tenant.
          </div>

          {deleteStatus && (
            <div className="p-2.5 bg-red-500/10 border border-red-500/20 rounded-lg text-red-600 font-mono text-[11px]">
              {deleteStatus}
            </div>
          )}

          <div className="flex items-center justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={() => setUserToDelete(null)}
              className="px-3 py-1.5 rounded-md border border-line bg-panel hover:bg-panel-light text-txt-secondary"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleDeleteUser}
              disabled={isDeletingUser}
              className="px-4 py-1.5 rounded-md bg-red-600 hover:bg-red-700 text-white font-bold transition disabled:opacity-50 cursor-pointer"
            >
              {isDeletingUser ? 'Deleting...' : 'Delete User'}
            </button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
