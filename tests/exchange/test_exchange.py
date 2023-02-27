import unittest
from decimal import Decimal
from unittest.mock import patch

from futuresboard.exchange.binance import Exchange


class TestExchange(unittest.TestCase):
    def test_attributes(self):
        exchange = Exchange()
        assert exchange.exchange is None
        assert exchange.futures_api_url is None
        assert exchange.futures_trade_url is None
        assert exchange.weight == 0
        assert exchange.max_weight == 100

    @patch("time.sleep", return_value=None)
    def test_check_weight(self, patched_time_sleep):
        exchange = Exchange()
        exchange.update_weight(weight=200)
        exchange.check_weight()
        self.assertEqual(1, patched_time_sleep.call_count)

    def test_update_weight(self):
        exchange = Exchange()
        exchange.update_weight(weight=10)
        assert exchange.weight == 10

    def test_get_futures_price(self):
        exchange = Exchange()
        futures_price = exchange.get_futures_price(base="BTC", quote="USDT")
        assert futures_price == Decimal(-1.0)

    def test_get_futures_prices(self):
        exchange = Exchange()
        assert exchange.get_futures_prices() == []

    def test_get_futures_kline(self):
        exchange = Exchange()
        futures_kline = exchange.get_futures_kline(
            base="BTC", quote="USDT", start_time=1632009600000
        )
        assert futures_kline == []

    def test_get_futures_trade_url(self):
        exchange = Exchange()
        assert exchange.get_futures_trade_url() is None
