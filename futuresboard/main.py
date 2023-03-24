from __future__ import annotations

import logging
import os
import threading
import time
from datetime import date, datetime
from datetime import time as dt_time
from datetime import timedelta
from pathlib import Path

from fastapi import FastAPI
from fastapi import Path as fPath
from fastapi import Request
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from futuresboard.core.config import load_config
from futuresboard.core.utils import dt_to_ts
from futuresboard.exchange.factory import load_exchanges
from futuresboard.exchange.utils import Exchanges, Intervals, Markets
from futuresboard.models.database import Database
from futuresboard.scraper.scraper import Scraper

config_file = Path(Path().resolve(), "config", "config.json")
config = load_config(path=config_file)

logs_file = Path(Path().resolve(), "log.txt")
logs_file.touch(exist_ok=True)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=os.environ.get("LOGLEVEL", config.log_level.upper()),
    handlers=[logging.FileHandler(logs_file), logging.StreamHandler()],
)

log = logging.getLogger(__name__)
log.info("futuresboard started")

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
app.add_middleware(GZipMiddleware)
templates = Jinja2Templates(directory="templates")

exchanges = load_exchanges()

database = Database(config=config.database)
database.set_accounts_inactive()

accounts = database.add_get_account_ids(accounts=config.accounts)

scraper = Scraper(
    accounts=accounts, database=database, exchanges=exchanges, news=config.news_source
)


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def index(request: Request):
    accounts = database.get_accounts()
    recent_trades = database.get_trades(limit=10, sort=True, order="desc")
    page_data = {"dashboard_title": config.dashboard_name, "year": date.today().year}

    now = datetime.now()
    one_hour_ago = now - timedelta(hours=1)
    today_start = datetime.combine(datetime.today(), dt_time.min)
    all_time = now - timedelta(weeks=104)

    news: dict = {
        "1h": database.get_count_news_items(
            start=dt_to_ts(one_hour_ago), end=dt_to_ts(now)
        ),
        "1d": database.get_count_news_items(
            start=dt_to_ts(today_start), end=dt_to_ts(now)
        ),
        "all": database.get_count_news_items(
            start=dt_to_ts(all_time), end=dt_to_ts(now)
        ),
    }

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "page_data": page_data,
            "accounts": accounts,
            "recent_trades": recent_trades,
            "news": news,
        },
    )


@app.get("/account/{account_id}", response_class=HTMLResponse, include_in_schema=False)
def account(
    request: Request,
    account_id: int = fPath(title="The ID of the account to get", gt=0),
):
    account = database.get_account(account_id=account_id)
    if not account:
        return RedirectResponse("/")

    page_data = {"dashboard_title": config.dashboard_name, "year": date.today().year}
    return templates.TemplateResponse(
        "account.html", {"request": request, "page_data": page_data, "account": account}
    )


@app.get("/news", response_class=HTMLResponse, include_in_schema=False)
def news(
    request: Request, exchange: Exchanges | None = None, timeframe: str | None = None
):
    page_data = {"dashboard_title": config.dashboard_name, "year": date.today().year}
    return templates.TemplateResponse(
        "news.html", {"request": request, "page_data": page_data}
    )


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
