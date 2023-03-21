from __future__ import annotations

import logging
from datetime import datetime
from decimal import Decimal

from futuresboard.core.utils import (
    find_all_occurrences_in_string,
    find_in_string,
    send_public_request,
)
from futuresboard.exchange.exchange import Exchange
from futuresboard.exchange.utils import Intervals

log = logging.getLogger(__name__)


class Okx(Exchange):
    def __init__(self):
        super().__init__()
        log.info("Okx initialised")

    exchange = "okx"
    news_url = "https://www.okx.com/support"
    futures_api_url = "https://www.okx.com"
    futures_trade_url = "https://www.okx.com/trade-futures/base-quote"
    max_weight = 600

    def get_futures_price(self, base: str, quote: str) -> Decimal:
        self.check_weight()
        params = {"instId": f"{base}-{quote}"}

        header, raw_json = send_public_request(
            url=self.futures_api_url,
            url_path="/api/v5/market/ticker",
            payload=params,
        )
        if "data" in [*raw_json]:
            if len(raw_json["data"]) > 0:
                if "last" in [*raw_json["data"][0]]:
                    return Decimal(raw_json["data"][0]["last"])
        return Decimal(-1.0)

    def get_futures_prices(self) -> list:
        self.check_weight()
        params = {"instType": "FUTURES"}
        header, raw_json = send_public_request(
            url=self.futures_api_url,
            url_path="/api/v5/market/tickers",
            payload=params,
        )
        if "data" in [*raw_json]:
            if len(raw_json["data"]) > 0:
                return [
                    {
                        "symbol": pair["instId"].replace("-", ""),
                        "price": Decimal(pair["last"]),
                    }
                    for pair in raw_json["data"]
                ]
        return []

    def get_instance_ids(self, base: str, quote: str) -> list:
        params = {"instType": "FUTURES"}
        header, raw_json = send_public_request(
            url=self.futures_api_url,
            url_path="/api/v5/market/tickers",
            payload=params,
        )
        if "data" in [*raw_json]:
            if len(raw_json["data"]) > 0:
                return [
                    pair["instId"]
                    for pair in raw_json["data"]
                    if base in pair["instId"] and quote in pair["instId"]
                ]
        return []

    def get_futures_kline(
        self,
        base: str,
        quote: str,
        start_time: int,
        end_time: int | None = None,
        interval: Intervals = Intervals.ONE_DAY,
        limit: int = 1440,
    ) -> list:
        self.check_weight()
        custom_intervals = {
            "1m": "1m",
            "5m": "5m",
            "15m": "15m",
            "1h": "1H",
            "4h": "4H",
            "1d": "1Dutc",
            "1w": "1Wutc",
        }
        instance_ids = self.get_instance_ids(base=base, quote=quote)
        log.info(instance_ids)
        if len(instance_ids) > 1:
            params: dict = {
                "instId": f"{instance_ids[1]}",
                "bar": custom_intervals[interval],
                "limit": limit,
            }
            if start_time is not None:
                params["before"] = start_time - 1
            if end_time is not None:
                params["after"] = end_time + 1

            header, raw_json = send_public_request(
                url=self.futures_api_url,
                url_path="/api/v5/market/candles",
                payload=params,
            )

            if "data" in [*raw_json]:
                if len(raw_json["data"]) > 0:
                    return [
                        {
                            "timestamp": int(candle[0]),
                            "open": Decimal(candle[1]),
                            "high": Decimal(candle[2]),
                            "low": Decimal(candle[3]),
                            "close": Decimal(candle[4]),
                            "volume": Decimal(candle[5]),
                        }
                        for candle in raw_json["data"]
                    ]
        return []

    def get_news(self) -> list:
        news_type = {
            "New-Token": "New crypto",
            "Latest-Announcements": "Latest news",
            "Latest-Event": "Latest activities",
            "Fiat-Gateway": "New fiat",
            "Spot-Margin-Trading": "Spot Crypto",
            "Derivatives": "Derivatives Crypto",
            "Deposit-Withdrawal-Suspension-Resumption": "Wallet",
            "Product-Updates": "Product",
            "API": "API",
            "Others": "Other",
        }
        header, raw_text = send_public_request(
            url=self.news_url,
            url_path="/hc/en-us/categories/115000275131-Announcements",
            json=False,
        )
        to_find_start = '<section class="section">'
        to_find_end = "</section>"
        news: list = []
        sections = find_all_occurrences_in_string(
            string=raw_text, start_substring=to_find_start, end_substring=to_find_end
        )
        to_find_start = 'href="'
        to_find_end = '"'
        for section in sections:
            section_link = find_in_string(
                string=section, start_substring=to_find_start, end_substring=to_find_end
            )
            if len(section_link) > 0:
                section_name = find_in_string(
                    string=section_link, start_substring="/hc/en-us/sections/"
                )
                section_name = find_in_string(string=section_name, start_substring="-")
                section_name = section_name.strip()
                if section_name in [
                    "OKB-Buy-back-Burn",
                    "Introduction-to-Digital-Assets",
                    "OKX-Pool-Announcement",
                    "OKX-Broker",
                    "OKC",
                    "P2P-Trading",
                ]:
                    continue
                header, raw_text = send_public_request(
                    url=self.news_url, url_path=f"{section_link}", json=False
                )
                articles = find_all_occurrences_in_string(
                    string=raw_text,
                    start_substring='<li class="article-list-item',
                    end_substring="</li>",
                )
                for article in articles:
                    article_link = find_in_string(
                        string=article,
                        start_substring=to_find_start,
                        end_substring=to_find_end,
                    )
                    header, raw_text = send_public_request(
                        url=self.news_url, url_path=f"{article_link}", json=False
                    )
                    title = find_in_string(
                        string=raw_text, start_substring="<h1", end_substring="</h1>"
                    )
                    title = find_in_string(string=title, start_substring=">")
                    title = title.strip()
                    release = find_in_string(
                        string=raw_text,
                        start_substring='<time datetime="',
                        end_substring='"',
                    )
                    release = datetime.strptime(release, "%Y-%m-%dT%H:%M:%SZ")
                    release = int(release.timestamp() * 1000)
                    news.append(
                        {
                            "headline": title,
                            "category": news_type[section_name],
                            "hyperlink": f"{self.news_url}{article_link}",
                            "news_time": release,
                        }
                    )
        return news
