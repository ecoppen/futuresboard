import logging

import requests  # type: ignore

from futuresboard.core.utils import send_public_request
from futuresboard.models.database import Database

log = logging.getLogger(__name__)


class Scraper:
    def __init__(self, accounts: list, database: Database, exchanges: dict) -> None:
        self.accounts = accounts
        self.database = database
        self.exchanges = exchanges

    def scrape(self) -> None:
        self.scrape_cycle()

    def scrape_cycle(self) -> None:
        for account in self.accounts:
            key_secret = {"key": account.api_key, "secret": account.api_secret}
            log.info(f"Starting scrape cycle for {account.name}")
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
            log.info(f"Scrape cycle for {account.name} complete")
