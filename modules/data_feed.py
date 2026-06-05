# modules/data_feed.py
# Connects to Exness MT5 and pulls live candle data

import MetaTrader5 as mt5
import pandas as pd
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import MT5_LOGIN, MT5_PASSWORD, MT5_SERVER, SYMBOL, CANDLE_LIMIT


def connect_mt5():
    """
    Start MT5 and log into your Exness account.
    MT5 desktop app must be open for this to work.
    """
    # Start MT5 connection
    if not mt5.initialize():
        print(f"❌ MT5 failed to start. Error: {mt5.last_error()}")
        return False

    # Log into your account
    login = mt5.login(
        login=MT5_LOGIN,
        password=MT5_PASSWORD,
        server=MT5_SERVER
    )

    if not login:
        print(f"❌ Login failed. Error: {mt5.last_error()}")
        print("Check your login, password and server name in config.py")
        mt5.shutdown()
        return False

    # Show account info on success
    info = mt5.account_info()
    print(f"✅ Connected to Exness MT5!")
    print(f"   Account  : {info.login}")
    print(f"   Balance  : ${info.balance:,.2f}")
    print(f"   Server   : {info.server}")
    return True


def fetch_candles():
    """
    Fetch OHLCV candle data for our symbol.
    Returns a clean pandas DataFrame.
    """
    import MetaTrader5 as mt5
    from config import SYMBOL, CANDLE_LIMIT

    # Map timeframe string to MT5 constant
    timeframe = mt5.TIMEFRAME_M5

    # Fetch candles — returns a numpy array
    rates = mt5.copy_rates_from_pos(SYMBOL, timeframe, 0, CANDLE_LIMIT)

    if rates is None:
        print(f"❌ Failed to fetch candles. Error: {mt5.last_error()}")
        print(f"   Make sure '{SYMBOL}' is in your MT5 Market Watch")
        return None

    # Convert to DataFrame
    df = pd.DataFrame(rates)

    # Convert timestamp to readable datetime
    df['time'] = pd.to_datetime(df['time'], unit='s')
    df.set_index('time', inplace=True)

    # Keep only the columns we need
    df = df[['open', 'high', 'low', 'close', 'tick_volume']].copy()
    df.rename(columns={'tick_volume': 'volume'}, inplace=True)

    return df


def disconnect_mt5():
    """Cleanly close the MT5 connection."""
    mt5.shutdown()
    print("MT5 disconnected.")


# ── TEST ─────────────────────────────────────────────
if __name__ == '__main__':
    print("Testing MT5 connection...")
    print()

    if connect_mt5():
        print()
        print(f"Fetching candles for {SYMBOL}...")
        df = fetch_candles()

        if df is not None:
            print(f"✅ Got {len(df)} candles!")
            print()
            print("Last 5 candles:")
            print(df.tail(5))

        disconnect_mt5()