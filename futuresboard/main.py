from __future__ import annotations

import logging
import os
import threading
import time
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from futuresboard.core.config import load_config
from futuresboard.exchange.factory import load_exchanges
from futuresboard.exchange.utils import Exchanges, Intervals, Markets
from futuresboard.models.database import Database
from futuresboard.scraper.scraper import Scraper

logs_file = Path(Path().resolve(), "log.txt")
logs_file.touch(exist_ok=True)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=os.environ.get("LOGLEVEL", "INFO"),
    handlers=[logging.FileHandler(logs_file), logging.StreamHandler()],
)

log = logging.getLogger(__name__)
log.info("futuresboard started")

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
app.add_middleware(GZipMiddleware)
templates = Jinja2Templates(directory="templates")

exchanges = load_exchanges()
config_file = Path(Path().resolve(), "config", "config.json")
config = load_config(path=config_file)

database = Database(config=config.database)
accounts = database.add_get_account_ids(accounts=config.accounts)

scraper = Scraper(accounts=accounts, database=database, exchanges=exchanges)


@app.get("/getprice")
def get_price(
    exchange: Exchanges,
    market: Markets,
    base: str,
    quote: str,
):
    if market == Markets.FUTURES.value:
        return exchanges[exchange].get_futures_price(
            base=base.upper(), quote=quote.upper()
        )

    return {"error": "not implemented yet"}


@app.get("/getprices")
def get_prices(
    exchange: Exchanges,
    market: Markets,
):
    if market == Markets.FUTURES.value:
        return exchanges[exchange].get_futures_prices()
    return {"error": "not implemented yet"}


@app.get("/getkline")
def get_kline(
    exchange: Exchanges,
    market: Markets,
    base: str,
    quote: str,
    interval: Intervals = Intervals.ONE_DAY,
    start_time: int | None = None,
    end_time: int | None = None,
    limit: int = 500,
):
    if market == Markets.FUTURES.value:
        return exchanges[exchange].get_futures_kline(
            base=base.upper(),
            quote=quote.upper(),
            interval=interval,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
        )
    else:
        return {"error": "not implemented yet"}


def _auto_scrape():
    while True:
        log.info("Auto scrape routines starting")
        scraper.scrape()
        log.info(
            f"Auto scrape routines terminated. Sleeping {config.scrape_interval} seconds..."
        )
        time.sleep(config.scrape_interval)


@app.on_event("startup")
def auto_scrape():
    thread = threading.Thread(target=_auto_scrape)
    thread.daemon = True
    thread.start()
