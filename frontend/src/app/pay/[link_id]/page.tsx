'use client';

import React, { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import {
  CreditCard,
  QrCode,
  Smartphone,
  ShieldCheck,
  CheckCircle2,
  AlertCircle,
  Building2,
  Lock,
  ArrowRight,
  ExternalLink,
  Copy,
  RefreshCw,
} from 'lucide-react';

export default function CheckoutPage() {
  const params = useParams();
  const router = useRouter();
  const linkId = params?.link_id as string;

  const [linkData, setLinkData] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedMethod, setSelectedMethod] = useState<'card' | 'apple_google' | 'upi' | 'crypto'>('card');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [paymentSuccess, setPaymentSuccess] = useState<any>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Form inputs
  const [cardNumber, setCardNumber] = useState('4242 •••• •••• 4242');
  const [cardExpiry, setCardExpiry] = useState('12/28');
  const [cardCvc, setCardCvc] = useState('888');
  const [cardHolder, setCardHolder] = useState('Marvan Trader');
  const [upiRef, setUpiRef] = useState('');
  const [cryptoTx, setCryptoTx] = useState('');

  useEffect(() => {
    if (!linkId) return;
    const fetchLink = async () => {
      try {
        setIsLoading(true);
        const res = await fetch(`/api/pay/links`);
        if (res.ok) {
          const data = await res.json();
          const found = (data.links || []).find((l: any) => l.link_id === linkId);
          if (found) {
            setLinkData(found);
            if (found.status === 'PAID') {
              setPaymentSuccess({ message: 'This payment link has already been settled and credited to the broker.' });
            }
          } else {
            // Fallback mock representation for direct view
            setLinkData({
              link_id: linkId,
              amount: 1000,
              currency: 'INR',
              target_broker_name: 'Kotak Neo (Kotak Securities)',
              title: 'Aegis Quant Bot Capital Deposit',
            });
          }
        }
      } catch (e) {
        console.error('Error fetching link', e);
      } finally {
        setIsLoading(false);
      }
    };
    fetchLink();
  }, [linkId]);

  const handleConfirmPayment = async () => {
    setIsSubmitting(true);
    setErrorMessage(null);

    let ref = `CARD-${Math.random().toString(36).substring(2, 9).toUpperCase()}`;
    if (selectedMethod === 'upi') {
      ref = upiRef.trim() || `UPI-${Math.random().toString(36).substring(2, 9).toUpperCase()}`;
    } else if (selectedMethod === 'crypto') {
      ref = cryptoTx.trim() || `TX-${Math.random().toString(36).substring(2, 9).toUpperCase()}`;
    }

    try {
      const res = await fetch(`/api/pay/confirm/${linkId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          method: selectedMethod.toUpperCase(),
          payment_reference: ref,
          notes: 'Processed via Aegis Quant Universal Hosted Checkout',
        }),
      });

      const data = await res.json();
      if (res.ok && data.status === 'SUCCESS') {
        setPaymentSuccess(data);
      } else {
        setErrorMessage(data.message || 'Payment confirmation failed.');
      }
    } catch (e: any) {
      setErrorMessage(e.message || 'Network error confirming payment');
    } finally {
      setIsSubmitting(false);
    }
  };

  const curr = linkData?.currency === 'INR' ? '₹' : '$';

  if (isLoading) {
    return (
      <div className="min-h-screen bg-[#07090e] text-slate-100 flex items-center justify-center">
        <div className="flex items-center gap-3 text-sm font-semibold text-slate-400">
          <RefreshCw className="h-5 w-5 animate-spin text-brand" />
          <span>Loading secure checkout session...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#07090e] text-slate-100 flex flex-col justify-between selection:bg-brand selection:text-white">
      {/* Top Header */}
      <header className="border-b border-slate-800/80 bg-[#0c1017]/90 backdrop-blur px-4 py-3 sticky top-0 z-50">
        <div className="max-w-3xl mx-auto flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-brand to-emerald-500 flex items-center justify-center text-white font-black text-xs shadow-md">
              AQ
            </div>
            <div>
              <div className="text-xs font-black tracking-tight text-white flex items-center gap-1.5">
                AEGIS-QUANT
                <span className="text-[9px] uppercase tracking-widest px-1.5 py-0.2 rounded bg-emerald-500/20 text-emerald-400 font-bold border border-emerald-500/30">
                  SECURE GATEWAY
                </span>
              </div>
              <div className="text-[10px] text-slate-400 font-mono">End-to-End Encrypted Broker Custody</div>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
              256-BIT SSL SECURE
            </span>
          </div>
        </div>
      </header>

      {/* Main Container */}
      <main className="max-w-xl w-full mx-auto p-4 md:py-8 flex-1">
        <div className="bg-[#0f141e] border border-slate-800 rounded-3xl p-6 md:p-8 shadow-2xl relative overflow-hidden">
          {/* Amount Badge */}
          <div className="bg-[#141b28] border border-slate-700/60 rounded-2xl p-5 mb-6 text-center">
            <div className="text-xs uppercase tracking-wider font-bold text-slate-400 mb-1">Total Deposit Amount</div>
            <div className="text-4xl md:text-5xl font-black text-white font-mono tracking-tight my-1">
              {curr}{linkData?.amount?.toFixed(2) || '1,000.00'}
            </div>
            <div className="inline-flex items-center gap-1.5 text-xs font-semibold px-3 py-1 rounded-full bg-slate-800 text-slate-300 border border-slate-700 mt-2">
              <Building2 className="h-3.5 w-3.5 text-emerald-400" />
              <span>Target Broker Destination:</span>
              <strong className="text-white">{linkData?.target_broker_name || 'Kotak Neo Live Pool'}</strong>
            </div>
          </div>

          {paymentSuccess ? (
            <div className="space-y-4 py-4 text-center">
              <div className="w-16 h-16 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 flex items-center justify-center mx-auto">
                <CheckCircle2 className="h-8 w-8" />
              </div>
              <h3 className="text-lg font-bold text-white">Payment Confirmed & Capital Allocated!</h3>
              <p className="text-xs text-slate-300 leading-relaxed max-w-sm mx-auto">
                {paymentSuccess.message || 'Your deposit has been verified via the double-entry ledger. Trading margin is now active in your pool.'}
              </p>
              <div className="p-3 bg-slate-900 border border-slate-800 rounded-xl text-left text-xs space-y-1 font-mono">
                <div className="text-slate-400">Transaction ID: <span className="text-white font-bold">{linkId}</span></div>
                <div className="text-slate-400">Target Broker: <span className="text-emerald-400 font-bold">{linkData?.target_broker_name || 'Kotak Neo'}</span></div>
                <div className="text-slate-400">Ledger Status: <span className="text-emerald-400 font-bold">SETTLED & ACTIVE</span></div>
              </div>

              <div className="pt-2">
                <button
                  onClick={() => router.push('/deposit')}
                  className="w-full py-3 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs uppercase tracking-wider transition cursor-pointer"
                >
                  Return to Dashboard & Ledger
                </button>
              </div>
            </div>
          ) : (
            <div className="space-y-5">
              {/* Method Selector Tabs */}
              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-400 mb-2">
                  Select Payment Method
                </label>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                  <button
                    type="button"
                    onClick={() => setSelectedMethod('card')}
                    className={`p-3 rounded-xl border text-xs font-bold flex flex-col items-center gap-1.5 transition cursor-pointer ${
                      selectedMethod === 'card'
                        ? 'bg-brand/20 border-brand text-brand'
                        : 'bg-slate-800/40 border-slate-700 text-slate-400 hover:text-white'
                    }`}
                  >
                    <CreditCard className="h-5 w-5" />
                    <span>Card / Debit</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => setSelectedMethod('apple_google')}
                    className={`p-3 rounded-xl border text-xs font-bold flex flex-col items-center gap-1.5 transition cursor-pointer ${
                      selectedMethod === 'apple_google'
                        ? 'bg-brand/20 border-brand text-brand'
                        : 'bg-slate-800/40 border-slate-700 text-slate-400 hover:text-white'
                    }`}
                  >
                    <Smartphone className="h-5 w-5" />
                    <span>Apple / GPay</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => setSelectedMethod('upi')}
                    className={`p-3 rounded-xl border text-xs font-bold flex flex-col items-center gap-1.5 transition cursor-pointer ${
                      selectedMethod === 'upi'
                        ? 'bg-emerald-500/20 border-emerald-500 text-emerald-400'
                        : 'bg-slate-800/40 border-slate-700 text-slate-400 hover:text-white'
                    }`}
                  >
                    <QrCode className="h-5 w-5" />
                    <span>Instant UPI</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => setSelectedMethod('crypto')}
                    className={`p-3 rounded-xl border text-xs font-bold flex flex-col items-center gap-1.5 transition cursor-pointer ${
                      selectedMethod === 'crypto'
                        ? 'bg-amber-500/20 border-amber-500 text-amber-400'
                        : 'bg-slate-800/40 border-slate-700 text-slate-400 hover:text-white'
                    }`}
                  >
                    <Lock className="h-5 w-5" />
                    <span>Binance Pay</span>
                  </button>
                </div>
              </div>

              {/* Method Forms */}
              {selectedMethod === 'card' && (
                <div className="space-y-3 bg-[#121824] p-4 rounded-2xl border border-slate-700/60">
                  <div className="flex items-center justify-between text-xs text-slate-400 mb-1">
                    <span>Card Details</span>
                    <span className="text-[10px] text-emerald-400 font-mono">Sandbox Test Active</span>
                  </div>
                  <div>
                    <input
                      type="text"
                      value={cardNumber}
                      onChange={(e) => setCardNumber(e.target.value)}
                      className="w-full bg-[#0a0e17] border border-slate-700 rounded-lg px-3 py-2 text-xs font-mono text-white focus:outline-none focus:border-brand"
                      placeholder="Card number"
                    />
                  </div>
                  <div className="grid grid-cols-2 gap-2">
                    <input
                      type="text"
                      value={cardExpiry}
                      onChange={(e) => setCardExpiry(e.target.value)}
                      className="w-full bg-[#0a0e17] border border-slate-700 rounded-lg px-3 py-2 text-xs font-mono text-white focus:outline-none focus:border-brand"
                      placeholder="MM/YY"
                    />
                    <input
                      type="text"
                      value={cardCvc}
                      onChange={(e) => setCardCvc(e.target.value)}
                      className="w-full bg-[#0a0e17] border border-slate-700 rounded-lg px-3 py-2 text-xs font-mono text-white focus:outline-none focus:border-brand"
                      placeholder="CVC"
                    />
                  </div>
                  <div>
                    <input
                      type="text"
                      value={cardHolder}
                      onChange={(e) => setCardHolder(e.target.value)}
                      className="w-full bg-[#0a0e17] border border-slate-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-brand"
                      placeholder="Cardholder Name"
                    />
                  </div>
                </div>
              )}

              {selectedMethod === 'apple_google' && (
                <div className="bg-[#121824] p-5 rounded-2xl border border-slate-700/60 text-center space-y-3">
                  <div className="text-xs text-slate-300">
                    Pay securely using Apple Pay, Google Pay, or Contactless NFC Tap.
                  </div>
                  <div className="p-3 bg-black/60 rounded-xl border border-slate-700 text-xs font-semibold text-white flex items-center justify-center gap-2">
                    <Smartphone className="h-4 w-4 text-brand" />
                    <span>1-Tap Biometric Authentication Ready</span>
                  </div>
                </div>
              )}

              {selectedMethod === 'upi' && (
                <div className="bg-[#121824] p-4 rounded-2xl border border-slate-700/60 space-y-3 text-center">
                  <div className="text-xs font-semibold text-slate-300">Scan UPI QR with GPay / PhonePe / Paytm</div>
                  <div className="w-36 h-36 bg-white p-2 rounded-xl mx-auto flex items-center justify-center shadow-lg">
                    <QrCode className="h-32 w-32 text-black" />
                  </div>
                  <div className="text-[11px] font-mono text-slate-400">
                    VPA: <strong className="text-emerald-400">marvan.aegis@kotak</strong>
                  </div>
                  <div>
                    <input
                      type="text"
                      value={upiRef}
                      onChange={(e) => setUpiRef(e.target.value)}
                      className="w-full bg-[#0a0e17] border border-slate-700 rounded-lg px-3 py-2 text-xs font-mono text-white focus:outline-none focus:border-emerald-500 text-center"
                      placeholder="Enter 12-digit UPI UTR (optional for auto-verify)"
                    />
                  </div>
                </div>
              )}

              {selectedMethod === 'crypto' && (
                <div className="bg-[#121824] p-4 rounded-2xl border border-slate-700/60 space-y-3">
                  <div className="text-xs font-semibold text-slate-300">Direct Binance Pay & Web3 Deposit</div>
                  <div className="p-2.5 bg-[#0a0e17] rounded-lg border border-slate-700 text-[11px] font-mono text-slate-300 break-all select-all">
                    USDT (TRC20): <span className="text-amber-400">TYu98AegisQuantPoolBinance7721Live</span>
                  </div>
                  <div>
                    <input
                      type="text"
                      value={cryptoTx}
                      onChange={(e) => setCryptoTx(e.target.value)}
                      className="w-full bg-[#0a0e17] border border-slate-700 rounded-lg px-3 py-2 text-xs font-mono text-white focus:outline-none focus:border-amber-500"
                      placeholder="Binance Pay Order ID / TxHash"
                    />
                  </div>
                </div>
              )}

              {errorMessage && (
                <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-400 text-xs flex items-center gap-2">
                  <AlertCircle className="h-4 w-4 shrink-0" />
                  <span>{errorMessage}</span>
                </div>
              )}

              {/* Submit Button */}
              <button
                onClick={handleConfirmPayment}
                disabled={isSubmitting}
                className="w-full py-4 px-6 rounded-2xl bg-brand hover:bg-brand/90 text-white font-black text-sm uppercase tracking-wider flex items-center justify-center gap-2 shadow-lg transition cursor-pointer"
              >
                {isSubmitting ? (
                  <RefreshCw className="h-5 w-5 animate-spin" />
                ) : (
                  <Lock className="h-5 w-5" />
                )}
                <span>Confirm {curr}{linkData?.amount || '1,000'} Deposit</span>
              </button>
            </div>
          )}
        </div>
      </main>

      {/* Footer */}
      <footer className="py-4 border-t border-slate-800 text-center text-[11px] text-slate-500">
        Aegis Quant Institutional Architecture • 256-Bit SSL • Double-Entry Vault Reserve
      </footer>
    </div>
  );
}
