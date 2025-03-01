# backend/django/app/quant/algorithms/fibonacci/entry.py

import pandas as pd
import requests
import logging
from dotenv import load_dotenv
import traceback

from app.utils.arithmetics import calculate_order_capital, calculate_order_size_usd, calculate_commission, get_price_at_pnl, get_pnl_at_price, convert_usd_to_lots
from app.utils.api.data import fetch_data_pos, symbol_info_tick, account_info
from app.utils.api.order import send_market_order
from app.utils.account import have_open_positions_in_symbol
from app.utils.market import is_market_open
from app.quant.indicators.trend import detect_trend, get_enhanced_swing_points
from app.quant.indicators.candlestick import detect_candlestick_pattern
from app.quant.indicators.fibonacci import calculate_fib_levels
from app.quant.algorithms.fibonacci.config import PAIRS, PRIMARY_TIMEFRAME, ENTRY_TIMEFRAME, LOOKBACK_PERIOD, FIB_LEVELS, RISK_PER_TRADE, LEVERAGE, DEVIATION, MAGIC_NUMBER, CANDLESTICK_PATTERNS_BULLISH, CANDLESTICK_PATTERNS_BEARISH, TP_LEVEL_MULTIPLIER, SL_LEVEL_MULTIPLIER
from app.utils.risk_management.position_sizing import calculate_position_size
from app.utils.db.create import create_trade

load_dotenv()
logger = logging.getLogger(__name__)

def entry_algorithm():
    try:
        for pair in PAIRS:
            logger.info(f"Checking {pair} for Fibonacci strategy entry.")
            if have_open_positions_in_symbol(pair):
                logger.info(f"Skipping {pair} due to existing open positions.")
                continue

            if not is_market_open(pair):
                logger.info(f"Skipping {pair} market is closed.")
                continue

            # Fetch data for primary and entry timeframes
            primary_rates = fetch_data_pos(pair, PRIMARY_TIMEFRAME, LOOKBACK_PERIOD + 2) # +2 for swing point detection
            entry_rates = fetch_data_pos(pair, ENTRY_TIMEFRAME, LOOKBACK_PERIOD)

            if primary_rates is None or primary_rates.empty:
                logger.info(f"Skipping {pair} due to insufficient primary timeframe data.")
                continue

            if entry_rates is None or entry_rates.empty:
                logger.info(f"Skipping {pair} due to insufficient entry timeframe data.")
                continue

            # Trend analysis on primary timeframe
            p_highs, p_lows = get_enhanced_swing_points(primary_rates)
            trend = detect_trend(p_highs, p_lows)

            # Fibonacci levels calculation
            fib_levels_prices = []
            swing_high = None
            swing_low = None
            if len(p_highs) >= 2 and len(p_lows) >= 2:
                swing_high = p_highs[-1]['price']
                swing_low = p_lows[-1]['price']
                fib_levels_prices = calculate_fib_levels(swing_high, swing_low, FIB_LEVELS)
            else:
                logger.info(f"Skipping {pair} - not enough swing points for Fibonacci levels.")
                continue

            # Candlestick pattern detection on entry timeframe
            pattern = detect_candlestick_pattern(entry_rates)
            tick_info = symbol_info_tick(pair)
            if tick_info is None or tick_info.empty:
                logger.info(f"Skipping {pair} - no tick info available.")
                continue
            current_price = tick_info['ask'].iloc[0] if trend == "uptrend" else tick_info['bid'].iloc[0]


            # Signal generation and order execution
            signal = None
            stop_loss_price = None # Initialize stop_loss_price
            take_profit_price = None # Initialize take_profit_price

            if trend == "uptrend" and pattern in CANDLESTICK_PATTERNS_BULLISH:
                for level in fib_levels_prices:
                    if abs(current_price - level) < 0.0005 and current_price > swing_low: # Price near Fib level and above swing low
                        signal = "buy"
                        stop_loss_price = swing_low
                        take_profit_price = fib_levels_prices[-1] # 100% retracement level as TP
                        break # Execute trade at the first valid level
            elif trend == "downtrend" and pattern in CANDLESTICK_PATTERNS_BEARISH:
                for level in fib_levels_prices:
                    if abs(current_price - level) < 0.0005 and current_price < swing_high: # Price near Fib level and below swing high
                        signal = "sell"
                        stop_loss_price = swing_high
                        take_profit_price = fib_levels_prices[0] # 0% retracement level as TP
                        break # Execute trade at the first valid level

            if signal:
                order_capital = calculate_order_capital(RISK_PER_TRADE) # Still using order_capital to define base risk amount
                order_type = signal.upper()
                last_tick_price = tick_info['ask'].iloc[0] if order_type == 'BUY' else tick_info['bid'].iloc[0]
                price_decimals = len(str(last_tick_price).split('.')[-1])

                account_balance_data = account_info()  # Fetch account balance
                if account_balance_data is None or account_balance_data.empty:
                    logger.error(f"Could not fetch account balance for position sizing. Skipping {pair}")
                    continue
                account_balance_usd = account_balance_data.iloc[0]['balance']


                if stop_loss_price is not None: # Ensure stop_loss_price is calculated
                    stop_loss_pips = abs(last_tick_price - stop_loss_price) / tick_info['point'].iloc[0] # Calculate SL in pips
                else:
                    logger.error(f"Stop loss price is not defined, cannot calculate position size for {pair}")
                    continue

                tick_value = tick_info['tick_value'].iloc[0]
                order_volume_lots = calculate_position_size(RISK_PER_TRADE, account_balance_usd, stop_loss_pips, tick_value)


                if isinstance(order_volume_lots, (pd.Series, pd.DataFrame)):
                    order_volume_lots = order_volume_lots.iloc[0] if not order_volume_lots.empty else 0.0

                if order_volume_lots < 0.01:
                    error_msg = f"Order volume too low for {pair} after position sizing."
                    logger.error({'error_msg': error_msg, 'order_volume_lots': order_volume_lots})
                    continue

                order_size_usd = calculate_order_size_usd(order_capital, LEVERAGE) # Recalculate order_size_usd based on order_capital - might need review if position sizing logic changes drastically.

                desired_sl_pnl = order_capital * RISK_PER_TRADE * SL_LEVEL_MULTIPLIER * -1
                commission = calculate_commission(order_size_usd, pair)

                sl_including_commission, sl_excluding_commission = get_price_at_pnl(
                    desired_pnl=desired_sl_pnl,
                    commission=commission,
                    order_size_usd=order_size_usd,
                    leverage=LEVERAGE,
                    entry_price=last_tick_price,
                    type=order_type
                )

                tp_including_commission, tp_excluding_commission = get_price_at_pnl(
                    desired_pnl=order_capital * RISK_PER_TRADE * TP_LEVEL_MULTIPLIER,
                    commission=commission,
                    order_size_usd=order_size_usd,
                    leverage=LEVERAGE,
                    entry_price=last_tick_price,
                    type=order_type
                )


                order = send_market_order(
                    symbol=pair,
                    volume=order_volume_lots,
                    order_type=order_type,
                    sl=round(stop_loss_price, price_decimals),
                    tp=round(take_profit_price, price_decimals),
                    deviation=DEVIATION,
                    type_filling="ORDER_FILLING_FOK",
                    magic=MAGIC_NUMBER,
                    position_size_usd=order_size_usd,
                    commission=commission,
                    capital=order_capital,
                    leverage=LEVERAGE
                )

                if order is not None:
                    trade_info = {
                        'event': 'trade_opened',
                        'symbol': pair,
                        'entry_condition': f"FIBONACCI {pattern.upper()} PATTERN DETECTED AT FIB LEVEL",
                        'order_capital': f"${order_capital:.5f}",
                        'order_size_usd': f"${order_size_usd:.5f}",
                        'risk_per_trade': f"{RISK_PER_TRADE * 100}%",
                        'desired_sl_pnl': f"${desired_sl_pnl:.5f}",
                        'commission': f"${commission:.5f}",
                        'order_info': {
                            'order': order,
                            'type': order_type,
                            "sl": stop_loss_price,
                            "tp": take_profit_price
                        },
                        'tick_info': tick_info,
                        'fibonacci_levels': fib_levels_prices,
                        'swing_high': swing_high,
                        'swing_low': swing_low,
                        'candlestick_pattern': pattern,
                        'trend': trend,
                        'sl_including_commission': {
                            'sl_including_commission': f"${sl_including_commission:.5f}",
                            'sl_price_difference_including_commission': f"${(sl_including_commission - last_tick_price):.5f}",
                            'sl_price_difference_percentage_including_commission': f"{(sl_including_commission / last_tick_price - 1) * 100:.5f}%",
                            'pnl_at_sl_including_commission': f"${get_pnl_at_price(sl_including_commission, last_tick_price, order_size_usd, LEVERAGE, order_type, commission)[1]:.5f}",
                        },
                        'sl_excluding_commission': {
                            'sl_excluding_commission': f"${sl_excluding_commission:.5f}",
                            'sl_price_difference_excluding_commission': f"${(sl_excluding_commission - last_tick_price):.5f}",
                            'sl_price_difference_percentage_excluding_commission': f"{(sl_excluding_commission / last_tick_price - 1) * 100:.5f}%",
                            'pnl_at_sl_excluding_commission': f"${get_pnl_at_price(sl_excluding_commission, last_tick_price, order_size_usd, LEVERAGE, order_type, commission)[1]:.5f}",
                        },
                        'tp_including_commission': {
                            'tp_including_commission': f"${tp_including_commission:.5f}",
                            'tp_price_difference_including_commission': f"${(tp_including_commission - last_tick_price):.5f}",
                            'tp_price_difference_percentage_including_commission': f"{(tp_including_commission / last_tick_price - 1) * 100:.5f}%",
                            'pnl_at_tp_including_commission': f"${get_pnl_at_price(tp_including_commission, last_tick_price, order_size_usd, LEVERAGE, order_type, commission)[1]:.5f}",
                        },
                        'tp_excluding_commission': {
                            'tp_excluding_commission': f"${tp_excluding_commission:.5f}",
                            'tp_price_difference_excluding_commission': f"${(tp_excluding_commission - last_tick_price):.5f}",
                            'tp_price_difference_percentage_excluding_commission': f"{(tp_excluding_commission / last_tick_price - 1) * 100:.5f}%",
                            'pnl_at_tp_excluding_commission': f"${get_pnl_at_price(tp_excluding_commission, last_tick_price, order_size_usd, LEVERAGE, order_type, commission)[1]:.5f}",
                        },
                    }

                    try:
                        create_trade(order, pair, order_capital, order_size_usd,
                                     LEVERAGE, commission, order_type, 'Alpari',
                                     'FOREX', 'FIBONACCI', PRIMARY_TIMEFRAME, order_volume_lots,
                                     stop_loss_price, take_profit_price) # Using calculated SL/TP prices
                    except Exception as e:
                        error_msg = f"DB Error creating trade record: {e}\n{traceback.format_exc()}"
                        logger.error(error_msg)

                    info_msg = f"FIBONACCI: Order placed for {pair}, signal: {signal}, pattern: {pattern}, Fib level near price: {current_price:.5f}"
                    logger.info(info_msg, trade_info, order)

                else:
                    trade_info = {
                        'event': 'trade_failed_to_open',
                        'entry_condition': f"FIBONACCI {pattern.upper()} PATTERN DETECTED AT FIB LEVEL",
                        'symbol': pair,
                        'type': order_type,
                        'order_capital': f"${order_capital:.5f}",
                        'order_volume_lots': f"{order_volume_lots} lots",
                        'order_size_usd': f"${order_size_usd:.5f}",
                        'risk_per_trade': f"{RISK_PER_TRADE * 100}%",
                        'desired_sl_pnl': f"${desired_sl_pnl:.5f}",
                        'commission': f"${commission:.5f}",
                        'tick_info': tick_info,
                        'fibonacci_levels': fib_levels_prices,
                        'swing_high': swing_high,
                        'swing_low': swing_low,
                        'candlestick_pattern': pattern,
                        'trend': trend,
                         'sl_including_commission': {
                            'sl_including_commission': f"${sl_including_commission:.5f}",
                            'sl_price_difference_including_commission': f"${(sl_including_commission - last_tick_price):.5f}",
                            'sl_price_difference_percentage_including_commission': f"{(sl_including_commission / last_tick_price - 1) * 100:.5f}%",
                            'pnl_at_sl_including_commission': f"${get_pnl_at_price(sl_including_commission, last_tick_price, order_size_usd, LEVERAGE, order_type, commission)[1]:.5f}",
                        },
                        'sl_excluding_commission': {
                            'sl_excluding_commission': f"${sl_excluding_commission:.5f}",
                            'sl_price_difference_excluding_commission': f"${(sl_excluding_commission - last_tick_price):.5f}",
                            'sl_price_difference_percentage_excluding_commission': f"{(sl_excluding_commission / last_tick_price - 1) * 100:.5f}%",
                            'pnl_at_sl_excluding_commission': f"${get_pnl_at_price(sl_excluding_commission, last_tick_price, order_size_usd, LEVERAGE, order_type, commission)[1]:.5f}",
                        },
                        'tp_including_commission': {
                            'tp_including_commission': f"${tp_including_commission:.5f}",
                            'tp_price_difference_including_commission': f"${(tp_including_commission - last_tick_price):.5f}",
                            'tp_price_difference_percentage_including_commission': f"{(tp_including_commission / last_tick_price - 1) * 100:.5f}%",
                            'pnl_at_tp_including_commission': f"${get_pnl_at_price(tp_including_commission, last_tick_price, order_size_usd, LEVERAGE, order_type, commission)[1]:.5f}",
                        },
                        'tp_excluding_commission': {
                            'tp_excluding_commission': f"${tp_excluding_commission:.5f}",
                            'tp_price_difference_excluding_commission': f"${(tp_excluding_commission - last_tick_price):.5f}",
                            'tp_price_difference_percentage_excluding_commission': f"{(tp_excluding_commission / last_tick_price - 1) * 100:.5f}%",
                            'pnl_at_tp_excluding_commission': f"${get_pnl_at_price(tp_excluding_commission, last_tick_price, order_size_usd, LEVERAGE, order_type, commission)[1]:.5f}",
                        },
                    }
                    error_msg = f"FIBONACCI: Order failed to open for {pair}, signal: {signal}, pattern: {pattern}, Fib level near price: {current_price:.5f}"
                    logger.error(error_msg, trade_info, order)
            else:
                message = f"FIBONACCI: No signal detected for {pair}. Trend: {trend}, Current price: {current_price:.5f}, Swing High: {swing_high}, Swing Low: {swing_low}"
                logger.info(message)


    except requests.RequestException as e:
        error_msg = f"Error fetching MT5 data: {str(e)}"
        logger.error(error_msg)
    except Exception as e:
        error_msg = f"Exception in fibonacci entry_algorithm: {e}\n{traceback.format_exc()}"
        logger.error(error_msg)