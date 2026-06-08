# modules/risk.py
# Dynamic compounding risk — 2% of current balance per trade

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import REWARD_RATIO, MAX_DAILY_LOSS, MAX_LOT, MIN_SL_DISTANCE, RISK_PCT


def calculate_lot_size(sl_distance, balance):
    """
    Dynamic compounding lot size.
    Risks 2% of CURRENT balance on every trade.
    As account grows → lot size grows automatically.

    Formula:
    dollar_risk = balance × RISK_PCT (2%)
    lot = dollar_risk / (sl_distance × 100)

    Example at $10,000:
    dollar_risk = $200
    SL = 5pts → lot = 200/(5×100) = 0.40 lots
    Risk if SL hit = 0.40 × 5 × 100 = $200 ✅

    Example at $15,000 (after profits):
    dollar_risk = $300
    SL = 5pts → lot = 300/(5×100) = 0.60 lots
    Risk if SL hit = 0.60 × 5 × 100 = $300 ✅
    """
    dollar_risk = balance * RISK_PCT
    if sl_distance <= 0:
        return 0.01
    lot = dollar_risk / (sl_distance * 100)
    lot = round(lot, 2)
    lot = max(0.01, min(lot, MAX_LOT))
    return lot


def calculate_trade_levels(df, signal_info, balance):
    """
    Calculate SL, TP and dynamic lot size based on current balance.
    Works with both string signal and signal_info dict.
    """
    last  = df.iloc[-1]
    price = last['close']

    # ── Handle signal format ──────────────────────────
    if isinstance(signal_info, dict):
        signal     = signal_info['signal']
        sl_ref     = signal_info.get('sl_ref', None)
        setup      = signal_info.get('setup', 'PRICE ACTION')
        pattern    = signal_info.get('pattern', '')
        level      = signal_info.get('level', 0)
        level_type = signal_info.get('level_type', '')
    else:
        signal     = signal_info
        sl_ref     = None
        setup      = 'INDICATOR'
        pattern    = ''
        level      = 0
        level_type = ''

    if signal == 'HOLD':
        return None

    # ── SL Distance ───────────────────────────────────
    if sl_ref:
        sl_distance = abs(price - sl_ref)
    else:
        atr         = last.get('atr', 5.0)
        sl_distance = atr * 1.5

    sl_distance = max(sl_distance, MIN_SL_DISTANCE)
    tp_distance = sl_distance * REWARD_RATIO

    # ── Entry, SL, TP ─────────────────────────────────
    if signal == 'BUY':
        stop_loss   = round(price - sl_distance, 3)
        take_profit = round(price + tp_distance, 3)
    else:
        stop_loss   = round(price + sl_distance, 3)
        take_profit = round(price - tp_distance, 3)

    # ── Dynamic lot size (compounds with balance) ─────
    lot_size      = calculate_lot_size(sl_distance, balance)

    # ── Actual dollar risk/reward ─────────────────────
    actual_risk   = round(sl_distance * lot_size * 100, 2)
    actual_reward = round(actual_risk * REWARD_RATIO, 2)
    risk_pct_show = round((actual_risk / balance) * 100, 2)

    return {
        'signal'        : signal,
        'entry'         : round(price, 3),
        'stop_loss'     : stop_loss,
        'take_profit'   : take_profit,
        'sl_distance'   : round(sl_distance, 3),
        'tp_distance'   : round(tp_distance, 3),
        'lot_size'      : lot_size,
        'dollar_risk'   : actual_risk,
        'dollar_reward' : actual_reward,
        'risk_pct'      : risk_pct_show,
        'rr_ratio'      : f"1:{REWARD_RATIO}",
        'setup'         : setup,
        'pattern'       : pattern,
        'level'         : level,
        'level_type'    : level_type,
    }


def check_daily_loss_limit(starting_balance, current_balance):
    """Shut down bot if daily loss exceeds MAX_DAILY_LOSS."""
    loss_pct = (starting_balance - current_balance) / starting_balance
    if loss_pct >= MAX_DAILY_LOSS:
        print(f"🛑 DAILY LOSS LIMIT HIT: {loss_pct*100:.1f}% loss today")
        print(f"   Starting: ${starting_balance:,.2f}")
        print(f"   Current : ${current_balance:,.2f}")
        return True
    return False


def print_trade_plan(levels):
    """Pretty print the trade plan."""
    if not levels:
        print("No trade plan — signal is HOLD")
        return

    signal = levels['signal']
    emoji  = '🟢 LONG' if signal == 'BUY' else '🔴 SHORT'

    print(f"=== TRADE PLAN: {emoji} ===")
    print()
    if levels.get('setup'):
        print(f"  Setup      : {levels['setup']}")
    if levels.get('pattern'):
        print(f"  Pattern    : {levels['pattern']}")
    if levels.get('level_type'):
        print(f"  Level      : {levels['level_type']} @ {levels['level']}")
    print()
    print(f"  Entry      : {levels['entry']}")
    print(f"  Stop Loss  : {levels['stop_loss']}  ({levels['sl_distance']} pts)")
    print(f"  Take Profit: {levels['take_profit']}  ({levels['tp_distance']} pts)")
    print(f"  Lot Size   : {levels['lot_size']}  (auto-calculated)")
    print(f"  Risk       : ${levels['dollar_risk']}  ({levels['risk_pct']}% of balance)")
    print(f"  Reward     : ${levels['dollar_reward']}  (if TP hit)")
    print(f"  R:R        : {levels['rr_ratio']}")


# ── TEST ─────────────────────────────────────────────
if __name__ == '__main__':
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from modules.data_feed import connect_mt5, fetch_candles, disconnect_mt5

    print("Testing dynamic compounding risk calculation...")
    if connect_mt5():
        import MetaTrader5 as mt5
        balance = mt5.account_info().balance
        df      = fetch_candles()
        print(f"Current balance: ${balance:,.2f}")
        print(f"Risk per trade : 2% = ${balance * 0.02:,.2f}")
        print()

        print("── BUY simulation (SL = 5 points) ──")
        fake_buy = {
            'signal': 'BUY', 'sl_ref': df.iloc[-1]['close'] - 5,
            'setup': 'BOUNCE', 'pattern': 'Bullish Engulfing',
            'level': 0, 'level_type': 'Support'
        }
        levels = calculate_trade_levels(df, fake_buy, balance)
        print_trade_plan(levels)

        print()
        print("── SELL simulation (SL = 8 points) ──")
        fake_sell = {
            'signal': 'SELL', 'sl_ref': df.iloc[-1]['close'] + 8,
            'setup': 'BOUNCE', 'pattern': 'Bearish Pin Bar',
            'level': 0, 'level_type': 'Resistance'
        }
        levels = calculate_trade_levels(df, fake_sell, balance)
        print_trade_plan(levels)

        print()
        print("── Compounding simulation ──")
        print(f"  {'Balance':>10}  {'2% Risk':>10}  {'Lot (5pt SL)':>14}")
        print(f"  {'─'*40}")
        for bal in [10000, 11000, 12000, 15000, 20000, 30000]:
            risk = bal * 0.02
            lot  = calculate_lot_size(5.0, bal)
            print(f"  ${bal:>9,}  ${risk:>9,.0f}  {lot:>14.2f} lots")

        print()
        print("── Daily loss limit test ──")
        print(f"  4% loss → stop? {check_daily_loss_limit(10000, 9600)}")
        print(f"  6% loss → stop? {check_daily_loss_limit(10000, 9400)}")

        disconnect_mt5()