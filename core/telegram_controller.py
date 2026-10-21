"""
AEGIS-QUANT Interactive Telegram Bot Controller.
Handles two-way remote command execution via Telegram:
  /status    - System health, active broker, balance & PnL
  /paylink   - Generate an instant card/NFC/UPI deposit link (e.g. /paylink 1000 kotak)
  /bias      - Real-time pre-market global bias
  /positions - Active open positions summary
  /close_all - Emergency squareoff of all active trades
  /kill      - Hardware kill-switch engagement
"""

import os
import time
from typing import Dict, Any, Optional
from datetime import datetime, timezone, timedelta

IST_TZ = timezone(timedelta(hours=5, minutes=30))


class TelegramController:
    def __init__(self):
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID", "")

    def process_incoming_command(self, text: str, sender_chat_id: str) -> str:
        """Process an inbound text command and return Markdown response."""
        cmd_parts = text.strip().split()
        if not cmd_parts:
            return "Please provide a command. Type /help to see options."

        cmd = cmd_parts[0].lower()

        if cmd in ["/start", "/help"]:
            return (
                "🤖 *AEGIS-QUANT NEXT-LEVEL BOT CONTROLLER*\n\n"
                "Available commands:\n"
                "• `/status` — View real-time system & broker health\n"
                "• `/positions` — View open Indian & Crypto trades\n"
                "• `/bias` — Pre-market global sentiment & bias\n"
                "• `/paylink <amount> <broker>` — Generate instant deposit link\n"
                "• `/close_all` — Market close all open positions\n"
                "• `/kill` — Emergency Kill Switch activation\n"
            )

        elif cmd == "/status":
            try:
                from execution.broker_gateway_manager import broker_gateway_manager
                from core.daily_circuit_breaker import daily_circuit_breaker
                from execution.kotak_neo_broker import kotak_neo_broker

                kotak_stat = "🟢 ONLINE" if kotak_neo_broker._is_authenticated else "🟡 STANDBY"
                today_str = datetime.now(timezone.utc).astimezone(IST_TZ).strftime("%Y-%m-%d %H:%M:%S IST")

                return (
                    f"⚡ *AEGIS QUANT SYSTEM STATUS*\n"
                    f"━━━━━━━━━━━━━━━━━━━\n"
                    f"• *Kotak Neo (NSE):* {kotak_stat}\n"
                    f"• *Active Client UCC:* `{kotak_neo_broker.ucc or '16MT6'}`\n"
                    f"• *Live Capital:* ₹{float(kotak_neo_broker._live_cash):,.2f}\n"
                    f"• *Circuit Breaker:* {'🛑 LOCKED' if daily_circuit_breaker.is_circuit_open else '✅ HEALTHY'}\n"
                    f"• *Engine Time:* {today_str}\n"
                )
            except Exception as e:
                return f"⚠️ Error fetching status: {e}"

        elif cmd == "/bias":
            try:
                from core.pre_market_engine import pre_market_engine
                b = pre_market_engine.evaluate_global_bias()
                return (
                    f"🌐 *PRE-MARKET GLOBAL BIAS REPORT*\n"
                    f"━━━━━━━━━━━━━━━━━━━\n"
                    f"• *Verdict:* *{b['bias_verdict']}*\n"
                    f"• *Macro Score:* {b['macro_sentiment_score']} / 100\n"
                    f"• *Directional Filter:* `{b['directional_filter']}`\n"
                    f"• *Strategy Recommendation:*\n_{b['recommended_strategy']}_\n"
                    f"• *Evaluated At:* {b['computed_at']}"
                )
            except Exception as e:
                return f"⚠️ Bias calculation error: {e}"

        elif cmd == "/paylink":
            try:
                amt = float(cmd_parts[1]) if len(cmd_parts) > 1 else 1000.0
                target = cmd_parts[2] if len(cmd_parts) > 2 else "kotak"
                from execution.payment_link_gateway import payment_link_gateway
                res = payment_link_gateway.create_payment_link(
                    amount=amt,
                    currency="INR" if "kotak" in target.lower() or "upstox" in target.lower() else "USD",
                    target_broker=target,
                    title="Bot Capital Top-Up",
                )
                if res.get("status") == "SUCCESS":
                    return (
                        f"💳 *INSTANT PAYMENT LINK GENERATED*\n"
                        f"━━━━━━━━━━━━━━━━━━━\n"
                        f"• *Amount:* {res['currency']} {res['amount']:,.2f}\n"
                        f"• *Target Broker:* {res['target_broker_name']}\n"
                        f"• *Payment Methods:* Cards, Apple Pay, Google Pay, NFC, UPI, Binance Pay\n\n"
                        f"🔗 *Pay Online:* {res['checkout_url']}\n\n"
                        f"_Tap link above to complete instant deposit!_"
                    )
                return f"❌ Failed: {res.get('message')}"
            except Exception as e:
                return f"⚠️ Usage: `/paylink <amount> <broker>` (e.g. `/paylink 1000 kotak`)"

        elif cmd == "/positions":
            try:
                from execution.paper_broker import paper_broker
                pos_list = list(paper_broker.positions.values())
                if not pos_list:
                    return "ℹ️ *No open positions at this moment.* Market is clear."
                
                txt = f"📊 *ACTIVE POSITIONS ({len(pos_list)} Open)*\n━━━━━━━━━━━━━━━━━━━\n"
                for p in pos_list:
                    txt += f"• *{p.get('symbol')}* ({p.get('side')}): Qty {p.get('quantity', 1)} @ ₹{float(p.get('entry_price', 0)):,.2f} | PnL: ₹{float(p.get('unrealized_pnl', 0)):+,.2f}\n"
                return txt
            except Exception as e:
                return f"⚠️ Error fetching positions: {e}"

        elif cmd == "/close_all":
            try:
                from execution.paper_broker import paper_broker
                from execution.kotak_neo_broker import kotak_neo_broker
                count = len(paper_broker.positions)
                for sym, pos in list(paper_broker.positions.items()):
                    if kotak_neo_broker._is_authenticated:
                        kotak_neo_broker.close_position(sym, quantity=float(pos.get("quantity", 1)))
                    paper_broker.close_position(sym, exit_price=float(pos.get("current_price", 0)), reason="TELEGRAM_REMOTE_CLOSE_ALL")
                return f"🚨 *Emergency Liquidate Executed:* Closed {count} positions across all venues."
            except Exception as e:
                return f"⚠️ Liquidation error: {e}"

        return "Command not recognized. Type /help for options."


# Global Singleton
telegram_controller = TelegramController()
