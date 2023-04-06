import unittest
from decimal import Decimal

import requests  # type: ignore
import responses

from futuresboard.exchange.binance import Binance
from futuresboard.exchange.utils import Intervals


class TestBinanceExchange(unittest.TestCase):
    def test_attributes(self):
        binance = Binance()
        assert binance.exchange == "binance"
        assert binance.futures_api_url == "https://fapi.binance.com"
        assert (
            binance.futures_trade_url == "https://www.binance.com/en/futures/BASEQUOTE"
        )
        assert binance.weight == 0
        assert binance.max_weight == 1000

    @responses.activate
    def test_get_futures_price_valid(self):
        binance = Binance()
        responses.get(
            url=f"{binance.futures_api_url}/fapi/v1/ticker/price?symbol=BTCUSDT",
            body='{"price": "16605.48"}',
            status=200,
            content_type="application/json",
            headers={"X-MBX-USED-WEIGHT-1M": "10"},
        )
        futures_price = binance.get_futures_price(base="BTC", quote="USDT")
        assert futures_price == Decimal("16605.48")
        assert binance.weight == 10

    @responses.activate
    def test_get_futures_price_invalid(self):
        binance = Binance()
        responses.get(
            url=f"{binance.futures_api_url}/fapi/v1/ticker/price?symbol=BTCUSDT",
            body="{}",
            status=200,
            content_type="application/json",
            headers={"X-MBX-USED-WEIGHT-1M": "10"},
        )
        futures_price = binance.get_futures_price(base="BTC", quote="USDT")
        assert futures_price == Decimal(-1.0)
        assert binance.weight == 10

    @responses.activate
    def test_get_futures_prices_valid(self):
        binance = Binance()
        responses.get(
            url=f"{binance.futures_api_url}/fapi/v1/ticker/price",
            body='[{"symbol": "XRPBUSD", "price": "0.3592"}, {"symbol": "MKRUSDT", "price": "526.2"}]',
            status=200,
            content_type="application/json",
            headers={"X-MBX-USED-WEIGHT-1M": "10"},
        )
        futures_prices = binance.get_futures_prices()
        assert futures_prices == {
            "XRPBUSD": Decimal("0.3592"),
            "MKRUSDT": Decimal("526.2"),
        }
        assert binance.weight == 10

    @responses.activate
    def test_get_futures_prices_invalid(self):
        binance = Binance()
        responses.get(
            url=f"{binance.futures_api_url}/fapi/v1/ticker/price",
            body="[]",
            status=200,
            content_type="application/json",
            headers={"X-MBX-USED-WEIGHT-1M": "10"},
        )
        futures_prices = binance.get_futures_prices()
        assert futures_prices == {}
        assert binance.weight == 10

    @responses.activate
    def test_get_futures_kline_valid(self):
        binance = Binance()
        responses.get(
            url=f"{binance.futures_api_url}/fapi/v1/klines?symbol=STMXUSDT&interval=1d&limit=500&startTime=1632009600000&endTime=1632182400000",
            body='[[1632009600000,"0.03515000","0.03518000","0.03277000","0.03337000","127617246.00000000",1632095999999,"4327991.04616000",15680,"64375971.00000000","2182522.22624000","0"],[1632096000000,"0.03336000","0.03344000","0.02689000","0.02786000","337670129.00000000",1632182399999,"9944265.78278600",30983,"172004389.00000000","5064091.80455000","0"],[1632182400000,"0.02786000","0.02866000","0.02418000","0.02481000","441562231.00000000",1632268799999,"11701702.31097000",33681,"229838713.00000000","6085871.73077800","0"]]',
            status=200,
            content_type="application/json",
            headers={"X-MBX-USED-WEIGHT-1M": "10"},
        )
        futures_kline = binance.get_futures_kline(
            base="STMX",
            quote="USDT",
            start_time=1632009600000,
            end_time=1632182400000,
            interval=Intervals.ONE_DAY,
            limit=500,
        )
        assert futures_kline == [
            {
                "timestamp": 1632009600000,
                "open": Decimal("0.03515000"),
                "high": Decimal("0.03518000"),
                "low": Decimal("0.03277000"),
                "close": Decimal("0.03337000"),
                "volume": Decimal("127617246.00000000"),
            },
            {
                "timestamp": 1632096000000,
                "open": Decimal("0.03336000"),
                "high": Decimal("0.03344000"),
                "low": Decimal("0.02689000"),
                "close": Decimal("0.02786"),
                "volume": Decimal("337670129.00000000"),
            },
            {
                "timestamp": 1632182400000,
                "open": Decimal("0.02786000"),
                "high": Decimal("0.02866000"),
                "low": Decimal("0.02418000"),
                "close": Decimal("0.02481000"),
                "volume": Decimal("441562231.00000000"),
            },
        ]
        assert binance.weight == 10

    @responses.activate
    def test_get_futures_kline_invalid(self):
        binance = Binance()
        responses.get(
            url=f"{binance.futures_api_url}/fapi/v1/klines?symbol=STMXUSDT&interval=1d&limit=500&startTime=1632009600000&endTime=1632182400000",
            body="{}",
            status=200,
            content_type="application/json",
            headers={"X-MBX-USED-WEIGHT-1M": "10"},
        )
        futures_kline = binance.get_futures_kline(
            base="STMX",
            quote="USDT",
            start_time=1632009600000,
            end_time=1632182400000,
            interval=Intervals.ONE_DAY,
            limit=500,
        )
        assert futures_kline == []
        assert binance.weight == 10


if __name__ == "__main__":
    unittest.main()
