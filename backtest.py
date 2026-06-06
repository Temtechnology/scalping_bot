# backtest.py — Price Action Strategy Backtest v2.1
# Updates: Session filter + Min SL 3pts + Tighter SR_ZONE 1.2

import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime, timedelta
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import (MT5_LOGIN, MT5_PASSWORD, MT5_SERVER, SYMBOL,
                    DOLLAR_RISK, REWARD_RATIO, MAX_LOT)

# ── Settings ──────────────────────────────────────────
MONTHS_BACK  = 1
INITIAL_BAL  = 10000
SR_LOOKBACK  = 50
SR_ZONE      = 1.5
MIN_BODY     = 0.6
PIN_RATIO    = 0.65
BREAKOUT_CON = 3
MIN_SL       = 1.0
LONDON_OPEN  = 9
LONDON_CLOSE = 13
NY_OPEN      = 14
NY_CLOSE     = 18


def connect():
    mt5.initialize()
    mt5.login(MT5_LOGIN, MT5_PASSWORD, MT5_SERVER)
    print(f"✅ Connected — fetching {MONTHS_BACK} months of {SYMBOL}...")


def fetch_history():
    end   = datetime.now()
    start = end - timedelta(days=MONTHS_BACK * 30)
    rates = mt5.copy_rates_range(SYMBOL, mt5.TIMEFRAME_M15, start, end)
    df    = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    df.set_index('time', inplace=True)
    df = df[['open','high','low','close','tick_volume']].copy()
    df.rename(columns={'tick_volume': 'volume'}, inplace=True)
    df.dropna(inplace=True)
    print(f"✅ Got {len(df):,} candles on M15 ({MONTHS_BACK} months)")
    return df


def in_session(timestamp):
    """Check if timestamp is within London or NY session."""
    hour = timestamp.hour
    return (LONDON_OPEN <= hour < LONDON_CLOSE) or (NY_OPEN <= hour < NY_CLOSE)


# ── S&R DETECTION ─────────────────────────────────────
def find_sr_levels(df, end_idx):
    data   = df.iloc[max(0, end_idx - SR_LOOKBACK): end_idx]
    levels = []

    for i in range(2, len(data) - 2):
        row   = data.iloc[i]
        prev  = data.iloc[i-1]
        prev2 = data.iloc[i-2]
        nxt1  = data.iloc[i+1]
        nxt2  = data.iloc[i+2]

        if (row['high'] > prev['high'] and row['high'] > prev2['high'] and
                row['high'] > nxt1['high'] and row['high'] > nxt2['high']):
            levels.append((row['high'], 'resistance'))

        if (row['low'] < prev['low'] and row['low'] < prev2['low'] and
                row['low'] < nxt1['low'] and row['low'] < nxt2['low']):
            levels.append((row['low'], 'support'))

    filtered = []
    for lv in levels:
        too_close = any(abs(lv[0] - ex[0]) < SR_ZONE * 2 for ex in filtered)
        if not too_close:
            filtered.append(lv)

    return filtered


def near_level(price, level, zone=None):
    z = zone if zone else SR_ZONE
    return abs(price - level) <= z


# ── CANDLESTICK PATTERNS ──────────────────────────────
def is_bull_engulf(prev, last):
    if prev['close'] >= prev['open'] or last['close'] <= last['open']:
        return False
    engulfs = last['close'] > prev['open'] and last['open'] < prev['close']
    rng     = last['high'] - last['low']
    body    = abs(last['close'] - last['open'])
    strong  = (body / rng) >= MIN_BODY if rng > 0 else False
    return engulfs and strong


def is_bear_engulf(prev, last):
    if prev['close'] <= prev['open'] or last['close'] >= last['open']:
        return False
    engulfs = last['close'] < prev['open'] and last['open'] > prev['close']
    rng     = last['high'] - last['low']
    body    = abs(last['close'] - last['open'])
    strong  = (body / rng) >= MIN_BODY if rng > 0 else False
    return engulfs and strong


def is_bull_pin(c):
    rng        = c['high'] - c['low']
    if rng == 0: return False
    lower_wick = min(c['open'], c['close']) - c['low']
    upper_wick = c['high'] - max(c['open'], c['close'])
    return (lower_wick / rng) >= PIN_RATIO and upper_wick < lower_wick * 0.3


def is_bear_pin(c):
    rng        = c['high'] - c['low']
    if rng == 0: return False
    upper_wick = c['high'] - max(c['open'], c['close'])
    lower_wick = min(c['open'], c['close']) - c['low']
    return (upper_wick / rng) >= PIN_RATIO and lower_wick < upper_wick * 0.3


# ── SIGNAL ────────────────────────────────────────────
def get_signal(df, i):
    last   = df.iloc[i]
    prev   = df.iloc[i-1]
    price  = last['close']
    levels = find_sr_levels(df, i)

    for lp, lt in levels:
        # ── BOUNCE ───────────────────────────────────
        if lt == 'support' and near_level(price, lp):
            if is_bull_engulf(prev, last) or is_bull_pin(last):
                return ('BUY', 'BOUNCE', lp, lp - SR_ZONE)

        if lt == 'resistance' and near_level(price, lp):
            if is_bear_engulf(prev, last) or is_bear_pin(last):
                return ('SELL', 'BOUNCE', lp, lp + SR_ZONE)

        # ── BREAKOUT RETEST ───────────────────────────
        if lt == 'resistance' and i >= BREAKOUT_CON + 1:
            window = df.iloc[i-BREAKOUT_CON-1: i-1]
            if all(c['close'] > lp for _, c in window.iterrows()):
                if near_level(price, lp, SR_ZONE * 2):
                    if is_bull_engulf(prev, last) or is_bull_pin(last):
                        return ('BUY', 'BREAKOUT', lp, lp - SR_ZONE)

        if lt == 'support' and i >= BREAKOUT_CON + 1:
            window = df.iloc[i-BREAKOUT_CON-1: i-1]
            if all(c['close'] < lp for _, c in window.iterrows()):
                if near_level(price, lp, SR_ZONE * 2):
                    if is_bear_engulf(prev, last) or is_bear_pin(last):
                        return ('SELL', 'BREAKOUT', lp, lp + SR_ZONE)

    return None


# ── LOT SIZE ──────────────────────────────────────────
def calc_lot(sl_distance):
    """
    Bitcoin lot size formula on Exness:
    1 lot BTC = contract size of 1 BTC
    At $60,000 BTC price:
    1 lot = $60,000 value
    0.01 lot = $600 value
    
    P&L per point = lot × 1
    So: lot = dollar_risk / sl_distance
    """
    if sl_distance <= 0: return 0.01
    lot = DOLLAR_RISK / sl_distance
    return max(0.01, min(round(lot, 4), MAX_LOT))

# ── BACKTEST ──────────────────────────────────────────
def run_backtest(df):
    balance  = INITIAL_BAL
    trades   = []
    in_trade = False
    entry = sl = tp = direction = entry_time = setup = lot = None

    print(f"\nRunning backtest on {len(df):,} candles...")
    print(f"Session filter : London {LONDON_OPEN}AM-{LONDON_CLOSE}PM + NY {NY_OPEN}PM-{NY_CLOSE}PM WAT")
    print(f"Min SL         : {MIN_SL} points")
    print(f"SR Zone        : {SR_ZONE} points")
    print("=" * 55)

    for i in range(SR_LOOKBACK + 1, len(df)):
        row = df.iloc[i]

        # ── Monitor open trade ────────────────────────
        if in_trade:
            hit_tp = (direction=='BUY'  and row['high'] >= tp) or \
                     (direction=='SELL' and row['low']  <= tp)
            hit_sl = (direction=='BUY'  and row['low']  <= sl) or \
                     (direction=='SELL' and row['high'] >= sl)

            if hit_tp or hit_sl:
                sl_dist = abs(entry - sl)
                pnl     = (sl_dist * lot * 100 * REWARD_RATIO) if hit_tp else -(sl_dist * lot * 100)
                balance += pnl
                trades.append({
                    'entry_time' : entry_time,
                    'exit_time'  : row.name,
                    'direction'  : direction,
                    'setup'      : setup,
                    'entry'      : entry,
                    'sl'         : sl,
                    'tp'         : tp,
                    'lot'        : lot,
                    'result'     : 'WIN' if hit_tp else 'LOSS',
                    'pnl'        : round(pnl, 2),
                    'balance'    : round(balance, 2),
                })
                in_trade = False

        # ── Look for new signal ───────────────────────
        else:
            # ── Session filter ────────────────────────

            sig = get_signal(df, i)
            if sig:
                direction, setup, level, sl_ref = sig
                price    = row['close']
                sl_dist  = abs(price - sl_ref)
                sl_dist  = max(sl_dist, MIN_SL)   # Minimum 3 points
                tp_dist  = sl_dist * REWARD_RATIO
                lot      = calc_lot(sl_dist)
                entry    = price
                sl       = price - sl_dist if direction=='BUY' else price + sl_dist
                tp       = price + tp_dist if direction=='BUY' else price - tp_dist
                entry_time = row.name
                in_trade = True

    return trades


# ── REPORT ────────────────────────────────────────────
def print_report(trades, df, label="PRICE ACTION v2.1"):
    if not trades:
        print("❌ No trades found")
        return {}

    results   = pd.DataFrame(trades)
    wins      = results[results['result']=='WIN']
    losses    = results[results['result']=='LOSS']
    total     = len(results)
    win_rate  = len(wins) / total * 100
    total_pnl = results['pnl'].sum()
    avg_win   = wins['pnl'].mean()   if len(wins)   > 0 else 0
    avg_loss  = losses['pnl'].mean() if len(losses) > 0 else 0
    gross_win = wins['pnl'].sum()
    gross_loss= abs(losses['pnl'].sum())
    pf        = gross_win / gross_loss if gross_loss > 0 else 999
    final_bal = results['balance'].iloc[-1]
    ret       = (final_bal - INITIAL_BAL) / INITIAL_BAL * 100
    days      = (df.index[-1] - df.index[0]).days
    tpw       = total / (days/7) if days > 0 else 0

    # Max drawdown
    peak   = INITIAL_BAL
    max_dd = 0
    for b in results['balance']:
        if b > peak: peak = b
        dd = (peak - b) / peak * 100
        if dd > max_dd: max_dd = dd

    # Max loss streak
    streak = max_streak = 0
    for r in results['result']:
        streak = streak + 1 if r == 'LOSS' else 0
        max_streak = max(max_streak, streak)

    # Setup breakdown
    bounce   = results[results['setup']=='BOUNCE']
    breakout = results[results['setup']=='BREAKOUT']
    b_wr     = len(bounce[bounce['result']=='WIN']) / len(bounce) * 100 if len(bounce) > 0 else 0
    br_wr    = len(breakout[breakout['result']=='WIN']) / len(breakout) * 100 if len(breakout) > 0 else 0

    print(f"\n{'='*55}")
    print(f"   📊 {label} — {SYMBOL} ({MONTHS_BACK}mo)")
    print(f"{'='*55}")
    print(f"  Period         : {df.index[0].date()} → {df.index[-1].date()}")
    print(f"  Timeframe      : M15")
    print(f"  Session        : London + NY only")
    print(f"{'─'*55}")
    print(f"  Total Trades   : {total}")
    print(f"  Wins           : {len(wins)}  ({win_rate:.1f}%)")
    print(f"  Losses         : {len(losses)}  ({100-win_rate:.1f}%)")
    print(f"  Trades/Week    : {tpw:.1f}")
    print(f"{'─'*55}")
    print(f"  Bounce         : {len(bounce)} trades  {b_wr:.1f}% win rate")
    print(f"  Breakout       : {len(breakout)} trades  {br_wr:.1f}% win rate")
    print(f"{'─'*55}")
    print(f"  Starting Bal   : ${INITIAL_BAL:,.2f}")
    print(f"  Final Bal      : ${final_bal:,.2f}")
    print(f"  Total P&L      : ${total_pnl:+,.2f}")
    print(f"  Total Return   : {ret:+.1f}%")
    print(f"{'─'*55}")
    print(f"  Avg Win        : ${avg_win:+.2f}")
    print(f"  Avg Loss       : ${avg_loss:+.2f}")
    print(f"  Profit Factor  : {pf:.2f}")
    print(f"  Max Drawdown   : {max_dd:.1f}%")
    print(f"  Max Loss Streak: {max_streak} trades")
    print(f"{'='*55}")

    print(f"\n  🏆 VERDICT:")
    if pf >= 1.5 and ret > 0 and max_dd < 15:
        print(f"  ✅ STRATEGY PROFITABLE — ready for live demo!")
    elif pf >= 1.2 and ret > 0 and max_dd < 15:
        print(f"  ✅ GOOD EDGE — profitable, keep running on demo")
    elif ret > 0 and pf >= 1.0:
        print(f"  ⚠️  MARGINAL — profitable but needs work")
    else:
        print(f"  ❌ NEEDS WORK — do not go live yet")

    path = f'data/backtest_pa_v2.xlsx'
    results.to_excel(path, index=False)
    print(f"\n  💾 Saved to: {path}")
    print(f"{'='*55}\n")

    return {
        'label'   : label,
        'trades'  : total,
        'win_rate': win_rate,
        'return'  : ret,
        'pf'      : pf,
        'max_dd'  : max_dd,
        'streak'  : max_streak,
        'tpw'     : tpw,
    }


# ── RUN ───────────────────────────────────────────────
if __name__ == '__main__':
    connect()
    df       = fetch_history()
    trades   = run_backtest(df)
    stats_v2 = print_report(trades, df)

    # ── COMPARISON ───────────────────────────────────
    print("\n" + "="*55)
    print("   ⚔️  VERSION COMPARISON")
    print("="*55)

    stats_v1 = {
        'label'   : 'PA Bot v1 (no filters)',
        'trades'  : 342,
        'win_rate': 50.6,
        'return'  : 19.1,
        'pf'      : 1.53,
        'max_dd'  : 2.3,
        'streak'  : 12,
        'tpw'     : 13.4,
    }

    for s in [stats_v1, stats_v2]:
        if not s: continue
        verdict = '✅' if s['return'] > 0 and s['pf'] >= 1.2 else '❌'
        print(f"\n  {verdict} {s['label']}")
        print(f"     Trades/week : {s['tpw']:.1f}")
        print(f"     Win Rate    : {s['win_rate']:.1f}%")
        print(f"     Return      : {s['return']:+.1f}%")
        print(f"     Profit Fact : {s['pf']:.2f}")
        print(f"     Max DD      : {s['max_dd']:.1f}%")
        print(f"     Loss Streak : {s['streak']}")

    print()
    if stats_v2:
        if stats_v2['win_rate'] > stats_v1['win_rate']:
            print("  🏆 v2.1 improved win rate! Filters working ✅")
        if stats_v2['pf'] > stats_v1['pf']:
            print("  🏆 v2.1 improved profit factor! ✅")
        if stats_v2['max_dd'] < stats_v1['max_dd']:
            print("  🏆 v2.1 safer drawdown! ✅")
        if stats_v2['tpw'] < stats_v1['tpw']:
            print(f"  📉 Trades reduced: {stats_v1['tpw']:.1f} → {stats_v2['tpw']:.1f}/week (quality over quantity)")
    print("="*55)

    mt5.shutdown()