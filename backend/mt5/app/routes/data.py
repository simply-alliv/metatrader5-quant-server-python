from flask import Blueprint, jsonify, request
import MetaTrader5 as mt5
import logging
from datetime import datetime
import pytz
import pandas as pd
from flasgger import swag_from
from lib import get_timeframe

data_bp = Blueprint('data', __name__)
logger = logging.getLogger(__name__)

@data_bp.route('/fetch_data_pos', methods=['GET'])
@swag_from({
    'tags': ['Data'],
    'parameters': [
        {
            'name': 'symbol',
            'in': 'query',
            'type': 'string',
            'required': True,
            'description': 'Symbol name to fetch data for.'
        },
        {
            'name': 'timeframe',
            'in': 'query',
            'type': 'string',
            'required': False,
            'default': 'M1',
            'description': 'Timeframe for the data (e.g., M1, M5, H1).'
        },
        {
            'name': 'num_bars',
            'in': 'query',
            'type': 'integer',
            'required': False,
            'default': 100,
            'description': 'Number of bars to fetch.'
        }
    ],
    'responses': {
        200: {
            'description': 'Data fetched successfully.',
            'schema': {
                'type': 'array',
                'items': {
                    'type': 'object',
                    'properties': {
                        'time': {'type': 'string', 'format': 'date-time'},
                        'open': {'type': 'number'},
                        'high': {'type': 'number'},
                        'low': {'type': 'number'},
                        'close': {'type': 'number'},
                        'tick_volume': {'type': 'integer'},
                        'spread': {'type': 'integer'},
                        'real_volume': {'type': 'integer'}
                    }
                }
            }
        },
        400: {
            'description': 'Invalid request parameters.'
        },
        404: {
            'description': 'Failed to get rates data.'
        },
        500: {
            'description': 'Internal server error.'
        }
    }
})
def fetch_data_pos_endpoint():
    """
    Fetch Data from Position
    ---
    description: Retrieve historical price data for a given symbol starting from a specific position.
    """
    try:
        symbol = request.args.get('symbol')
        timeframe = request.args.get('timeframe', 'M1')
        num_bars = int(request.args.get('num_bars', 100))
        
        if not symbol:
            return jsonify({"error": "Symbol parameter is required"}), 400

        mt5_timeframe = get_timeframe(timeframe)
        
        rates = mt5.copy_rates_from_pos(symbol, mt5_timeframe, 0, num_bars)
        if rates is None:
            return jsonify({"error": "Failed to get rates data"}), 404
        
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        
        return jsonify(df.to_dict(orient='records'))
    
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.error(f"Error in fetch_data_pos: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@data_bp.route('/fetch_data_range', methods=['GET'])
@swag_from({
    'tags': ['Data'],
    'parameters': [
        {
            'name': 'symbol',
            'in': 'query',
            'type': 'string',
            'required': True,
            'description': 'Symbol name to fetch data for.'
        },
        {
            'name': 'timeframe',
            'in': 'query',
            'type': 'string',
            'required': False,
            'default': 'M1',
            'description': 'Timeframe for the data (e.g., M1, M5, H1).'
        },
        {
            'name': 'start',
            'in': 'query',
            'type': 'string',
            'required': True,
            'format': 'date-time',
            'description': 'Start datetime in ISO format.'
        },
        {
            'name': 'end',
            'in': 'query',
            'type': 'string',
            'required': True,
            'format': 'date-time',
            'description': 'End datetime in ISO format.'
        }
    ],
    'responses': {
        200: {
            'description': 'Data fetched successfully.',
            'schema': {
                'type': 'array',
                'items': {
                    'type': 'object',
                    'properties': {
                        'time': {'type': 'string', 'format': 'date-time'},
                        'open': {'type': 'number'},
                        'high': {'type': 'number'},
                        'low': {'type': 'number'},
                        'close': {'type': 'number'},
                        'tick_volume': {'type': 'integer'},
                        'spread': {'type': 'integer'},
                        'real_volume': {'type': 'integer'}
                    }
                }
            }
        },
        400: {
            'description': 'Invalid request parameters.'
        },
        404: {
            'description': 'Failed to get rates data.'
        },
        500: {
            'description': 'Internal server error.'
        }
    }
})
def fetch_data_range_endpoint():
    """
    Fetch Data within a Date Range
    ---
    description: Retrieve historical price data for a given symbol within a specified date range.
    """
    try:
        symbol = request.args.get('symbol')
        timeframe = request.args.get('timeframe', 'M1')
        start_str = request.args.get('start')
        end_str = request.args.get('end')
        
        if not all([symbol, start_str, end_str]):
            return jsonify({"error": "Symbol, start, and end parameters are required"}), 400

        mt5_timeframe = get_timeframe(timeframe)
        
        # Convert string dates to datetime objects
        utc = pytz.UTC
        start_date = utc.localize(datetime.fromisoformat(start_str.replace('Z', '+00:00')))
        end_date = utc.localize(datetime.fromisoformat(end_str.replace('Z', '+00:00')))
        
        rates = mt5.copy_rates_range(symbol, mt5_timeframe, start_date, end_date)
        if rates is None:
            return jsonify({"error": "Failed to get rates data"}), 404
        
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        
        return jsonify(df.to_dict(orient='records'))
    
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.error(f"Error in fetch_data_range: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500
    
@data_bp.route('/account_info', methods=['GET'])
@swag_from({
    'tags': ['Data'],
    'responses': {
        200: {
            'description': 'Account information fetched successfully.',
            'schema': {
                'type': 'object',
                'properties': {
                    'login': {'type': 'integer'},
                    'trade_mode': {'type': 'integer'},
                    'leverage': {'type': 'integer'},
                    'limit_orders': {'type': 'integer'},
                    'margin_so_mode': {'type': 'integer'},
                    'trade_allowed': {'type': 'boolean'},
                    'trade_expert': {'type': 'boolean'},
                    'margin_mode': {'type': 'integer'},
                    'currency_digits': {'type': 'integer'},
                    'margin_initial': {'type': 'number'},
                    'margin_maintenance': {'type': 'number'},
                    'margin_rate_initial': {'type': 'number'},
                    'margin_rate_maintenance': {'type': 'number'},
                    'margin_liquidation': {'type': 'number'},
                    'margin_call': {'type': 'number'},
                    'balance': {'type': 'number'},
                    'credit': {'type': 'number'},
                    'equity': {'type': 'number'},
                    'profit': {'type': 'number'},
                    'margin': {'type': 'number'},
                    'margin_free': {'type': 'number'},
                    'margin_level': {'type': 'number'},
                    'margin_level_so': {'type': 'number'},
                    'assets': {'type': 'number'},
                    'liabilities': {'type': 'number'},
                    'commission_blocked': {'type': 'number'},
                    'name': {'type': 'string'},
                    'server': {'type': 'string'},
                    'currency': {'type': 'string'},
                    'company': {'type': 'string'}
                }
            }
        },
        404: {
            'description': 'Failed to get account information.'
        },
        500: {
            'description': 'Internal server error.'
        }
    }
})
def account_info_endpoint():
    """
    Fetch Account Information
    ---
    description: Retrieve MetaTrader 5 account information.
    """
    try:
        account = mt5.account_info()
        if account is None:
            return jsonify({"error": "Failed to get account information"}), 404

        # Convert account info to a dictionary
        account_dict = {
            'login': account.login,
            'trade_mode': account.trade_mode,
            'leverage': account.leverage,
            'limit_orders': account.limit_orders,
            'margin_so_mode': account.margin_so_mode,
            'trade_allowed': account.trade_allowed,
            'trade_expert': account.trade_expert,
            'margin_mode': account.margin_mode,
            'currency_digits': account.currency_digits,
            'margin_initial': account.margin_initial,
            'margin_maintenance': account.margin_maintenance,
            'margin_rate_initial': account.margin_rate_initial,
            'margin_rate_maintenance': account.margin_rate_maintenance,
            'margin_liquidation': account.margin_liquidation,
            'margin_call': account.margin_call,
            'balance': account.balance,
            'credit': account.credit,
            'equity': account.equity,
            'profit': account.profit,
            'margin': account.margin,
            'margin_free': account.margin_free,
            'margin_level': account.margin_level,
            'margin_level_so': account.margin_level_so,
            'assets': account.assets,
            'liabilities': account.liabilities,
            'commission_blocked': account.commission_blocked,
            'name': account.name,
            'server': account.server,
            'currency': account.currency,
            'company': account.company
        }

        return jsonify(account_dict), 200

    except Exception as e:
        logger.error(f"Error in account_info_endpoint: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500