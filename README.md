# Aegis-Quant: Autonomous Self-Learning Quantitative Trading System

Aegis-Quant is a state-of-the-art, autonomous, self-learning algorithmic trading system written in Python. It features PyTorch Reinforcement Learning, Daily Sentiment Strategy Synchronization, Self-Diagnostics with AI Trade Forensics, Military-Grade Fernet AES-256 Key Vault, Risk Management Circuit Breakers, $100,000 Virtual Paper Trading Capital, Forex & Equity multi-asset coverage, and a Cyberpunk Web Dashboard.

---

## Key Modules & Features

1. **Auto-Learning Engine (Reinforcement Learning)**: Deep Q-Network (DQN) with PyTorch, Experience Replay, Target Network, and dynamic state normalization across Forex pairs (`EURUSD=X`, `GBPUSD=X`) and Equities (`XLK`, `XLF`).
2. **Daily Strategy Sync**: Cron/Scheduler module fetching market sentiment (News API / NLP) and aligning strategy weights with macro human market behavior.
3. **Self-Diagnostic & AI Trade Forensics**: Auto-intercepts exceptions and performs root-cause attribution for closed trades (explaining **WHY** a trade gained or lost money) along with RL self-learning feedback logs.
4. **Military-Grade Security**: Fernet AES-256 Key Vault for secret encryption/decryption, zero hardcoded credentials, secret masking in log outputs.
5. **Paper Trading & Risk Management**: Starts with **$100,000 Virtual Capital**, implements Half-Kelly position sizing, Stop-Loss, Take-Profit, and an 8% Max Drawdown Circuit Breaker.
6. **Real-time Web Dashboard**: Built with FastAPI, HTML5, Tailwind CSS, and Chart.js featuring the **AI Trade Forensics & Self-Learning Feed**.

---

## Project Structure

```
quantum_trading_system/
├── config/
│   ├── __init__.py
│   ├── security.py       # Fernet AES-256 Secret Vault & Secret Masking
│   └── settings.py       # Global configs ($100k capital, Forex pairs, Risk limits)
├── core/
│   ├── __init__.py
│   ├── data_loader.py    # Multi-asset data pipeline & technical indicators (RSI, MACD)
│   ├── risk_engine.py    # Kelly Sizing, Stop-Loss, Max Drawdown Circuit Breaker
│   └── diagnostics.py    # Self-Diagnostic & AI Trade Forensics Attribution Engine
├── models/
│   ├── __init__.py
│   ├── rl_environment.py # Custom Gym multi-asset trading environment
│   └── rl_agent.py       # PyTorch DQN Reinforcement Learning Agent
├── sync/
│   ├── __init__.py
│   ├── sentiment_analyzer.py # NLP Sentiment Analyzer for News & Social feeds
│   └── daily_sync.py     # Cron Strategy Sync module
├── execution/
│   ├── __init__.py
│   └── paper_broker.py   # Paper Trading Broker Simulator ($100k Virtual Balance)
├── backtest/
│   ├── __init__.py
│   └── backtest_engine.py # Vectorized Backtester (Sharpe, Drawdown, Win Rate)
├── dashboard/
│   ├── __init__.py
│   ├── app.py            # FastAPI Server
│   └── templates/
│       └── index.html    # Cyberpunk Web Dashboard UI
├── main.py               # Master CLI Launcher
├── requirements.txt      # Python Dependencies
└── README.md             # Documentation
```

---

## Step-by-Step Setup Instructions

### 1. Prerequisite
Ensure Python 3.9+ is installed on your system.

### 2. Navigate to Project Directory & Create Virtual Environment
```bash
cd /Users/marvan/.gemini/antigravity/scratch/quantum_trading_system
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

---

## How to Run the System

### 1. Launch Live System (Paper Trading + Web Dashboard)
```bash
python main.py --mode run
```
Then open your web browser at:
`http://127.0.0.1:8000`

### 2. Run Strategy Backtest (Forex EUR/USD or Stocks)
```bash
python main.py --mode backtest --ticker EURUSD=X
```

### 3. Encrypt Sensitive API Keys (Optional)
```bash
python main.py --mode encrypt-key
```

---

## Security Best Practices
- Never check raw API secrets into version control.
- All secrets loaded via `config.security.vault` are decrypted in memory only.
- System log files automatically redact sensitive tokens.
