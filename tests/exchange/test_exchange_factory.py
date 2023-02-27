import unittest

from futuresboard.exchange.factory import load_exchanges


class TestExchangeFactory(unittest.TestCase):
    def test_factory(self):
        exchanges = load_exchanges()
        assert len(exchanges) == 2
        assert [*exchanges] == ["binance", "bybit"]
        for exchange in exchanges:
            assert exchange == exchanges[exchange].exchange
