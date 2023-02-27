from __future__ import annotations

import logging
from decimal import Decimal

from futuresboard.core.utils import send_public_request
from futuresboard.exchange.exchange import Exchange
from futuresboard.exchange.utils import Intervals

log = logging.getLogger(__name__)


class Bybit(Exchange):
    def __init__(self):
        super().__init__()
        log.info("Bybit initialised")

    exchange = "bybit"
    futures_api_url = "https://api.bybit.com"
    futures_trade_url = "https://www.bybit.com/trade/usdt/BASEQUOTE"
    max_weight = 120

    def get_futures_price(self, base: str, quote: str) -> Decimal:
        self.check_weight()
        params = {"category": "linear", "symbol": f"{base}{quote}"}
        header, raw_json = send_public_request(
            url=self.futures_api_url,
            url_path="/v5/market/tickers",
            payload=params,
        )
        if "result" in [*raw_json]:
            if "list" in [*raw_json["result"]]:
                if len(raw_json["result"]["list"]) > 0:
                    if "lastPrice" in [*raw_json["result"]["list"][0]]:
                        return Decimal(raw_json["result"]["list"][0]["lastPrice"])
        return Decimal(-1.0)

    def get_futures_prices(self) -> list:
        self.check_weight()
        params: dict = {"category": "linear"}
        header, raw_json = send_public_request(
            url=self.futures_api_url,
            url_path="/v5/market/tickers",
            payload=params,
        )
        if "result" in [*raw_json]:
            if "list" in [*raw_json["result"]]:
                return [
                    {"symbol": pair["symbol"], "price": Decimal(pair["lastPrice"])}
                    for pair in raw_json["result"]["list"]
                ]
        return []

    def get_futures_kline(
        self,
        base: str,
        quote: str,
        start_time: int | None = None,
        end_time: int | None = None,
        interval: Intervals = Intervals.ONE_DAY,
        limit: int = 200,
    ) -> list:
        self.check_weight()
        custom_intervals = {
            "1m": 1,
            "5m": 5,
            "15m": 15,
            "1h": 60,
            "4h": 240,
            "1d": "D",
            "1w": "W",
        }
        params = {
            "category": "linear",
            "symbol": f"{base}{quote}",
            "interval": custom_intervals[interval],
            "limit": limit,
        }

        if start_time is not None:
            params["start"] = start_time
        if end_time is not None:
            params["end"] = end_time

        header, raw_json = send_public_request(
            url=self.futures_api_url,
            url_path="/v5/market/kline",
            payload=params,
        )

        if "result" in [*raw_json]:
            if "list" in [*raw_json["result"]]:
                if len(raw_json["result"]["list"]) > 0:
                    if end_time is not None:
                        return [
                            {
                                "timestamp": int(candle[0]),
                                "open": Decimal(candle[1]),
                                "high": Decimal(candle[2]),
                                "low": Decimal(candle[3]),
                                "close": Decimal(candle[4]),
                                "volume": Decimal(candle[5]),
                            }
                            for candle in raw_json["result"]["list"]
                            if int(candle[0]) <= end_time
                        ]
                    return [
                        {
                            "timestamp": int(candle[0]),
                            "open": Decimal(candle[1]),
                            "high": Decimal(candle[2]),
                            "low": Decimal(candle[3]),
                            "close": Decimal(candle[4]),
                            "volume": Decimal(candle[5]),
                        }
                        for candle in raw_json["result"]["list"]
                    ]
        return []
