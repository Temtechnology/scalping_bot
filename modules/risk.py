# modules/risk.py
# Correct risk calculation for Gold on Exness

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import REWARD_RATIO, MAX_DAILY_LOSS, DOLLAR_RISK, MAX_LOT


def calculate_lot_size(sl_distance):
    """
    Correct Gold lot size formula for Exness.
    
    1 standard lot Gold = $100 per point
    0.01 lot Gold       = $1 per point
    
    Formula: lot = dollar_risk / (sl_distance × 100)
    
    Example:
    SL distance = 5 points, dollar risk = $50
    lot = 50 / (5 × 100) = 50 / 500 = 0.10 lots
    If SL hit  → lose exactly $50 ✅
    If TP hit  → make exactly $100 ✅
    """
    if sl_distance <= 0:
        return 0.01
    lot = DOLLAR_RISK / (sl_distance * 100)
    lot = round(lot, 2)
    lot = max(0.01, min(lot, MAX_LOT))  # Between 0.01 and MAX_LOT
    return lot


def calculate_trade_levels(df, signal_info, balance=None):
    """
    Calculate SL, TP and correct lot size.
    Works with both old string signal and new signal_info dict.
    """
    last  = df.iloc[-1]
    price = last['close']

    # ── Handle both old and new signal format ────────
    if isinstance(signal_info, dict):
        signal  = signal_info['signal']
        sl_ref  = signal_info.get('sl_ref', None)
        setup   = signal_info.get('setup', 'PRICE ACTION')
        pattern = signal_info.get('pattern', '')
        level   = signal_info.get('level', 0)
        level_type = signal_info.get('level_type', '')
    else:
        # Old format — plain string like 'BUY' or 'SELL'
        signal  = signal_info
        sl_ref  = None
        setup   = 'INDICATOR'
        pattern = ''
        level   = 0
        level_type = ''

    if signal == 'HOLD':
        return None

    # ── Calculate SL distance ─────────────────────────
    if sl_ref:
        sl_distance = abs(price - sl_ref)
    else:
        # Fallback to ATR if no S&R reference
        atr         = last.get('atr', 5.0)
        sl_distance = atr * 1.5

    # Minimum SL distance to avoid micro stops
    sl_distance = max(sl_distance, 3.0)   # Minimum 3 pts for Gold
    tp_distance = sl_distance * REWARD_RATIO

    # ── Entry, SL, TP ─────────────────────────────────
    if signal == 'BUY':
        stop_loss   = round(price - sl_distance, 3)
        take_profit = round(price + tp_distance, 3)
    else:
        stop_loss   = round(price + sl_distance, 3)
        take_profit = round(price - tp_distance, 3)

    # ── Correct lot size ──────────────────────────────
    lot_size      = calculate_lot_size(sl_distance)

    # ── Actual dollar risk/reward ─────────────────────
    actual_risk   = round(sl_distance * lot_size * 100, 2)
    actual_reward = round(actual_risk * REWARD_RATIO, 2)

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
    print(f"  Lot Size   : {levels['lot_size']}")
    print(f"  Risk       : ${levels['dollar_risk']}  (actual dollars)")
    print(f"  Reward     : ${levels['dollar_reward']}  (if TP hit)")
    print(f"  R:R        : {levels['rr_ratio']}")


# ── TEST ─────────────────────────────────────────────
if __name__ == '__main__':
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from modules.data_feed import connect_mt5, fetch_candles, disconnect_mt5

    print("Testing correct Gold risk calculation...")
    if connect_mt5():
        import MetaTrader5 as mt5
        balance = mt5.account_info().balance
        df      = fetch_candles()

        print()
        print("── BUY simulation (SL = 5 points away) ──")
        fake_buy = {'signal': 'BUY', 'sl_ref': df.iloc[-1]['close'] - 5,
                    'setup': 'TEST', 'pattern': 'Test', 'level': 0, 'level_type': ''}
        levels = calculate_trade_levels(df, fake_buy, balance)
        print_trade_plan(levels)

        print()
        print("── SELL simulation (SL = 8 points away) ──")
        fake_sell = {'signal': 'SELL', 'sl_ref': df.iloc[-1]['close'] + 8,
                     'setup': 'TEST', 'pattern': 'Test', 'level': 0, 'level_type': ''}
        levels = calculate_trade_levels(df, fake_sell, balance)
        print_trade_plan(levels)

        print()
        print("── Daily loss limit test ──")
        print(f"  4% loss → stop? {check_daily_loss_limit(10000, 9600)}")
        print(f"  6% loss → stop? {check_daily_loss_limit(10000, 9400)}")

        disconnect_mt5()