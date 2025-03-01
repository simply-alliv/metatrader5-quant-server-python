# backend/django/app/quant/indicators/trend.py

def get_enhanced_swing_points(rates):
    """Improved swing point detection based on proper highs/lows

    Args:
        rates (list): List of candle data (open, high, low, close)

    Returns:
        tuple: Lists of swing highs and swing lows, each a list of dictionaries with 'index' and 'price'.
    """
    highs = []
    lows = []

    if len(rates) < 5: # Need at least 5 bars for swing point detection
        return highs, lows

    for i in range(2, len(rates)-2):
        # Proper High: two lower highs on both sides
        if (rates[i-2][3] < rates[i][3] and
            rates[i-1][3] < rates[i][3] and
            rates[i+1][3] < rates[i][3] and
            rates[i+2][3] < rates[i][3]):
            highs.append({'index': i, 'price': rates[i][3]})

        # Proper Low: two higher lows on both sides
        if (rates[i-2][4] > rates[i][4] and
            rates[i-1][4] > rates[i][4] and
            rates[i+1][4] > rates[i][4] and
            rates[i+2][4] > rates[i][4]):
            lows.append({'index': i, 'price': rates[i][4]})

    return highs, lows

def detect_trend(highs, lows):
    """Determine market trend based on swing points

    Args:
        highs (list): List of swing highs (dictionaries with 'price').
        lows (list): List of swing lows (dictionaries with 'price').

    Returns:
        str: "uptrend", "downtrend", or "range" indicating the market trend.
    """
    if len(highs) < 2 or len(lows) < 2:
        return "range"

    # Check for uptrend (higher highs and higher lows)
    if highs[-1]['price'] > highs[-2]['price'] and lows[-1]['price'] > lows[-2]['price']:
        return "uptrend"

    # Check for downtrend (lower highs and lower lows)
    if highs[-1]['price'] < highs[-2]['price'] and lows[-1]['price'] < lows[-2]['price']:
        return "downtrend"

    return "range"