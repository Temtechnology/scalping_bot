# config.py — Price Action Bot Settings

# ── MT5 Account ──────────────────────────────────────
MT5_LOGIN    = 436146117
MT5_PASSWORD = "@Bot12345"
MT5_SERVER   = "Exness-MT5Trial9"

# ── Market ───────────────────────────────────────────
SYMBOL       = "XAUUSDm"
TIMEFRAME    = "M15"          # M15 — your preferred timeframe
CANDLE_LIMIT = 200

# ── S&R Detection ────────────────────────────────────
SR_LOOKBACK  = 50             # Candles to look back for S&R levels
SR_ZONE      = 1.5            # Points — how close price must be to S&R
SR_STRENGTH  = 3              # How many times level must be tested

# ── Candlestick Patterns ─────────────────────────────
MIN_BODY_RATIO    = 0.6       # Engulfing body must be 60% of candle
PIN_BAR_RATIO     = 0.65      # Pin bar wick must be 65% of candle
BREAKOUT_CONFIRM  = 3         # Candles price must hold beyond S&R

# ── Risk Management ──────────────────────────────────
DOLLAR_RISK       = 50        # Risk exactly $50 per trade
REWARD_RATIO      = 2.0       # TP = 2× SL distance
MAX_DAILY_LOSS    = 0.05      # Shut down at 5% daily loss
MAX_LOT           = 0.10      # Safety cap on lot size
# Add this line:
MIN_SL_DISTANCE = 3.0    # Never allow SL closer than 3 points

# ── Bot Behaviour ────────────────────────────────────
SLEEP_SECONDS     = 60
PAPER_TRADING     = False
MAGIC_NUMBER      = 123456

# ── Telegram Alerts ──────────────────────────────────
TELEGRAM_TOKEN   = "8705959885:AAFt_ux9YJ3jCXyuQG65zLBbYDDOu5x9Q5k"    # ← paste your token
TELEGRAM_CHAT_ID = "5886438301"      # ← paste your chat ID