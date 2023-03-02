import unittest
from decimal import Decimal
from unittest.mock import patch

import requests  # type: ignore
import responses

from futuresboard.exchange.okx import Okx
from futuresboard.exchange.utils import Intervals


class TestBybitExchange(unittest.TestCase):
    def test_attributes(self):
        okx = Okx()
        assert okx.exchange == "okx"
        assert okx.futures_api_url == "https://www.okx.com"
        assert okx.futures_trade_url == "https://www.okx.com/trade-futures/base-quote"
        assert okx.weight == 0
        assert okx.max_weight == 600

    @responses.activate
    def test_get_futures_price_valid(self):
        okx = Okx()
        responses.get(
            url=f"{okx.futures_api_url}/api/v5/market/ticker?instId=ADA-USD-230106",
            body='{"code":"0","msg":"","data":[{"instType":"FUTURES","instId":"ADA-USD-230106","last":"0.26276","lastSz":"2","askPx":"0.26288","askSz":"16","bidPx":"0.26244","bidSz":"52","open24h":"0.25106","high24h":"0.27006","low24h":"0.25056","volCcy24h":"2480779.8191","vol24h":"65114","ts":"1672865124308","sodUtc0":"0.25287","sodUtc8":"0.26787"}]}',
            status=200,
            content_type="application/json",
        )
        futures_price = okx.get_futures_price(base="ADA", quote="USD-230106")
        assert futures_price == Decimal("0.26276")

    @responses.activate
    def test_get_futures_price_invalid(self):
        okx = Okx()
        responses.get(
            url=f"{okx.futures_api_url}/api/v5/market/ticker?instId=ADA-USD-230106",
            body="{}",
            status=200,
            content_type="application/json",
        )
        futures_price = okx.get_futures_price(base="ADA", quote="USD-230106")
        assert futures_price == Decimal(-1.0)

    @responses.activate
    def test_get_futures_prices_valid(self):
        okx = Okx()
        responses.get(
            url=f"{okx.futures_api_url}/api/v5/market/tickers?instType=FUTURES",
            body='{"code":"0","msg":"","data":[{"instType":"FUTURES","instId":"ADA-USD-230106","last":"0.26327","lastSz":"5","askPx":"0.26338","askSz":"54","bidPx":"0.26276","bidSz":"116","open24h":"0.25121","high24h":"0.27006","low24h":"0.25056","volCcy24h":"2486177.1178","vol24h":"65260","ts":"1672865290208","sodUtc0":"0.25287","sodUtc8":"0.26787"},{"instType":"FUTURES","instId":"BCH-USD-230106","last":"100.49","lastSz":"5","askPx":"100.54","askSz":"35","bidPx":"100.39","bidSz":"109","open24h":"99.2","high24h":"102.3","low24h":"98.97","volCcy24h":"6165.9459","vol24h":"62252","ts":"1672865285409","sodUtc0":"99.5","sodUtc8":"101.37"}]}',
            status=200,
            content_type="application/json",
        )
        futures_prices = okx.get_futures_prices()
        assert futures_prices == [
            {"symbol": "ADAUSD230106", "price": Decimal("0.26327")},
            {"symbol": "BCHUSD230106", "price": Decimal("100.49")},
        ]

    @responses.activate
    def test_get_futures_prices_invalid(self):
        okx = Okx()
        responses.get(
            url=f"{okx.futures_api_url}/api/v5/market/tickers?instType=FUTURES",
            body="{}",
            status=200,
            content_type="application/json",
        )
        futures_prices = okx.get_futures_prices()
        assert futures_prices == []

    @responses.activate
    @patch("futuresboard.exchange.okx.Okx.get_instance_ids")
    def test_get_futures_kline_valid(self, mock_get_instance_ids):
        okx = Okx()

        responses.get(
            url=f"{okx.futures_api_url}/api/v5/market/candles?instId=BTC-USDT-230303&bar=1Dutc&limit=500&before=1632009599999&after=1632182400001",
            body='{"code":"0","msg":"","data":[["1632182400000","43938.2","44578","40263","41546.5","2888189","28881.89","1229831310.846","1"],["1632096000000","48382.9","48487.6","43213","43954.6","2781978","27819.78","1279974167.91","1"],["1632009600000","49699","49786.8","47927.7","48384.6","790243","7902.43","386819997.285","1"]]}',
            status=200,
            content_type="application/json",
        )
        mock_get_instance_ids.return_value = [
            "BTC-USDT-230331",
            "BTC-USDT-230303",
            "BTC-USDT-230630",
            "BTC-USDT-230310",
        ]
        futures_kline = okx.get_futures_kline(
            base="BTC",
            quote="USDT",
            start_time=1632009600000,
            end_time=1632182400000,
            interval=Intervals.ONE_DAY,
            limit=500,
        )
        assert futures_kline == [
            {
                "timestamp": 1632182400000,
                "open": Decimal("43938.2"),
                "high": Decimal("44578"),
                "low": Decimal("40263"),
                "close": Decimal("41546.5"),
                "volume": Decimal("2888189"),
            },
            {
                "timestamp": 1632096000000,
                "open": Decimal("48382.9"),
                "high": Decimal("48487.6"),
                "low": Decimal("43213"),
                "close": Decimal("43954.6"),
                "volume": Decimal("2781978"),
            },
            {
                "timestamp": 1632009600000,
                "open": Decimal("49699"),
                "high": Decimal("49786.8"),
                "low": Decimal("47927.7"),
                "close": Decimal("48384.6"),
                "volume": Decimal("790243"),
            },
        ]

    @responses.activate
    def test_get_futures_kline_invalid(self):
        okx = Okx()
        responses.get(
            url=f"{okx.futures_api_url}/api/v5/market/candles?instId=BTC-USDT-230303&bar=1Dutc&limit=500&before=1632009599999&after=1632182400001",
            body="{}",
            status=200,
            content_type="application/json",
        )
        futures_kline = okx.get_futures_kline(
            base="BTC",
            quote="USDT",
            start_time=1632009600000,
            end_time=1632182400000,
            interval=Intervals.ONE_DAY,
            limit=500,
        )
        assert futures_kline == []

    @responses.activate
    def test_get_futures_instance_ids_valid(self):
        okx = Okx()
        responses.get(
            url=f"{okx.futures_api_url}/api/v5/market/tickers?instType=FUTURES",
            body='{"code":"0","msg":"","data":[{"instType":"FUTURES","instId":"BTC-USDT-230331","last":"23480.7","lastSz":"6","askPx":"23474.9","askSz":"41","bidPx":"23474.8","bidSz":"6","open24h":"23841.6","high24h":"24007.3","low24h":"23405.1","volCcy24h":"1320.7","vol24h":"132070","ts":"1677752935304","sodUtc0":"23733.9","sodUtc8":"23827"},{"instType":"FUTURES","instId":"BTC-USDT-230303","last":"23402.1","lastSz":"6","askPx":"23404.2","askSz":"15","bidPx":"23404.1","bidSz":"6","open24h":"23758.7","high24h":"23915.9","low24h":"23328.5","volCcy24h":"660.76","vol24h":"66076","ts":"1677752934704","sodUtc0":"23651.9","sodUtc8":"23735.4"},{"instType":"FUTURES","instId":"BTC-USDT-230630","last":"23771.3","lastSz":"5","askPx":"23768.9","askSz":"8","bidPx":"23768.8","bidSz":"1","open24h":"24139","high24h":"24294.9","low24h":"23705.9","volCcy24h":"522.52","vol24h":"52252","ts":"1677752935704","sodUtc0":"24038.7","sodUtc8":"24102.4"},{"instType":"FUTURES","instId":"BTC-USDT-230310","last":"23414.5","lastSz":"6","askPx":"23416.6","askSz":"12","bidPx":"23416.5","bidSz":"6","open24h":"23770.3","high24h":"23927.4","low24h":"23343.5","volCcy24h":"409.16","vol24h":"40916","ts":"1677752934704","sodUtc0":"23668.7","sodUtc8":"23750.9"}]}',
            status=200,
            content_type="application/json",
        )
        futures_instance_ids = okx.get_instance_ids(base="BTC", quote="USDT")
        assert futures_instance_ids == [
            "BTC-USDT-230331",
            "BTC-USDT-230303",
            "BTC-USDT-230630",
            "BTC-USDT-230310",
        ]

    @responses.activate
    def test_get_futures_instance_ids_invalid(self):
        okx = Okx()
        responses.get(
            url=f"{okx.futures_api_url}/api/v5/market/tickers?instType=FUTURES",
            body="{}",
            status=200,
            content_type="application/json",
        )
        futures_instance_ids = okx.get_instance_ids(base="BTC", quote="USDT")
        assert futures_instance_ids == []


if __name__ == "__main__":
    unittest.main()
