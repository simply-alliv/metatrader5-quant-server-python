# backend/django/app/quant/indicators/fibonacci.py

def calculate_fib_levels(swing_high, swing_low, levels):
    """Calculates Fibonacci retracement levels.

    Args:
        swing_high (float): The recent swing high price.
        swing_low (float): The recent swing low price.
        levels (list): List of Fibonacci ratios (e.g., [0.0, 0.382, 0.5, 0.618, 1.0]).

    Returns:
        list: List of Fibonacci retracement price levels.
    """
    diff = swing_high - swing_low
    fib_prices = []
    for level in levels:
        fib_prices.append(swing_high - diff * level) # Retracement from high to low
    return fib_prices