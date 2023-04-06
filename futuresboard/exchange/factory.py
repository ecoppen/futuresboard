from futuresboard.exchange.binance import Binance
from futuresboard.exchange.bybit import Bybit
from futuresboard.exchange.okx import Okx


def load_exchanges():
    return {
        "binance": Binance(),
        "bybit": Bybit(),
        "okx": Okx(),
    }
