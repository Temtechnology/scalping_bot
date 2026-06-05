# modules/telegram_alerts.py
# Sends instant alerts to your Telegram when bot acts

import requests
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, SYMBOL


def send_message(msg):
    """Send any text message to your Telegram."""
    url  = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "HTML"}
    try:
        requests.post(url, data=data, timeout=10)
    except Exception as e:
        print(f"⚠️ Telegram error: {e}")


def alert_signal(signal, details):
    """Alert when a new BUY or SELL signal fires."""
    emoji = "🟢 BUY SIGNAL" if signal == "BUY" else "🔴 SELL SIGNAL"
    msg = (
        f"<b>{emoji} — {SYMBOL}</b>\n\n"
        f"💰 Price  : {details['close']}\n"
        f"📊 RSI    : {details['rsi']}\n"
        f"📈 VWAP   : {details['vwap']}\n"
        f"⚡ ATR    : {details['atr']}\n"
    )
    send_message(msg)


def alert_trade_opened(signal, levels):
    """Alert when a trade is placed."""
    emoji = "🟢 LONG" if signal == "BUY" else "🔴 SHORT"
    msg = (
        f"<b>✅ TRADE OPENED — {emoji}</b>\n\n"
        f"📐 Setup   : {levels.get('setup', '')}\n"
        f"🕯 Pattern : {levels.get('pattern', '')}\n"
        f"📊 Level   : {levels.get('level_type', '')} @ {levels.get('level', '')}\n\n"
        f"📌 Entry   : {levels['entry']}\n"
        f"🛑 SL      : {levels['stop_loss']}\n"
        f"🎯 TP      : {levels['take_profit']}\n"
        f"⚖️ R:R     : {levels['rr_ratio']}\n"
        f"💵 Risk    : ${levels['dollar_risk']}\n"
        f"💰 Reward  : ${levels['dollar_reward']}\n"
        f"📦 Lots    : {levels['lot_size']}"
    )
    send_message(msg)

def alert_daily_limit():
    """Alert when daily loss limit is hit."""
    msg = (
        f"🛑 <b>DAILY LOSS LIMIT HIT</b>\n\n"
        f"Bot has shut down to protect your account.\n"
        f"Max 5% daily loss reached on {SYMBOL}."
    )
    send_message(msg)


def alert_bot_started(balance):
    """Alert when bot starts up."""
    msg = (
        f"🤖 <b>Scalping Bot STARTED</b>\n\n"
        f"📊 Symbol  : {SYMBOL}\n"
        f"💰 Balance : ${balance:,.2f}\n"
        f"📝 Mode    : Paper Trading"
    )
    send_message(msg)


def alert_bot_stopped(pnl):
    """Alert when bot shuts down."""
    emoji = "📈" if pnl >= 0 else "📉"
    msg = (
        f"⛔ <b>Bot STOPPED</b>\n\n"
        f"{emoji} Session P&L: ${pnl:+,.2f}"
    )
    send_message(msg)


# ── TEST ─────────────────────────────────────────────
if __name__ == '__main__':
    print("Sending test message to Telegram...")
    send_message(
        "🤖 <b>Scalping Bot Connected!</b>\n\n"
        "✅ Telegram alerts are working.\n"
        "You will receive alerts for every signal and trade."
    )
    print("✅ Done! Check your Telegram.")