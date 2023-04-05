from __future__ import annotations

import logging
import logging.handlers as handlers
import os
import threading
import time
from datetime import date, datetime
from datetime import time as dt_time
from datetime import timedelta
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi import Path as fPath
from fastapi import Request
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from futuresboard.core.config import load_config
from futuresboard.core.utils import dt_to_ts, timeranges
from futuresboard.exchange.factory import load_exchanges
from futuresboard.exchange.utils import Exchanges, Intervals, Markets
from futuresboard.models.database import Database
from futuresboard.scraper.scraper import Scraper

config_file = Path(Path().resolve(), "config", "config.json")
config = load_config(path=config_file)

logs_file = Path(Path().resolve(), "log.txt")
logs_file.touch(exist_ok=True)

log = logging.getLogger()
formatter = logging.Formatter(
    fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
rotatingHandler = handlers.RotatingFileHandler(
    "log.txt", maxBytes=5000000, backupCount=4
)
rotatingHandler.setFormatter(formatter)
log.setLevel(os.environ.get("LOGLEVEL", config.log_level.upper()))
log.addHandler(rotatingHandler)
streamHandler = logging.StreamHandler()
streamHandler.setFormatter(formatter)
log.addHandler(streamHandler)

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
    page_data = {
        "dashboard_title": config.dashboard_name,
        "year": date.today().year,
        "page": "",
    }

    now = datetime.now()
    one_hour_ago = now - timedelta(hours=1)
    today_start = datetime.combine(datetime.today(), dt_time.min)

    news: dict = {
        "1h": [
            database.get_count_news_items(start=dt_to_ts(one_hour_ago)),
            dt_to_ts(one_hour_ago),
        ],
        "1d": [
            database.get_count_news_items(start=dt_to_ts(today_start)),
            dt_to_ts(today_start),
        ],
        "all": [database.get_count_news_items(), 0],
    }

    navbar: dict[str, dict[str, Any]] = {
        "select": {"placeholder": "Select an account", "items": []}
    }

    for each_account in accounts["active"] + accounts["inactive"]:
        navbar["select"]["items"].append(
            {
                "item": f"{each_account['id']} - {each_account['name']} ({each_account['exchange']})",
                "selected": False,
                "account_id": each_account["id"],
            }
        )

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "page_data": page_data,
            "accounts": accounts,
            "recent_trades": recent_trades,
            "news": news,
            "navbar": navbar,
        },
    )


@app.get("/account_switch", include_in_schema=False)
async def account_switcher(id: int):
    account_check = database.get_account(account_id=id)
    if not account_check:
        return RedirectResponse("/")
    return RedirectResponse(f"/account/{id}")


@app.get("/account/{account_id}", response_class=HTMLResponse, include_in_schema=False)
def account(
    request: Request,
    account_id: int = fPath(title="The ID of the account to get", gt=0),
):
    accounts = database.get_accounts()
    account_check = database.get_account(account_id=account_id)
    if not account_check:
        return RedirectResponse("/")

    ranges = timeranges()

    wallet_balances = database.get_wallet_balances(account_id=account_id)
    wallet_key = ""
    if len(wallet_balances) == 1:
        wallet_key = next(iter(wallet_balances))
    else:
        keys = [*wallet_balances]
        last_traded = database.get_trades(account_id=account_id, limit=1)
        if len(last_traded) > 0:
            symbol = last_traded[0]["symbol"]
            for key in keys:
                if symbol.endswith(key):
                    wallet_key = key
                    break
        if wallet_key == "":
            wallet_key = next(iter(wallet_balances))

    data = {
        "profit_today": database.get_closed_profit(
            account_id=account_id,
            start=ranges["today"]["start_ts"],
            end=ranges["today"]["end_ts"],
        ),
        "profit_week": database.get_closed_profit(
            account_id=account_id,
            start=ranges["this_week"]["start_ts"],
            end=ranges["this_week"]["end_ts"],
        ),
        "profit_month": database.get_closed_profit(
            account_id=account_id,
            start=ranges["this_month"]["start_ts"],
            end=ranges["this_month"]["end_ts"],
        ),
        "total": database.get_closed_profit(account_id=account_id),
        "unrealised": database.get_unrealised_profit(account_id=account_id),
        "balance": wallet_balances[wallet_key],
        "quote": wallet_key,
    }
    if data["balance"] == 0:
        data["profit_percentages"] = {"today": 0, "week": 0, "month": 0, "total": 0}
    else:
        data["profit_percentages"] = {
            "today": data["profit_today"] / data["balance"] * 100,
            "week": data["profit_week"] / data["balance"] * 100,
            "month": data["profit_month"] / data["balance"] * 100,
            "total": data["total"] / data["balance"] * 100,
        }
    page_data = {
        "dashboard_title": config.dashboard_name,
        "year": date.today().year,
        "page": f"{account_check['name']} ({account_check['exchange']})",
    }
    navbar: dict[str, dict[str, Any]] = {
        "select": {"placeholder": "Select an account", "items": []}
    }

    for each_account in accounts["active"] + accounts["inactive"]:
        selected = False
        if account_id == each_account["id"]:
            selected = True
        navbar["select"]["items"].append(
            {
                "item": f"{each_account['id']} - {each_account['name']} ({each_account['exchange']})",
                "selected": selected,
                "account_id": each_account["id"],
            }
        )

    return templates.TemplateResponse(
        "account.html",
        {
            "request": request,
            "page_data": page_data,
            "account": account_check,
            "data": data,
            "navbar": navbar,
        },
    )


@app.get("/news", response_class=HTMLResponse, include_in_schema=False)
def news(
    request: Request,
    exchange: Exchanges | None = None,
    start: int | None = None,
    end: int | None = None,
):
    page_data = {
        "dashboard_title": config.dashboard_name,
        "year": date.today().year,
        "page": "news",
    }
    news = get_news(exchange=exchange, start=start, end=end)

    now = datetime.now()
    one_hour_ago = now - timedelta(hours=1)
    today_start = datetime.combine(datetime.today(), dt_time.min)

    navbar = {
        "buttons": {
            "1h": {
                "url": "news",
                "active": False,
                "news_params": True,
                "news_value": dt_to_ts(one_hour_ago),
            },
            "1d": {
                "url": "news",
                "active": False,
                "news_params": True,
                "news_value": dt_to_ts(today_start),
            },
            "all": {"url": "news", "active": False, "news_params": False},
        }
    }
    if start is None:
        navbar["buttons"]["all"]["active"] = True
    elif start == dt_to_ts(today_start):
        navbar["buttons"]["1d"]["active"] = True
    elif start == dt_to_ts(one_hour_ago):
        navbar["buttons"]["1h"]["active"] = True

    return templates.TemplateResponse(
        "news.html",
        {"request": request, "page_data": page_data, "news": news, "navbar": navbar},
    )


@app.get("/getnews")
def get_news(
    exchange: Exchanges | None = None, start: int | None = None, end: int | None = None
):
    return database.get_news_items(start=start, end=end, exchange=exchange)


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
