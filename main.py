# main.py — Price Action Bot with S&R + Candlestick Patterns

import MetaTrader5 as mt5
import time
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from modules.data_feed       import connect_mt5, fetch_candles, disconnect_mt5
from modules.signals         import get_signal, find_sr_levels
from modules.risk            import calculate_trade_levels, check_daily_loss_limit, print_trade_plan
from modules.executor        import place_trade, get_open_position, print_position_status
from modules.telegram_alerts import (alert_bot_started, alert_signal,
                                      alert_trade_opened, alert_daily_limit,
                                      alert_bot_stopped, send_message)
from config import SLEEP_SECONDS, PAPER_TRADING, SYMBOL


def print_header():
    mode = "📝 PAPER TRADING" if PAPER_TRADING else "💰 LIVE TRADING"
    print("=" * 55)
    print(f"   PRICE ACTION BOT v2 — {SYMBOL}")
    print(f"   Mode     : {mode}")
    print(f"   Strategy : S&R Bounce + Breakout/Retest")
    print(f"   Patterns : Engulfing + Pin Bar")
    print(f"   Interval : every {SLEEP_SECONDS} seconds")
    print("=" * 55)
    print()


def log(msg):
    now = datetime.now().strftime("%H:%M:%S")
    print(f"[{now}] {msg}")


def run():
    print_header()

    log("Connecting to Exness MT5...")
    if not connect_mt5():
        print("❌ Could not connect. Is MT5 open?")
        return

    starting_balance = mt5.account_info().balance
    log(f"Starting balance : ${starting_balance:,.2f}")
    alert_bot_started(starting_balance)
    log("📱 Telegram notified")
    log("Bot running. Press Ctrl+C to stop.")
    print()

    cycle = 0
    while True:
        try:
            cycle += 1
            print("-" * 55)
            log(f"Cycle #{cycle} — scanning {SYMBOL}...")

            current_balance = mt5.account_info().balance

            # ── Daily loss check ──────────────────────
            if check_daily_loss_limit(starting_balance, current_balance):
                alert_daily_limit()
                log("🛑 Daily loss limit — shutting down.")
                break

            # ── Fetch candles ─────────────────────────
            df = fetch_candles()
            if df is None:
                log("⚠️  No candles — skipping")
                time.sleep(SLEEP_SECONDS)
                continue

            # ── Current price info ────────────────────
            last  = df.iloc[-1]
            price = last['close']

            # ── S&R levels ────────────────────────────
            levels = find_sr_levels(df)
            nearest = []
            for lp, lt in levels:
                if abs(price - lp) < 15:  # Show levels within 15 pts
                    nearest.append(f"{lt[:3].upper()}:{lp:.1f}")

            log(f"Gold    : {price}")
            log(f"Levels  : {' | '.join(nearest) if nearest else 'none nearby'}")

            # ── Check open position ───────────────────
            position = get_open_position()

            if position:
                log("📊 Monitoring open position:")
                print_position_status(position)
                log("Waiting for SL or TP...")

            else:
                # ── Get price action signal ───────────
                signal_info = get_signal(df)
                signal      = signal_info['signal']

                emoji = '🟢' if signal=='BUY' else '🔴' if signal=='SELL' else '⚪'
                log(f"Signal  : {emoji} {signal}")

                if signal == 'HOLD':
                    reason = signal_info.get('reason', 'waiting for pattern at S&R')
                    log(f"Reason  : {reason}")

                elif signal in ('BUY', 'SELL'):
                    print()
                    log(f"✅ Pattern: {signal_info['pattern']}")
                    log(f"   Setup : {signal_info['setup']}")
                    log(f"   Level : {signal_info['level_type']} @ {signal_info['level']}")
                    print()

                    # ── Calculate trade levels ────────
                    levels_plan = calculate_trade_levels(df, signal_info, current_balance)
                    print_trade_plan(levels_plan)
                    print()

                    # ── Telegram signal alert ─────────
                    alert_signal(signal, {
                        'close' : price,
                        'rsi'   : 0,
                        'vwap'  : 0,
                        'atr'   : levels_plan['sl_distance'],
                    })

                    # ── Place trade ───────────────────
                    result = place_trade(signal, levels_plan)
                    if result:
                        alert_trade_opened(signal, levels_plan)
                        log(f"📱 Alerts sent!")
                        log(f"🎯 Trade active! Ticket: {result['ticket']}")
                    else:
                        log("❌ Trade failed — retrying next cycle")

            print()
            log(f"Next scan in {SLEEP_SECONDS}s...")
            time.sleep(SLEEP_SECONDS)

        except KeyboardInterrupt:
            print()
            log("⛔ Stopped by user.")
            break

        except Exception as e:
            log(f"❌ Error: {e}")
            log("Retrying in 30s...")
            time.sleep(30)

    # ── Shutdown ──────────────────────────────────────
    print()
    final_balance = mt5.account_info().balance
    pnl   = final_balance - starting_balance
    emoji = '📈' if pnl >= 0 else '📉'
    alert_bot_stopped(pnl)
    log(f"{emoji} Session P&L : ${pnl:+,.2f}")
    log(f"Final balance  : ${final_balance:,.2f}")
    disconnect_mt5()
    log("✅ Shutdown complete.")


if __name__ == '__main__':
    run()