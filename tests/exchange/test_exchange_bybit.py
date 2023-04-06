import unittest
from decimal import Decimal

import requests  # type: ignore
import responses

from futuresboard.exchange.bybit import Bybit
from futuresboard.exchange.utils import Intervals


class TestBybitExchange(unittest.TestCase):
    def test_attributes(self):
        bybit = Bybit()
        assert bybit.exchange == "bybit"
        assert bybit.futures_api_url == "https://api.bybit.com"
        assert bybit.futures_trade_url == "https://www.bybit.com/trade/usdt/BASEQUOTE"
        assert bybit.weight == 0
        assert bybit.max_weight == 1200

    @responses.activate
    def test_get_futures_price_valid(self):
        bybit = Bybit()
        responses.get(
            url=f"{bybit.futures_api_url}/v5/market/tickers?category=linear&symbol=BTCUSDT",
            body='{"retCode":0,"retMsg":"OK","result":{"category":"linear","list":[{"symbol":"BTCUSDT","lastPrice":"23334.80","indexPrice":"23340.45","markPrice":"23332.21","prevPrice24h":"23240.00","price24hPcnt":"0.004079","highPrice24h":"23889.00","lowPrice24h":"23135.30","prevPrice1h":"23806.50","openInterest":"51737.719","openInterestValue":"1207155324.63","turnover24h":"3878849719.0390005","volume24h":"164954.492","fundingRate":"0.0001","nextFundingTime":"1677542400000","predictedDeliveryPrice":"","basisRate":"","deliveryFeeRate":"","deliveryTime":"0","ask1Size":"4.461","bid1Price":"23334.80","ask1Price":"23334.90","bid1Size":"36.848"}]},"retExtInfo":{},"time":1677515084284}',
            status=200,
            content_type="application/json",
        )
        futures_price = bybit.get_futures_price(base="BTC", quote="USDT")
        assert futures_price == Decimal("23334.80")

    @responses.activate
    def test_get_futures_price_invalid(self):
        bybit = Bybit()
        responses.get(
            url=f"{bybit.futures_api_url}/v5/market/tickers/price?symbol=BTCUSDT",
            body="{}",
            status=200,
            content_type="application/json",
        )
        futures_price = bybit.get_futures_price(base="BTC", quote="USDT")
        assert futures_price == Decimal(-1.0)

    @responses.activate
    def test_get_futures_prices_valid(self):
        bybit = Bybit()
        responses.get(
            url=f"{bybit.futures_api_url}/v5/market/tickers",
            body='{"retCode":0,"retMsg":"OK","result":{"category":"linear","list":[{"symbol":"10000NFTUSDT","lastPrice":"0.004890","indexPrice":"0.004899","markPrice":"0.004890","prevPrice24h":"0.004920","price24hPcnt":"-0.006097","highPrice24h":"0.004985","lowPrice24h":"0.004880","prevPrice1h":"0.004970","openInterest":"69719130","openInterestValue":"340926.55","turnover24h":"26004.58638998","volume24h":"5262760","fundingRate":"-0.000295","nextFundingTime":"1677542400000","predictedDeliveryPrice":"","basisRate":"","deliveryFeeRate":"","deliveryTime":"0","ask1Size":"108770","bid1Price":"0.004890","ask1Price":"0.004895","bid1Size":"287540"},{"symbol":"1000BONKUSDT","lastPrice":"0.000753","indexPrice":"0.000752","markPrice":"0.000753","prevPrice24h":"0.000764","price24hPcnt":"-0.014397","highPrice24h":"0.000785","lowPrice24h":"0.000744","prevPrice1h":"0.000773","openInterest":"10032282400","openInterestValue":"7554308.65","turnover24h":"6229294.0131","volume24h":"8126625900","fundingRate":"0.0001","nextFundingTime":"1677542400000","predictedDeliveryPrice":"","basisRate":"","deliveryFeeRate":"","deliveryTime":"0","ask1Size":"4330800","bid1Price":"0.000752","ask1Price":"0.000753","bid1Size":"1331700"}]}}',
            status=200,
            content_type="application/json",
        )
        futures_prices = bybit.get_futures_prices()
        assert futures_prices == {
            "10000NFTUSDT": Decimal("0.004890"),
            "1000BONKUSDT": Decimal("0.000753"),
        }

    @responses.activate
    def test_get_futures_prices_invalid(self):
        bybit = Bybit()
        responses.get(
            url=f"{bybit.futures_api_url}/v5/market/tickers",
            body="{}",
            status=200,
            content_type="application/json",
        )
        futures_prices = bybit.get_futures_prices()
        assert futures_prices == {}

    @responses.activate
    def test_get_futures_kline_valid_end_time(self):
        bybit = Bybit()
        responses.get(
            url=f"{bybit.futures_api_url}/v5/market/kline?category=linear&symbol=BTCUSDT&interval=D&limit=3&start=1632009600000&end=1632182400000",
            body='{"retCode":0,"retMsg":"OK","result":{"symbol":"BTCUSDT","category":"linear","list":[["1632182400000","43057","43600","39520","40724.5","102692.021","4182081209.2145"],["1632096000000","47274.5","47342","42500","43057","91656.427","3946450777.339"],["1632009600000","48300","48340.5","46880","47274.5","34445.799","1628407924.8255"]]},"retExtInfo":{},"time":1677516322292}',
            status=200,
            content_type="application/json",
        )
        futures_kline = bybit.get_futures_kline(
            base="BTC",
            quote="USDT",
            start_time=1632009600000,
            end_time=1632182400000,
            interval=Intervals.ONE_DAY,
            limit=3,
        )
        assert futures_kline == [
            {
                "timestamp": 1632182400000,
                "open": Decimal("43057"),
                "high": Decimal("43600"),
                "low": Decimal("39520"),
                "close": Decimal("40724.5"),
                "volume": Decimal("102692.021"),
            },
            {
                "timestamp": 1632096000000,
                "open": Decimal("47274.5"),
                "high": Decimal("47342"),
                "low": Decimal("42500"),
                "close": Decimal("43057"),
                "volume": Decimal("91656.427"),
            },
            {
                "timestamp": 1632009600000,
                "open": Decimal("48300"),
                "high": Decimal("48340.5"),
                "low": Decimal("46880"),
                "close": Decimal("47274.5"),
                "volume": Decimal("34445.799"),
            },
        ]

    @responses.activate
    def test_get_futures_kline_valid(self):
        bybit = Bybit()
        responses.get(
            url=f"{bybit.futures_api_url}/v5/market/kline?category=linear&symbol=BTCUSDT&interval=D&limit=3&start=1632009600000",
            body='{"retCode":0,"retMsg":"OK","result":{"symbol":"BTCUSDT","category":"linear","list":[["1632182400000","43057","43600","39520","40724.5","102692.021","4182081209.2145"],["1632096000000","47274.5","47342","42500","43057","91656.427","3946450777.339"],["1632009600000","48300","48340.5","46880","47274.5","34445.799","1628407924.8255"]]},"retExtInfo":{},"time":1677516528502}',
            status=200,
            content_type="application/json",
        )
        futures_kline = bybit.get_futures_kline(
            base="BTC",
            quote="USDT",
            start_time=1632009600000,
            interval=Intervals.ONE_DAY,
            limit=3,
        )
        assert futures_kline == [
            {
                "timestamp": 1632182400000,
                "open": Decimal("43057"),
                "high": Decimal("43600"),
                "low": Decimal("39520"),
                "close": Decimal("40724.5"),
                "volume": Decimal("102692.021"),
            },
            {
                "timestamp": 1632096000000,
                "open": Decimal("47274.5"),
                "high": Decimal("47342"),
                "low": Decimal("42500"),
                "close": Decimal("43057"),
                "volume": Decimal("91656.427"),
            },
            {
                "timestamp": 1632009600000,
                "open": Decimal("48300"),
                "high": Decimal("48340.5"),
                "low": Decimal("46880"),
                "close": Decimal("47274.5"),
                "volume": Decimal("34445.799"),
            },
        ]

    @responses.activate
    def test_get_futures_kline_invalid(self):
        bybit = Bybit()
        responses.get(
            url=f"{bybit.futures_api_url}/v5/market/kline?symbol=BTCUSDT&interval=D&limit=3&from=1632009600",
            body="{}",
            status=200,
            content_type="application/json",
        )
        futures_kline = bybit.get_futures_kline(
            base="BTC",
            quote="USDT",
            start_time=1632009600000,
            interval=Intervals.ONE_DAY,
            limit=3,
        )
        assert futures_kline == []


if __name__ == "__main__":
    unittest.main()
