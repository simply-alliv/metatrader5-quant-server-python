# backend/django/app/quant/indicators/candlestick.py

def detect_candlestick_pattern(rates):
    """Detect bullish/bearish reversal patterns

    Args:
        rates (list): List of candle data (open, high, low, close)

    Returns:
        str or None: Name of the detected candlestick pattern or None if no pattern is detected.
    """
    if len(rates) < 3: # Need at least 3 candles for patterns
        return None

    current = rates[-1]
    prev = rates[-2]
    prev2 = rates[-3]

    # Bullish Engulfing
    if (current[1] < current[4] and  # Current candle bullish
            prev[1] > prev[4] and     # Previous candle bearish
            current[4] > prev[1] and  # Current close > previous open
            current[3] < prev[4]):    # Current open < previous close
        return "bullish_engulfing"

    # Bearish Engulfing
    if (current[1] > current[4] and  # Current candle bearish
            prev[1] < prev[4] and     # Previous candle bullish
            current[4] < prev[1] and  # Current close < previous open
            current[3] > prev[4]):    # Current open > previous close
        return "bearish_engulfing"

    # Morning Star (simplified - more robust checks can be added)
    if (prev2[1] > prev2[4] and      # Far previous bearish
            prev[1] < prev[4] and     # Previous candle bullish (or small body)
            current[1] < current[4] and # Current candle bullish
            current[4] > (prev2[3] + prev2[4])/2): # Current close above midpoint of far previous
        return "morning_star"

    # Evening Star (simplified - more robust checks can be added)
    if (prev2[1] < prev2[4] and      # Far previous bullish
            prev[1] > prev[4] and     # Previous candle bearish (or small body)
            current[1] > current[4] and # Current candle bearish
            current[4] < (prev2[3] + prev2[4])/2): # Current close below midpoint of far previous
        return "evening_star"

    return None