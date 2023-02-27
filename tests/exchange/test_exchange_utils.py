import unittest

from futuresboard.exchange.utils import Exchanges, Intervals, Markets


class TestExchangeUtils(unittest.TestCase):
    def test_exchanges_dataclass(self):
        assert Exchanges.BINANCE.value == "binance"
        assert Exchanges.BYBIT.value == "bybit"

    def test_markets_dataclass(self):
        assert Markets.FUTURES.value == "FUTURES"

    def test_intervals_dataclass(self):
        assert Intervals.ONE_MINUTE.value == "1m"
        assert Intervals.FIVE_MINUTES.value == "5m"
        assert Intervals.FIFTEEN_MINUTES.value == "15m"
        assert Intervals.ONE_HOUR.value == "1h"
        assert Intervals.FOUR_HOURS.value == "4h"
        assert Intervals.ONE_DAY.value == "1d"
        assert Intervals.ONE_WEEK.value == "1w"


if __name__ == "__main__":
    unittest.main()
