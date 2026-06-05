# modules/executor.py
# Places, monitors and closes trades on Exness via MT5

import MetaTrader5 as mt5
import time
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import SYMBOL, MAGIC_NUMBER, PAPER_TRADING, SLEEP_SECONDS


def get_current_price(signal):
    """
    Get the right price for the trade direction.
    BUY  uses ASK price (what market sells to you)
    SELL uses BID price (what market buys from you)
    """
    tick = mt5.symbol_info_tick(SYMBOL)
    if tick is None:
        print(f"❌ Can't get price for {SYMBOL}")
        return None
    return tick.ask if signal == 'BUY' else tick.bid


def place_trade(signal, levels):
    """
    Places a market order on Exness.
    If PAPER_TRADING=True in config, only simulates — no real order.

    Returns order result or simulated result.
    """

    # ── Paper Trading Mode ────────────────────────────
    if PAPER_TRADING:
        print(f"  📝 PAPER TRADE — no real order placed")
        print(f"  Would {signal} {levels['lot_size']} lot at {levels['entry']}")
        print(f"  SL: {levels['stop_loss']}  TP: {levels['take_profit']}")
        # Return a fake ticket number for tracking
        return {'ticket': 999999, 'paper': True}

    # ── Live Trading Mode ─────────────────────────────
    order_type = mt5.ORDER_TYPE_BUY if signal == 'BUY' else mt5.ORDER_TYPE_SELL
    price      = get_current_price(signal)

    if price is None:
        return None

    request = {
        "action"      : mt5.TRADE_ACTION_DEAL,
        "symbol"      : SYMBOL,
        "volume"      : levels['lot_size'],
        "type"        : order_type,
        "price"       : price,
        "sl"          : levels['stop_loss'],
        "tp"          : levels['take_profit'],
        "deviation"   : 20,            # Max slippage allowed (points)
        "magic"       : MAGIC_NUMBER,  # Our bot's unique ID
        "comment"     : "ScalpBot v1",
        "type_time"   : mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_FOK
    }

    result = mt5.order_send(request)

    if result.retcode == mt5.TRADE_RETCODE_DONE:
        print(f"  ✅ Order placed! Ticket: {result.order}")
        return {'ticket': result.order, 'paper': False}
    else:
        print(f"  ❌ Order failed. Code: {result.retcode} — {result.comment}")
        return None


def get_open_position():
    """
    Check if our bot has an open trade right now.
    Returns the position or None.
    """
    positions = mt5.positions_get(symbol=SYMBOL)
    if positions:
        for pos in positions:
            if pos.magic == MAGIC_NUMBER:
                return pos
    return None


def close_trade(position):
    """
    Closes an open position immediately at market price.
    Used for emergency exits.
    """
    if PAPER_TRADING:
        print(f"  📝 PAPER CLOSE — simulated close")
        return True

    # Reverse the trade to close it
    if position.type == mt5.ORDER_TYPE_BUY:
        order_type = mt5.ORDER_TYPE_SELL
        price      = mt5.symbol_info_tick(SYMBOL).bid
    else:
        order_type = mt5.ORDER_TYPE_BUY
        price      = mt5.symbol_info_tick(SYMBOL).ask

    request = {
        "action"      : mt5.TRADE_ACTION_DEAL,
        "symbol"      : SYMBOL,
        "volume"      : position.volume,
        "type"        : order_type,
        "position"    : position.ticket,
        "price"       : price,
        "deviation"   : 20,
        "magic"       : MAGIC_NUMBER,
        "comment"     : "ScalpBot close",
        "type_time"   : mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }

    result = mt5.order_send(request)
    if result.retcode == mt5.TRADE_RETCODE_DONE:
        print(f"  ✅ Position closed.")
        return True
    else:
        print(f"  ❌ Close failed: {result.comment}")
        return False


def print_position_status(position):
    """Show current trade status in terminal."""
    pnl   = position.profit
    emoji = '🟢' if pnl >= 0 else '🔴'
    ptype = 'LONG' if position.type == 0 else 'SHORT'
    print(f"  {emoji} Open {ptype} | Entry: {position.price_open} | "
          f"P&L: ${pnl:.2f} | SL: {position.sl} | TP: {position.tp}")


# ── TEST ─────────────────────────────────────────────
if __name__ == '__main__':
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    from modules.data_feed  import connect_mt5, fetch_candles, disconnect_mt5
    from modules.indicators import add_indicators
    from modules.risk       import calculate_trade_levels

    print("Connecting to MT5...")
    if connect_mt5():
        balance = mt5.account_info().balance
        print()

        df     = fetch_candles()
        df     = add_indicators(df)
        levels = calculate_trade_levels(df, 'BUY', balance)

        print("── Testing paper trade (BUY simulation) ──")
        result = place_trade('BUY', levels)
        print(f"  Result: {result}")
        print()

        print("── Checking for open positions ──")
        pos = get_open_position()
        if pos:
            print_position_status(pos)
        else:
            print("  No open positions (expected in paper mode)")

        disconnect_mt5()