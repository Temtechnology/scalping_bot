# modules/indicators.py
# Calculates all technical indicators on the candle data

import pandas as pd
import pandas_ta_classic as ta
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import EMA_FAST, EMA_MID, EMA_SLOW, RSI_PERIOD, BB_PERIOD


def add_indicators(df):
    """
    Takes raw OHLCV candle DataFrame.
    Adds EMA, RSI, VWAP, Bollinger Bands, ATR columns.
    Returns the enriched DataFrame.
    """

    # ── EMA: Exponential Moving Averages ─────────────
    # Fast EMA (9)  = reacts quickly to price changes
    # Mid  EMA (20) = medium term trend
    # Slow EMA (50) = overall trend direction
    df['ema_fast'] = ta.ema(df['close'], length=EMA_FAST)
    df['ema_mid']  = ta.ema(df['close'], length=EMA_MID)
    df['ema_slow'] = ta.ema(df['close'], length=EMA_SLOW)

    # ── RSI: Relative Strength Index ─────────────────
    # Above 50 = bullish momentum
    # Below 50 = bearish momentum
    # Above 70 = overbought (price may drop soon)
    # Below 30 = oversold  (price may rise soon)
    df['rsi'] = ta.rsi(df['close'], length=RSI_PERIOD)

    # ── VWAP: Volume Weighted Average Price ──────────
    # Price weighted by volume — key level institutions watch
    # Price above VWAP = bullish
    # Price below VWAP = bearish
    df['vwap'] = (df['close'] * df['volume']).cumsum() / df['volume'].cumsum()

    # ── Bollinger Bands ──────────────────────────────
    # Upper band = price is expensive / overbought zone
    # Lower band = price is cheap / oversold zone
    # Width shows volatility — wider = more volatile
    bb = ta.bbands(df['close'], length=BB_PERIOD)
    df['bb_upper'] = bb[f'BBU_{BB_PERIOD}_2.0']
    df['bb_lower'] = bb[f'BBL_{BB_PERIOD}_2.0']
    df['bb_mid']   = bb[f'BBM_{BB_PERIOD}_2.0']

    # ── ATR: Average True Range ──────────────────────
    # Measures volatility — used to set stop loss size
    # High ATR = big price swings = wider stop needed
    # Low ATR  = calm market = tighter stop ok
    df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=14)

    # Drop early rows where indicators aren't ready yet
    df.dropna(inplace=True)

    return df


# ── TEST ─────────────────────────────────────────────
if __name__ == '__main__':
    # Import data feed to get real candles
    from data_feed import connect_mt5, fetch_candles, disconnect_mt5

    print("Connecting to MT5...")
    if connect_mt5():
        print()
        df = fetch_candles()

        if df is not None:
            print("Calculating indicators...")
            df = add_indicators(df)

            print(f"✅ Done! {len(df)} candles with indicators")
            print()

            # Show the last candle with all indicators
            last = df.iloc[-1]
            print("=== LATEST CANDLE SNAPSHOT ===")
            print(f"  Close     : {last['close']:.3f}")
            print(f"  EMA Fast  : {last['ema_fast']:.3f}")
            print(f"  EMA Mid   : {last['ema_mid']:.3f}")
            print(f"  EMA Slow  : {last['ema_slow']:.3f}")
            print(f"  RSI       : {last['rsi']:.1f}")
            print(f"  VWAP      : {last['vwap']:.3f}")
            print(f"  BB Upper  : {last['bb_upper']:.3f}")
            print(f"  BB Lower  : {last['bb_lower']:.3f}")
            print(f"  ATR       : {last['atr']:.3f}")
            print()

            # Tell us what the market looks like right now
            print("=== MARKET READING ===")
            if last['close'] > last['vwap']:
                print("  Price is ABOVE VWAP → Bullish bias")
            else:
                print("  Price is BELOW VWAP → Bearish bias")

            if last['ema_fast'] > last['ema_mid'] > last['ema_slow']:
                print("  EMAs are STACKED BULLISH → Uptrend")
            elif last['ema_fast'] < last['ema_mid'] < last['ema_slow']:
                print("  EMAs are STACKED BEARISH → Downtrend")
            else:
                print("  EMAs are MIXED → No clear trend")

            if last['rsi'] > 70:
                print(f"  RSI {last['rsi']:.1f} → OVERBOUGHT ⚠️")
            elif last['rsi'] < 30:
                print(f"  RSI {last['rsi']:.1f} → OVERSOLD ⚠️")
            elif last['rsi'] > 50:
                print(f"  RSI {last['rsi']:.1f} → Bullish momentum")
            else:
                print(f"  RSI {last['rsi']:.1f} → Bearish momentum")

        disconnect_mt5()