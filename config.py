# config.py — Price Action Bot Settings

# ── MT5 Account ──────────────────────────────────────
MT5_LOGIN    = 
MT5_PASSWORD = ""
MT5_SERVER   = ""


SYMBOL       = "XAUUSDm"
TIMEFRAME    = "M15"
CANDLE_LIMIT = 200

# ── S&R Detection ────────────────────────────────────
SR_LOOKBACK  = 50
SR_ZONE      = 1.5         # Tightened from 1.5 → better levels
SR_STRENGTH  = 3

# ── Candlestick Patterns ─────────────────────────────
MIN_BODY_RATIO   = 0.6
PIN_BAR_RATIO    = 0.65
BREAKOUT_CONFIRM = 3

# ── Risk Management ──────────────────────────────────
DOLLAR_RISK      = 50
REWARD_RATIO     = 2.0
MAX_DAILY_LOSS   = 0.05
MAX_LOT          = 0.10
MIN_SL_DISTANCE  = 1.0

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
TELEGRAM_TOKEN   = ""    # ← paste your token
TELEGRAM_CHAT_ID = ""      # ← paste your chat ID
