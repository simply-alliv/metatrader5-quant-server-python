from app.utils.constants import MT5Timeframe

# --- Fibonacci Strategy Settings ---
PAIRS = ['EURUSD.Z', 'GBPUSD.Z', 'USDJPY.Z', 'AUDUSD.Z', 'USDCAD.Z', 'USDCHF.Z', 'NZDUSD.Z']
PRIMARY_TIMEFRAME = MT5Timeframe.W1  # Timeframe for trend analysis (higher timeframe)
ENTRY_TIMEFRAME = MT5Timeframe.H4   # Timeframe for entry signals (lower timeframe)
LOOKBACK_PERIOD = 120                # Bars to look back for swing point detection

# Fibonacci Retracement Levels - Standard levels
FIB_LEVELS = [0.0, 0.236, 0.382, 0.50, 0.618, 0.786, 1.0]

# --- Trading Parameters ---
RISK_PER_TRADE = 0.02                 # Risk percentage per trade (e.g., 0.02 for 2%)
LEVERAGE = 200                        # Account leverage
DEVIATION = 20                        # Slippage/deviation for order execution
MAGIC_NUMBER = 219000                 # Magic number to identify trades from this strategy

# --- Candlestick Patterns ---
# Patterns to consider for entry signals (currently used in the strategy logic, can be made configurable here if needed)
CANDLESTICK_PATTERNS_BULLISH = ["bullish_engulfing", "morning_star"]
CANDLESTICK_PATTERNS_BEARISH = ["bearish_engulfing", "evening_star"]

# --- Advanced Strategy Settings (Optional - can be added later) ---
TP_LEVEL_MULTIPLIER = 3          # Example: Take Profit level multiplier based on Fibonacci range
SL_LEVEL_MULTIPLIER = 0.5          # Example: Stop Loss level multiplier based on Fibonacci range
# SWING_POINT_LOOKBACK = 200         # Example: Lookback for more significant swing points