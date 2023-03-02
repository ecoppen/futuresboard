import unittest

from futuresboard.exchange.factory import load_exchanges


class TestExchangeFactory(unittest.TestCase):
    def test_factory(self):
        exchanges = load_exchanges()
        assert len(exchanges) == 3
        assert [*exchanges] == ["binance", "bybit", "okx"]
        for exchange in exchanges:
            assert exchange == exchanges[exchange].exchange
