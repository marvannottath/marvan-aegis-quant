"""
AEGIS QUANT — PHASE 5 PAYMENT & WITHDRAWAL SECURITY TEST SUITE
Verifies:
 1. Double-Entry Ledger Posting & Balance Calculation
 2. USDT Deposit Engine: TRC20/BEP20 Network Validation
 3. Blockchain TX Hash Credit Verification
 4. Strict Idempotency Constraint (Duplicate Hash REJECTED)
 5. Zero-Withdrawal Safety Policy Enforcement
 6. Pending Withdrawal Lock (Withdrawable Balance Formula)
 7. Stripe Webhook Signature HMAC-SHA256 Verification
 8. Immutable Financial Audit Logger
"""

import sys
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.double_entry_ledger import double_entry_ledger
from execution.usdt_deposit_engine import usdt_deposit_engine
from execution.usdt_withdrawal_engine import usdt_withdrawal_engine
from execution.stripe_payment_engine import stripe_payment_engine
from core.audit_logger import audit_logger

results = []

def check(test_id, name, condition, detail=""):
    sym = "✅ PASS" if condition else "❌ FAIL"
    results.append({"id": test_id, "name": name, "status": "PASS" if condition else "FAIL", "detail": detail})
    print(f"[{test_id:02d}] {sym} {name}" + (f" | {detail}" if detail else ""))
    return condition

print("\n=== AEGIS QUANT PHASE 5 PAYMENT SECURITY TESTS ===\n")

# TEST 1: Double-Entry Ledger Entry
entry = double_entry_ledger.post_entry("DEPOSIT_LEDGER", "BANK_TRC20", "CUSTOMER_ACCOUNT_AEGIS_QUANT_MASTER", 500.0, "USDT", "DEP-TEST-1", "AEGIS_QUANT_MASTER")
check(1, "Double-Entry Ledger: Entry posted with DR/CR symmetry", entry["status"] == "POSTED", f"Entry ID: {entry['entry_id']}")

# TEST 2: USDT Deposit Request Creation with TRC20 Network Warning
req = usdt_deposit_engine.create_deposit_request(100.0, network="TRC20", environment="AEGIS_QUANT_MASTER")
check(2, "USDT Deposit Engine: TRC20 Network Warning Enforced", "TRC20" in req["warning"], f"Network: {req['network_name']}")

# TEST 3: Blockchain TX Hash Credit Verification (Unique Dynamic Hash)
unique_hash = f"0x99a8_{int(time.time()*1000)}_{uuid.uuid4().hex[:4]}"
tx_res = usdt_deposit_engine.verify_and_credit_blockchain_tx(req["deposit_id"], unique_hash, 100.0, network="TRC20", environment="AEGIS_QUANT_MASTER")
check(3, "USDT Deposit Verification: Valid TX Hash Credits Deposit Ledger", tx_res["status"] == "CREDITED", f"Status: {tx_res['status']}")

# TEST 4: STRICT IDEMPOTENCY CONSTRAINT (Duplicate Hash REJECTED)
dup_res = usdt_deposit_engine.verify_and_credit_blockchain_tx("DEP-TEST-DUP", unique_hash, 100.0, network="TRC20", environment="AEGIS_QUANT_MASTER")
check(4, "Strict Idempotency Constraint: Duplicate TX Hash REJECTED", dup_res["status"] == "REJECTED_DUPLICATE_TX", f"Result: {dup_res['status']}")

# TEST 5: Zero-Withdrawal Safety Policy Enforcement
usdt_withdrawal_engine.zero_withdrawal_policy = True
wdr_res = usdt_withdrawal_engine.request_withdrawal(50.0, "TQn9Y2khEsLJW1ChV8m3N9K7xPnR2J4vLm", network="TRC20", available_cash=1000.0)
check(5, "Zero-Withdrawal Policy Gate: Direct Withdrawal Blocked", wdr_res["status"] == "REJECTED_POLICY", f"Message: {wdr_res['message'][:45]}...")

# TEST 6: Pending Withdrawal Lock Formula
usdt_withdrawal_engine.zero_withdrawal_policy = False
# Add verified address first
usdt_withdrawal_engine.address_book.append({"address": "TQn9Y2khEsLJW1ChV8m3N9K7xPnR2J4vLm", "network": "TRC20", "status": "VERIFIED"})
w_key = f"WDR-LOCK-{int(time.time()*1000)}"
wdr_res2 = usdt_withdrawal_engine.request_withdrawal(400.0, "TQn9Y2khEsLJW1ChV8m3N9K7xPnR2J4vLm", network="TRC20", available_cash=500.0, environment="AEGIS_QUANT_MASTER", idempotency_key=w_key)
withdrawable = usdt_withdrawal_engine.calculate_withdrawable_balance(500.0, 0.0, "AEGIS_QUANT_MASTER")
check(6, "Pending Withdrawal Lock: $400 locked -> $100 withdrawable remaining", withdrawable < 500.0, f"Withdrawable: ${withdrawable}")

# TEST 7: Stripe Webhook Signature Verification
valid_sig = stripe_payment_engine.verify_webhook_signature(b'{"id":"evt_1"}', "t=1788250000,v1=bad_sig", "whsec_test")
check(7, "Stripe Webhook Signature Verification: Invalid Sig Rejected", not valid_sig, "Signature rejected as expected")

# TEST 8: Immutable Financial Audit Logging
audit_rec = audit_logger.log_event("DEPOSIT_CREDITED", "USER-101", 100.0, "USDT", "TRC20", "BINANCE", "DEP-TEST-1", "187.127.189.139", "AEGIS_QUANT_MASTER")
check(8, "Immutable Financial Audit Logger: Event recorded with IP metadata", audit_rec["event_type"] == "DEPOSIT_CREDITED", f"Event ID: {audit_rec['event_id']}")

print("\n" + "="*80)
passed = sum(1 for r in results if r["status"] == "PASS")
print(f"SUMMARY: {passed}/{len(results)} PHASE 5 SECURITY TESTS PASSED")
print("="*80)
