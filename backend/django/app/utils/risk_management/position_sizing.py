# backend/django/app/utils/risk_management/position_sizing.py

def calculate_position_size(risk_per_trade, account_balance, stop_loss_pips, tick_value):
    """Calculate position size based on risk percentage and stop loss in pips.

    Args:
        risk_per_trade (float): Risk per trade as a decimal (e.g., 0.01 for 1%).
        account_balance (float): Current trading account balance.
        stop_loss_pips (float): Stop loss distance in pips.
        tick_value (float): Tick value for the traded symbol (e.g., value per pip).

    Returns:
        float: Position size in lots, rounded to 2 decimal places. Returns 0 if tick_value or stop_loss_pips is zero.
    """
    if tick_value == 0 or stop_loss_pips == 0:
        return 0  # Avoid division by zero

    risk_amount = account_balance * risk_per_trade
    position_size = risk_amount / (stop_loss_pips * tick_value)
    return round(position_size, 2) # Round to 2 decimal places for lot size