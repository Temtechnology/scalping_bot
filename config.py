# config.py — Price Action Bot Settings

# ── MT5 Account ──────────────────────────────────────
MT5_LOGIN    = 436146117
MT5_PASSWORD = "@Bot12345"
MT5_SERVER   = "Exness-MT5Trial9"


SYMBOL       = "XAUUSDm"
TIMEFRAME    = "M15"
CANDLE_LIMIT = 200

# ── S&R Detection ────────────────────────────────────
SR_LOOKBACK  = 50
SR_ZONE      = 1.5        # Tightened from 1.5 → better levels
SR_STRENGTH  = 3

# ── Candlestick Patterns ─────────────────────────────
MIN_BODY_RATIO   = 0.6
PIN_BAR_RATIO    = 0.65
BREAKOUT_CONFIRM = 3

# ── Risk Management ──────────────────────────────────
DOLLAR_RISK     = 100.0
REWARD_RATIO     = 3.0
MAX_DAILY_LOSS   = 0.05
MAX_LOT          = 0.20
MIN_SL_DISTANCE = 1.0

# ── Session Filter (WAT = GMT+1) ──────────────────────
LONDON_OPEN  = 9           # 9AM WAT
LONDON_CLOSE = 13          # 1PM WAT
NY_OPEN      = 14          # 2PM WAT
NY_CLOSE     = 18          # 6PM WAT

# ── Bot Behaviour ─────────────────────────────────────
SLEEP_SECONDS  = 60
PAPER_TRADING  = False
MAGIC_NUMBER   = 123456


# ── Telegram Alerts ──────────────────────────────────
TELEGRAM_TOKEN   = "8705959885:AAFt_ux9YJ3jCXyuQG65zLBbYDDOu5x9Q5k"    # ← paste your token
TELEGRAM_CHAT_ID = "5886438301"      # ← paste your chat ID
