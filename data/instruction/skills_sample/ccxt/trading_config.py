# Trading configuration for multi-exchange bot

EXCHANGES = {
    "binance": {
        "api_key": "YOUR_BINANCE_API_KEY",
        "secret": "YOUR_BINANCE_SECRET",
        "sandbox": True,
    },
    "kraken": {
        "api_key": "YOUR_KRAKEN_API_KEY",
        "secret": "YOUR_KRAKEN_SECRET",
        "sandbox": True,
    }
}

TRADING_PAIRS = ["BTC/USDT", "ETH/USDT", "SOL/USDT"]
OHLCV_TIMEFRAME = "1h"
OHLCV_LIMIT = 100

STRATEGY = {
    "order_type": "limit",
    "order_side": "buy",
    "amount_usdt": 100,
    "price_offset_pct": 0.5,  # Place limit order 0.5% below current price
}
