from __future__ import annotations

import logging
from datetime import datetime, timedelta
from decimal import Decimal

from futuresboard.core.utils import (
    find_in_string,
    send_public_request,
    send_signed_request,
)
from futuresboard.exchange.exchange import Exchange
from futuresboard.exchange.utils import Intervals

log = logging.getLogger(__name__)


class Bybit(Exchange):
    def __init__(self):
        super().__init__()
        log.info("Bybit initialised")

    exchange = "bybit"
    news_url = "https://announcements.bybit.com/en-US/"
    futures_api_url = "https://api.bybit.com"
    futures_trade_url = "https://www.bybit.com/trade/usdt/BASEQUOTE"
    max_weight = 1200

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

    def get_futures_prices(self) -> dict:
        self.check_weight()
        params: dict = {"category": "linear"}
        header, raw_json = send_public_request(
            url=self.futures_api_url,
            url_path="/v5/market/tickers",
            payload=params,
        )
        prices = {}
        if "result" in [*raw_json]:
            if "list" in [*raw_json["result"]]:
                for pair in raw_json["result"]["list"]:
                    prices[pair["symbol"]] = Decimal(pair["lastPrice"])
        return prices

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

    def check_api_permissions(self, account: dict) -> None:
        self.check_weight()
        responseHeader, responseJSON = send_signed_request(
            http_method="GET",
            url_path="/v5/user/query-api",
            exchange="bybit",
            base_url=self.futures_api_url,
            keys=account,
        )
        if "rate_limit_status" in responseJSON:
            self.update_weight(weight=self.max_weight)
        else:
            self.update_weight(weight=0)

        if "result" in responseJSON:
            if responseJSON["result"]["readOnly"] == 0:
                log.warning(
                    "futuresboard does not need write access, API permissions should be read only"
                )
            if "*" in responseJSON["result"]["ips"]:
                log.warning(
                    "Each API key/secret should be set to a fixed IP unless absolutely necessary"
                )

    def get_open_futures_positions(self, account: dict) -> list:
        params = {"category": "linear", "limit": 200, "settleCoin": "USDT"}
        position_sides = {"buy": "LONG", "sell": "SHORT"}

        positions = []
        complete = False
        pagination = None
        while not complete:
            self.check_weight()
            if pagination is not None:
                params["cursor"] = pagination
            responseHeader, responseJSON = send_signed_request(
                http_method="GET",
                url_path="/v5/position/list",
                payload=params,
                exchange="bybit",
                base_url=self.futures_api_url,
                keys=account,
            )
            if "rate_limit_status" in responseJSON:
                self.update_weight(weight=self.max_weight)
            else:
                self.update_weight(weight=0)

            if "result" in responseJSON:
                if "nextPageCursor" in responseJSON["result"]:
                    pagination = responseJSON["result"]["nextPageCursor"]
                    if len(pagination) == 0:
                        complete = True

                if "list" in responseJSON["result"]:
                    for position in responseJSON["result"]["list"]:
                        if float(position["size"]) > 0:
                            position_side = position_sides[position["side"].lower()]
                            liq_price = position["liqPrice"]
                            if liq_price == '':
                                log.warning("Warning: liquidation price is an empty string. Defaulting to 0.")
                                liq_price = Decimal(0)
                            else:
                                try:
                                    liq_price = Decimal(liq_price)
                                except Exception as e:
                                    log.warning(f"Error converting liquidation price to Decimal: {e}")
                                    liq_price = Decimal(0)
                            positions.append(
                                {
                                    "symbol": position["symbol"],
                                    "unrealised_profit": Decimal(position["unrealisedPnl"]),
                                    "leverage": Decimal(position["leverage"]),
                                    "entry_price": Decimal(position["avgPrice"]),
                                    "side": position_side,
                                    "amount": Decimal(position["size"]),
                                    "liquidation_price": liq_price,
                                }
                            )
                else:
                    break
            else:
                break

        return positions
    
    def get_open_futures_orders(self, account: dict) -> list:
        params = {"category": "linear", "limit": 50, "settleCoin": "USDT"}
        orders = []

        complete = False
        pagination = None
        while not complete:
            self.check_weight()
            if pagination is not None:
                params["cursor"] = pagination
            responseHeader, responseJSON = send_signed_request(
                http_method="GET",
                url_path="/v5/order/realtime",
                payload=params,
                exchange="bybit",
                base_url=self.futures_api_url,
                keys=account,
            )
            if "rate_limit_status" in responseJSON:
                self.update_weight(weight=self.max_weight)
            else:
                self.update_weight(weight=0)

            if "result" in responseJSON:
                if "nextPageCursor" in responseJSON["result"]:
                    pagination = responseJSON["result"]["nextPageCursor"]
                    if len(pagination) == 0:
                        complete = True

                if "list" in responseJSON["result"]:
                    for order in responseJSON["result"]["list"]:
                        order_side = order["side"].upper()

                        orders.append(
                            {
                                "quantity": Decimal(order["qty"]),
                                "symbol": order["symbol"],
                                "price": Decimal(order["price"]),
                                "side": order_side,
                                "status": order["orderStatus"],
                                "type": order["orderType"],
                                "created_time": order["createdTime"],
                                "updated_time": order["updatedTime"],
                            }
                        )

        return orders

    def get_wallet_balance(self, account: dict) -> list:
        self.check_weight()
        params = {"accountType": "contract"}
        balances = []

        responseHeader, responseJSON = send_signed_request(
            http_method="GET",
            url_path="/v5/account/wallet-balance",
            payload=params,
            exchange="bybit",
            base_url=self.futures_api_url,
            keys=account,
        )
        if "rate_limit_status" in responseJSON:
            self.update_weight(weight=self.max_weight)
        else:
            self.update_weight(weight=0)

        if "result" in responseJSON:
            if "list" in responseJSON["result"]:
                if len(responseJSON["result"]["list"]) > 0:
                    if "coin" in responseJSON["result"]["list"][0]:
                        for coin in responseJSON["result"]["list"][0]["coin"]:
                            balances.append(
                                {"coin": coin["coin"], "amount": coin["equity"]}
                            )
        return balances

    def get_profit_and_loss(
        self, account: dict, start: int, symbol: str | None = None
    ) -> list:
        two_years_ago = datetime.now() - timedelta(days=729)
        two_years_ago_timestamp = int(two_years_ago.timestamp() * 1000)

        if start < two_years_ago_timestamp:
            start = two_years_ago_timestamp

        params = {
            "category": "linear",
            "limit": 100,
            "startTime": start,
        }
        if symbol is not None:
            params["symbol"] = symbol

        closed_pnl = []

        complete = False
        pagination = None
        while not complete:
            self.check_weight()
            if pagination is not None:
                params["cursor"] = pagination
            responseHeader, responseJSON = send_signed_request(
                http_method="GET",
                url_path="/v5/position/closed-pnl",
                payload=params,
                exchange="bybit",
                base_url=self.futures_api_url,
                keys=account,
            )

            if "rate_limit_status" in responseJSON:
                self.update_weight(weight=self.max_weight)
            else:
                self.update_weight(weight=0)

            if "result" in responseJSON:
                if "nextPageCursor" in responseJSON["result"]:
                    pagination = responseJSON["result"]["nextPageCursor"]
                    if len(pagination) == 0:
                        complete = True

                if "list" in responseJSON["result"]:
                    for transaction in responseJSON["result"]["list"]:
                        closed_pnl.append(
                            {
                                "symbol": transaction["symbol"],
                                "order_id": transaction["orderId"],
                                "order_type": transaction["orderType"],
                                "exec_type": transaction["execType"],
                                "profit": Decimal(transaction["closedPnl"]),
                                "created_time": int(transaction["createdTime"]),
                                "updated_time": int(transaction["updatedTime"]),
                            }
                        )
            else:
                complete = True

        return closed_pnl

    def get_news(self) -> list:
        all_categories = [
            "new_crypto",
            "latest_activities",
            "latest_bybit_news",
            "product_updates",
            "new_fiat_listings",
            "maintenance_updates",
            "delistings",
            "other",
        ]
        news_type = {
            "new_crypto": "New crypto",
            "latest_bybit_news": "Latest news",
            "latest_activities": "Latest activities",
            "new_fiat_listings": "New fiat",
            "delistings": "Delisting",
            "product_updates": "Product",
            "maintenance_updates": "API",
            "other": "Other",
        }
        news: list = []
        for category in all_categories:
            params: dict = {"category": category, "page": 1}
            header, raw_text = send_public_request(
                url=self.news_url, payload=params, json=False
            )
            to_find_start = '<script id="__NEXT_DATA__" type="application/json">'
            to_find_end = "</script>"

            text = find_in_string(
                string=raw_text,
                start_substring=to_find_start,
                end_substring=to_find_end,
                return_json=True,
            )
            if len(text) > 0:
                if "props" in text:
                    if "pageProps" in text["props"]:
                        if "articleInitEntity" in text["props"]["pageProps"]:
                            if (
                                "list"
                                in text["props"]["pageProps"]["articleInitEntity"]
                            ):
                                for item in text["props"]["pageProps"][
                                    "articleInitEntity"
                                ]["list"]:
                                    headline = item["title"]
                                    release = item["date_timestamp"] * 1000
                                    code = item["url"]
                                    news.append(
                                        {
                                            "headline": headline,
                                            "category": news_type[category],
                                            "hyperlink": f"{self.news_url}{code}",
                                            "news_time": release,
                                        }
                                    )
        return news
