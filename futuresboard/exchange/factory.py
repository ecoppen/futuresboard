from futuresboard.exchange.binance import Binance
from futuresboard.exchange.bybit import Bybit


def load_exchanges():
    return {
        "binance": Binance(),
        "bybit": Bybit(),
    }
