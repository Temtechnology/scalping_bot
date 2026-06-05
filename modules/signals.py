# modules/signals.py
# Price Action Strategy — S&R Bounce + Breakout/Retest

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import SR_LOOKBACK, SR_ZONE, SR_STRENGTH, MIN_BODY_RATIO, PIN_BAR_RATIO, BREAKOUT_CONFIRM


# ── S&R DETECTION ────────────────────────────────────

def find_sr_levels(df):
    """
    Automatically detect Support and Resistance levels.
    
    Method:
    - Resistance = swing highs (candle high > neighbours on both sides)
    - Support    = swing lows  (candle low  < neighbours on both sides)
    - Level is valid if price tested it SR_STRENGTH times
    
    Returns list of (price, type) tuples — type is 'resistance' or 'support'
    """
    levels = []
    data   = df.tail(SR_LOOKBACK)

    for i in range(2, len(data) - 2):
        row  = data.iloc[i]
        prev = data.iloc[i - 1]
        prev2= data.iloc[i - 2]
        next1= data.iloc[i + 1]
        next2= data.iloc[i + 2]

        # Swing HIGH — resistance
        if (row['high'] > prev['high'] and
            row['high'] > prev2['high'] and
            row['high'] > next1['high'] and
            row['high'] > next2['high']):
            levels.append((row['high'], 'resistance'))

        # Swing LOW — support
        if (row['low'] < prev['low'] and
            row['low'] < prev2['low'] and
            row['low'] < next1['low'] and
            row['low'] < next2['low']):
            levels.append((row['low'], 'support'))

    # Remove duplicate levels that are too close together
    filtered = []
    for level in levels:
        too_close = False
        for existing in filtered:
            if abs(level[0] - existing[0]) < SR_ZONE * 2:
                too_close = True
                break
        if not too_close:
            filtered.append(level)

    return filtered


def near_level(price, level, zone=None):
    """Check if price is within the S&R zone."""
    if zone is None:
        zone = SR_ZONE
    return abs(price - level) <= zone


# ── CANDLESTICK PATTERNS ─────────────────────────────

def is_bullish_engulfing(prev, last):
    """
    Bullish Engulfing:
    - Previous candle is bearish (red)
    - Current candle is bullish (green)
    - Current body completely engulfs previous body
    """
    prev_bearish = prev['close'] < prev['open']
    curr_bullish = last['close'] > last['open']

    if not prev_bearish or not curr_bullish:
        return False

    # Current body engulfs previous body
    engulfs = (last['close'] > prev['open'] and
               last['open']  < prev['close'])

    # Body must be significant
    candle_range = last['high'] - last['low']
    body         = abs(last['close'] - last['open'])
    strong_body  = (body / candle_range) >= MIN_BODY_RATIO if candle_range > 0 else False

    return engulfs and strong_body


def is_bearish_engulfing(prev, last):
    """
    Bearish Engulfing:
    - Previous candle is bullish (green)
    - Current candle is bearish (red)
    - Current body completely engulfs previous body
    """
    prev_bullish = prev['close'] > prev['open']
    curr_bearish = last['close'] < last['open']

    if not prev_bullish or not curr_bearish:
        return False

    engulfs = (last['close'] < prev['open'] and
               last['open']  > prev['close'])

    candle_range = last['high'] - last['low']
    body         = abs(last['close'] - last['open'])
    strong_body  = (body / candle_range) >= MIN_BODY_RATIO if candle_range > 0 else False

    return engulfs and strong_body


def is_pin_bar_bullish(candle):
    """
    Bullish Pin Bar (Hammer):
    - Long lower wick (rejection of lower prices)
    - Small body at top of candle
    - Signals reversal UP from support
    """
    candle_range = candle['high'] - candle['low']
    if candle_range == 0:
        return False

    body        = abs(candle['close'] - candle['open'])
    lower_wick  = min(candle['open'], candle['close']) - candle['low']
    upper_wick  = candle['high'] - max(candle['open'], candle['close'])

    # Lower wick must be 65%+ of total range
    long_lower  = (lower_wick / candle_range) >= PIN_BAR_RATIO
    small_upper = upper_wick < lower_wick * 0.3

    return long_lower and small_upper


def is_pin_bar_bearish(candle):
    """
    Bearish Pin Bar (Shooting Star):
    - Long upper wick (rejection of higher prices)
    - Small body at bottom of candle
    - Signals reversal DOWN from resistance
    """
    candle_range = candle['high'] - candle['low']
    if candle_range == 0:
        return False

    body        = abs(candle['close'] - candle['open'])
    upper_wick  = candle['high'] - max(candle['open'], candle['close'])
    lower_wick  = min(candle['open'], candle['close']) - candle['low']

    long_upper  = (upper_wick / candle_range) >= PIN_BAR_RATIO
    small_lower = lower_wick < upper_wick * 0.3

    return long_upper and small_lower


# ── BREAKOUT DETECTION ───────────────────────────────

def is_breakout_above(df, resistance):
    """
    Breakout above resistance:
    - Price closed above resistance for BREAKOUT_CONFIRM candles
    - Now pulling back to retest the broken level
    """
    recent = df.tail(BREAKOUT_CONFIRM + 3)

    # Check last N candles closed above resistance
    breakout_candles = recent.iloc[-(BREAKOUT_CONFIRM+1):-1]
    held_above = all(c['close'] > resistance for _, c in breakout_candles.iterrows())

    if not held_above:
        return False

    # Now price is pulling back toward the level (retest)
    last  = df.iloc[-1]
    retest = near_level(last['close'], resistance, SR_ZONE * 2)

    return retest


def is_breakout_below(df, support):
    """
    Breakout below support:
    - Price closed below support for BREAKOUT_CONFIRM candles
    - Now pulling back to retest the broken level
    """
    recent = df.tail(BREAKOUT_CONFIRM + 3)

    breakout_candles = recent.iloc[-(BREAKOUT_CONFIRM+1):-1]
    held_below = all(c['close'] < support for _, c in breakout_candles.iterrows())

    if not held_below:
        return False

    last   = df.iloc[-1]
    retest = near_level(last['close'], support, SR_ZONE * 2)

    return retest


# ── MAIN SIGNAL FUNCTION ─────────────────────────────

def get_signal(df):
    """
    Main signal engine — checks both setups:
    Setup 1: S&R Bounce  (reversal at level)
    Setup 2: S&R Breakout + Retest (continuation after break)

    Returns signal dict with type, setup, pattern, and level
    """
    last  = df.iloc[-1]
    prev  = df.iloc[-2]
    price = last['close']

    # Find all current S&R levels
    levels = find_sr_levels(df)

    if not levels:
        return {'signal': 'HOLD', 'reason': 'No S&R levels found'}

    # ── SETUP 1: S&R BOUNCE ───────────────────────────
    for level_price, level_type in levels:

        if level_type == 'support' and near_level(price, level_price):
            # Price at support — look for bullish reversal candle
            if is_bullish_engulfing(prev, last):
                return {
                    'signal' : 'BUY',
                    'setup'  : 'BOUNCE',
                    'pattern': 'Bullish Engulfing',
                    'level'  : level_price,
                    'level_type': 'Support',
                    'entry'  : price,
                    'sl_ref' : level_price - SR_ZONE,
                }
            if is_pin_bar_bullish(last):
                return {
                    'signal' : 'BUY',
                    'setup'  : 'BOUNCE',
                    'pattern': 'Bullish Pin Bar',
                    'level'  : level_price,
                    'level_type': 'Support',
                    'entry'  : price,
                    'sl_ref' : level_price - SR_ZONE,
                }

        if level_type == 'resistance' and near_level(price, level_price):
            # Price at resistance — look for bearish reversal candle
            if is_bearish_engulfing(prev, last):
                return {
                    'signal' : 'SELL',
                    'setup'  : 'BOUNCE',
                    'pattern': 'Bearish Engulfing',
                    'level'  : level_price,
                    'level_type': 'Resistance',
                    'entry'  : price,
                    'sl_ref' : level_price + SR_ZONE,
                }
            if is_pin_bar_bearish(last):
                return {
                    'signal' : 'SELL',
                    'setup'  : 'BOUNCE',
                    'pattern': 'Bearish Pin Bar',
                    'level'  : level_price,
                    'level_type': 'Resistance',
                    'entry'  : price,
                    'sl_ref' : level_price + SR_ZONE,
                }

    # ── SETUP 2: BREAKOUT + RETEST ────────────────────
    for level_price, level_type in levels:

        if level_type == 'resistance':
            if is_breakout_above(df, level_price):
                if is_bullish_engulfing(prev, last) or is_pin_bar_bullish(last):
                    pattern = 'Bullish Engulfing' if is_bullish_engulfing(prev, last) else 'Pin Bar'
                    return {
                        'signal' : 'BUY',
                        'setup'  : 'BREAKOUT',
                        'pattern': f'Breakout Retest + {pattern}',
                        'level'  : level_price,
                        'level_type': 'Broken Resistance → Support',
                        'entry'  : price,
                        'sl_ref' : level_price - SR_ZONE,
                    }

        if level_type == 'support':
            if is_breakout_below(df, level_price):
                if is_bearish_engulfing(prev, last) or is_pin_bar_bearish(last):
                    pattern = 'Bearish Engulfing' if is_bearish_engulfing(prev, last) else 'Pin Bar'
                    return {
                        'signal' : 'SELL',
                        'setup'  : 'BREAKOUT',
                        'pattern': f'Breakout Retest + {pattern}',
                        'level'  : level_price,
                        'level_type': 'Broken Support → Resistance',
                        'entry'  : price,
                        'sl_ref' : level_price + SR_ZONE,
                    }

    return {'signal': 'HOLD', 'reason': 'No pattern at S&R levels'}


# ── TEST ─────────────────────────────────────────────
if __name__ == '__main__':
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from modules.data_feed import connect_mt5, fetch_candles, disconnect_mt5

    print("Testing Price Action Signal Engine...")
    if connect_mt5():
        df     = fetch_candles()
        levels = find_sr_levels(df)
        result = get_signal(df)

        print(f"\n── S&R Levels Found: {len(levels)} ──")
        for price, ltype in levels[-5:]:
            print(f"  {ltype.upper():12} : {price:.3f}")

        print(f"\n── Signal ──")
        print(f"  {result}")

        disconnect_mt5()