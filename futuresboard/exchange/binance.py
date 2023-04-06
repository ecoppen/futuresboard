from __future__ import annotations

import logging
from decimal import Decimal

from futuresboard.core.utils import (
    find_in_string,
    send_public_request,
    send_signed_request,
)
from futuresboard.exchange.exchange import Exchange
from futuresboard.exchange.utils import Intervals

log = logging.getLogger(__name__)


class Binance(Exchange):
    def __init__(self):
        super().__init__()
        log.info("Binance initialised")

    exchange = "binance"
    news_url = "https://www.binance.com/en/support/announcement/"
    futures_api_url = "https://fapi.binance.com"
    futures_trade_url = "https://www.binance.com/en/futures/BASEQUOTE"
    max_weight = 1000

    def get_futures_price(self, base: str, quote: str) -> Decimal:
        self.check_weight()
        params: dict = {"symbol": f"{base}{quote}"}
        header, raw_json = send_public_request(
            url=self.futures_api_url,
            url_path="/fapi/v1/ticker/price",
            payload=params,
        )
        self.update_weight(int(header["X-MBX-USED-WEIGHT-1M"]))
        if "price" in [*raw_json]:
            return Decimal(raw_json["price"])
        return Decimal(-1.0)

    def get_futures_prices(self) -> dict:
        self.check_weight()
        params: dict = {}
        header, raw_json = send_public_request(
            url=self.futures_api_url,
            url_path="/fapi/v1/ticker/price",
            payload=params,
        )
        prices = {}
        self.update_weight(int(header["X-MBX-USED-WEIGHT-1M"]))
        if len(raw_json) > 0:
            for pair in raw_json:
                prices[pair["symbol"]] = Decimal(pair["price"])
        return prices

    def get_futures_kline(
        self,
        base: str,
        quote: str,
        start_time: int | None = None,
        end_time: int | None = None,
        interval: Intervals = Intervals.ONE_DAY,
        limit: int = 1000,
    ) -> list:
        self.check_weight()
        params: dict = {
            "symbol": f"{base}{quote}",
            "interval": interval,
            "limit": limit,
        }
        if start_time is not None:
            params["startTime"] = start_time
        if end_time is not None:
            params["endTime"] = end_time

        header, raw_json = send_public_request(
            url=self.futures_api_url, url_path="/fapi/v1/klines", payload=params
        )
        self.update_weight(int(header["X-MBX-USED-WEIGHT-1M"]))
        if len(raw_json) > 0:
            return [
                {
                    "timestamp": int(candle[0]),
                    "open": Decimal(candle[1]),
                    "high": Decimal(candle[2]),
                    "low": Decimal(candle[3]),
                    "close": Decimal(candle[4]),
                    "volume": Decimal(candle[5]),
                }
                for candle in raw_json
            ]
        return []

    def get_news(self) -> list:
        news_type = {
            48: "New crypto",
            49: "Latest news",
            93: "Latest activities",
            50: "New fiat",
            161: "Delisting",
            157: "Wallet",
            51: "API",
            128: "Airdrop",
        }
        header, raw_text = send_public_request(
            url=self.news_url, url_path="c-51?navId=51", json=False
        )
        to_find_start = '<script id="__APP_DATA" type="application/json">'
        to_find_end = "</script>"
        news: list = []
        text = find_in_string(
            string=raw_text,
            start_substring=to_find_start,
            end_substring=to_find_end,
            return_json=True,
        )
        if len(text) > 0:
            if "routeProps" in text:
                if "ce50" in text["routeProps"]:
                    if "catalogs" in text["routeProps"]["ce50"]:
                        for catalog in text["routeProps"]["ce50"]["catalogs"]:
                            catalog_id = catalog["catalogId"]
                            if "articles" in catalog:
                                for article in catalog["articles"]:
                                    headline = article["title"]
                                    code = article["code"]
                                    release = article["releaseDate"]
                                    news.append(
                                        {
                                            "headline": headline,
                                            "category": news_type[catalog_id],
                                            "hyperlink": f"{self.news_url}{code}",
                                            "news_time": release,
                                        }
                                    )
        return news
