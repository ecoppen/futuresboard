import logging
from datetime import date

import requests  # type: ignore

from futuresboard.core.utils import send_public_request
from futuresboard.models.database import Database

log = logging.getLogger(__name__)


class Scraper:
    def __init__(
        self, accounts: list, database: Database, exchanges: dict, news: list
    ) -> None:
        self.accounts = accounts
        self.database = database
        self.exchanges = exchanges
        self.news = news

        self.first_run = True
        self.today = date.today()

    def scrape(self) -> None:
        self.scrape_cycle()

    def scrape_cycle(self) -> None:
        if date.today() != self.today:
            self.first_run = True
            self.today = date.today()
        for exchange in ["binance", "bybit"]:  # self.news:
            news = self.exchanges[exchange].get_news()
            self.database.delete_then_update_news(exchange=exchange, data=news)
        for account in self.accounts:
            key_secret = {"key": account.api_key, "secret": account.api_secret}
            log.info(f"Starting scrape cycle for {account.name}")

            self.exchanges[account.exchange].check_api_permissions(account=key_secret)

            positions = self.exchanges[account.exchange].get_open_futures_positions(
                account=key_secret
            )
            self.database.delete_then_update_by_account_id(
                account_id=account.id, table="positions", data=positions
            )
            orders = self.exchanges[account.exchange].get_open_futures_orders(
                account=key_secret
            )
            self.database.delete_then_update_by_account_id(
                account_id=account.id, table="orders", data=orders
            )

            balances = self.exchanges[account.exchange].get_wallet_balance(
                account=key_secret
            )
            self.database.delete_then_update_by_account_id(
                account_id=account.id, table="wallet", data=balances
            )
            if self.first_run:
                pairs = self.exchanges[account.exchange].get_futures_prices()
                log.info(
                    f"Checking PnL for {len(pairs)} pairs listed on {account.exchange}"
                )
                pairs = [symbol["symbol"] for symbol in pairs]
            else:
                pairs = self.database.get_previously_traded_pairs(account_id=account.id)
                log.info(
                    f"Checking PnL for {len(pairs)} pairs that have previously been traded or in position"
                )
            if positions:
                pairs += [position["symbol"] for position in positions]
                pairs = list(set(pairs))
            for pair in pairs:
                start = self.database.get_latest_transaction(
                    account_id=account.id, symbol=pair
                )
                profit = self.exchanges[account.exchange].get_profit_and_loss(
                    account=key_secret, symbol=pair, start=start
                )

                if len(profit) > 0:
                    self.database.check_then_add_transaction(
                        account_id=account.id, data=profit
                    )
            log.info(f"Scrape cycle for {account.name} complete")
        if self.first_run:
            self.first_run = False
