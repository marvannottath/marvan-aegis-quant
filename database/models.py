"""
AEGIS-QUANT Unified Database Models.
Defines transactional schemas for:
  - Users, Accounts, Wallets (10 buckets)
  - Double-Entry Accounting Ledger
  - Orders, Fills, Positions, Trade History
  - Profit Sweeps & Reserve Vault
  - News Intelligence & High Impact News Lock Events
  - Risk Decisions & 100-Shield Audit Events
  - Backtests & Execution Telemetry
  - API & Security Configurations
"""

import os
import json
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy import (
    create_engine, Column, Integer, Float, String, Boolean, DateTime, Text, ForeignKey, JSON
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

IST_TZ = timezone(timedelta(hours=5, minutes=30))
Base = declarative_base()

def get_now_ist() -> str:
    return datetime.now(timezone.utc).astimezone(IST_TZ).strftime("%Y-%m-%d %H:%M:%S IST")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(64), unique=True, nullable=False, index=True)
    username = Column(String(64), unique=True, nullable=False)
    email = Column(String(128), unique=True, nullable=False)
    password_hash = Column(String(256), nullable=False)
    mfa_enabled = Column(Boolean, default=False)
    mfa_secret = Column(String(128), nullable=True)
    role = Column(String(32), default="TRADER")
    is_active = Column(Boolean, default=True)
    created_at = Column(String(32), default=get_now_ist)

    accounts = relationship("Account", back_populates="user", cascade="all, delete-orphan")


class Account(Base):
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(String(64), unique=True, nullable=False, index=True)
    user_id = Column(String(64), ForeignKey("users.user_id"), nullable=False)
    environment = Column(String(32), nullable=False, default="PAPER")  # PAPER, DEMO, TESTNET, LIVE
    account_name = Column(String(128), nullable=False)
    initial_capital = Column(Float, default=100000.0)
    virtual_cash = Column(Float, default=100000.0)
    equity = Column(Float, default=100000.0)
    ai_trading_active = Column(Boolean, default=True)
    created_at = Column(String(32), default=get_now_ist)

    user = relationship("User", back_populates="accounts")
    wallets = relationship("Wallet", back_populates="account", cascade="all, delete-orphan")
    orders = relationship("Order", back_populates="account", cascade="all, delete-orphan")
    positions = relationship("Position", back_populates="account", cascade="all, delete-orphan")


class Wallet(Base):
    __tablename__ = "wallets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    wallet_id = Column(String(64), unique=True, nullable=False, index=True)
    account_id = Column(String(64), ForeignKey("accounts.account_id"), nullable=False)
    asset = Column(String(16), default="USDT")
    total_balance = Column(Float, default=100000.0)
    available_balance = Column(Float, default=100000.0)
    trading_balance = Column(Float, default=100000.0)
    used_margin = Column(Float, default=0.0)
    unrealized_pnl = Column(Float, default=0.0)
    realized_pnl = Column(Float, default=0.0)
    fees_paid = Column(Float, default=0.0)
    locked_balance = Column(Float, default=0.0)
    withdrawable_balance = Column(Float, default=100000.0)
    profit_vault_balance = Column(Float, default=0.0)
    updated_at = Column(String(32), default=get_now_ist)

    account = relationship("Account", back_populates="wallets")


class LedgerEntry(Base):
    __tablename__ = "ledger_entries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    entry_id = Column(String(64), unique=True, nullable=False, index=True)
    timestamp = Column(String(32), default=get_now_ist)
    ledger_type = Column(String(64), nullable=False)
    debit_account = Column(String(64), nullable=False)
    credit_account = Column(String(64), nullable=False)
    amount = Column(Float, nullable=False)
    asset = Column(String(16), default="USDT")
    reference_id = Column(String(128), nullable=False)
    environment = Column(String(32), default="PAPER")
    notes = Column(Text, nullable=True)


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(String(64), unique=True, nullable=False, index=True)
    account_id = Column(String(64), ForeignKey("accounts.account_id"), nullable=False)
    environment = Column(String(32), default="PAPER")
    symbol = Column(String(32), nullable=False)
    side = Column(String(16), nullable=False)  # BUY, SELL
    order_type = Column(String(32), default="MARKET")
    quantity = Column(Float, nullable=False)
    price = Column(Float, default=0.0)
    status = Column(String(32), default="CREATED")
    executed_qty = Column(Float, default=0.0)
    avg_fill_price = Column(Float, default=0.0)
    client_order_id = Column(String(128), nullable=True)
    exchange_order_id = Column(String(128), nullable=True)
    created_at = Column(String(32), default=get_now_ist)
    updated_at = Column(String(32), default=get_now_ist)

    account = relationship("Account", back_populates="orders")


class Position(Base):
    __tablename__ = "positions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    trade_id = Column(String(64), unique=True, nullable=False, index=True)
    account_id = Column(String(64), ForeignKey("accounts.account_id"), nullable=False)
    environment = Column(String(32), default="PAPER")
    asset = Column(String(32), nullable=False)
    side = Column(String(16), nullable=False)
    units = Column(Float, nullable=False)
    entry_price = Column(Float, nullable=False)
    last_price = Column(Float, nullable=False)
    capital_allocated = Column(Float, nullable=False)
    leverage = Column(Float, default=10.0)
    unrealized_pnl = Column(Float, default=0.0)
    opened_at = Column(String(32), default=get_now_ist)
    is_active = Column(Boolean, default=True)

    account = relationship("Account", back_populates="positions")


class ProfitSweep(Base):
    __tablename__ = "profit_sweeps"

    id = Column(Integer, primary_key=True, autoincrement=True)
    transaction_id = Column(String(64), unique=True, nullable=False, index=True)
    environment = Column(String(32), default="PAPER")
    timestamp = Column(String(32), default=get_now_ist)
    source_trade_id = Column(String(64), nullable=True)
    asset = Column(String(32), nullable=False)
    realized_profit = Column(Float, nullable=False)
    sweep_amount = Column(Float, nullable=False)
    resulting_vault_balance = Column(Float, nullable=False)
    exit_reason = Column(String(128), default="PROFIT_SWEEP")
    status = Column(String(32), default="CONFIRMED")


class NewsIntelligenceEvent(Base):
    __tablename__ = "news_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(String(64), unique=True, nullable=False, index=True)
    source_id = Column(String(64), nullable=False)  # TELEGRAM, REUTERS, BLOOMBERG
    timestamp = Column(String(32), default=get_now_ist)
    headline = Column(Text, nullable=False)
    raw_content = Column(Text, nullable=True)
    affected_symbol = Column(String(32), nullable=False)
    sentiment_score = Column(Float, default=0.0)
    impact_score = Column(Float, default=0.0)
    confidence = Column(Float, default=0.0)
    lock_decision = Column(String(32), default="PASS")  # PASS, BLOCK, REDUCE_RISK, CLOSE_ONLY, COOLING_DOWN
    reason = Column(Text, nullable=True)


class RiskAuditCheck(Base):
    __tablename__ = "risk_audit_checks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    check_id = Column(String(64), unique=True, nullable=False, index=True)
    timestamp = Column(String(32), default=get_now_ist)
    environment = Column(String(32), default="PAPER")
    symbol = Column(String(32), nullable=False)
    passed_count = Column(Integer, nullable=False)
    total_checks = Column(Integer, default=100)
    status = Column(String(32), nullable=False)  # PASSED, REJECTED
    rejection_reasons = Column(JSON, nullable=True)
