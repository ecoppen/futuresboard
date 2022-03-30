from __future__ import annotations

import csv
import os
from datetime import date
from datetime import datetime
from datetime import timedelta
from typing import Any

import requests
from flask import Blueprint
from flask import redirect
from flask import render_template
from flask import request
from flask.helpers import url_for
from flask import current_app
from typing_extensions import TypedDict

from futuresboard import db

app = Blueprint("main", __name__)


class CoinsTotals(TypedDict):
    active: int
    inactive: int
    buys_long: int
    sells_long: int
    pbr_long: int
    buys_short: int
    sells_short: int
    pbr_short: int


class Coins(TypedDict):
    active: dict[str, tuple[int, int, int]]
    inactive: list[str]
    totals: CoinsTotals
    warning: bool


class History(TypedDict):
    columns: list[dict[str, Any]]


class Projections(TypedDict):
    dates: list[str]
    proj: dict[float, list[float]]
    pcustom: list[float]
    pcustom_value: float


remove_incomeTypes = ["TRANSFER", "COIN_SWAP_DEPOSIT", "COIN_SWAP_WITHDRAW"]


def zero_value(x):
    if x is None:
        return 0
    else:
        return x


def format_dp(value, dp=2):
    return "{:.{}f}".format(value, dp)


def calc_pbr(volume, price, side, balance):
    if price > 0.0:
        if side == "SHORT":
            return abs(volume * price) / balance
        elif side == "LONG":
            return abs(volume * price) / balance
    return 0.0


def average_down_target(posprice, posqty, currentprice, targetprice):
    return (posqty * (posprice - targetprice)) / (targetprice - currentprice)


def get_coins():
    coins: Coins = {
        "active": {},
        "inactive": [],
        "totals": {"active": 0, "inactive": 0, "buys_long": 0, "sells_long": 0, "pbr_long": 0, "buys_short": 0, "sells_short": 0, "pbr_short": 0},
        "warning": False,
    }

    all_active_positions = db.query(
        "SELECT symbol, entryPrice, positionSide, positionAmt FROM positions WHERE ABS(positionAmt) > 0 ORDER BY symbol ASC"
    )

    all_symbols_with_pnl = db.query(
        'SELECT DISTINCT(symbol) FROM income WHERE asset <> "BNB" AND symbol <> "" AND incomeType NOT IN'
        + " ({0})".format(", ".join("?" for _ in remove_incomeTypes))
        + " ORDER BY symbol ASC",
        remove_incomeTypes,
    )

    balance = db.query("SELECT totalWalletBalance FROM account WHERE AID = 1", one=True)

    active_symbols = []
    pbr_long, pbr_short = 0.0, 0.0

    for position in all_active_positions:
        if position[0] not in active_symbols:
            coins["totals"]["active"] += 1
        active_symbols.append(position[0])

        buy_long, sell_long, buy_short, sell_short,  = 0, 0, 0, 0

        buyorders_long = db.query(
            'SELECT COUNT(OID) FROM orders WHERE symbol = ? AND side = "BUY" AND positionSide = "LONG"',
            [position[0]],
            one=True,
        )

        buyorders_short = db.query(
            'SELECT COUNT(OID) FROM orders WHERE symbol = ? AND side = "BUY" AND positionSide = "SHORT"',
            [position[0]],
            one=True,
        )

        sellorders_long = db.query(
            'SELECT COUNT(OID) FROM orders WHERE symbol = ? AND side = "SELL" AND positionSide = "LONG"',
            [position[0]],
            one=True,
        )

        sellorders_short = db.query(
            'SELECT COUNT(OID) FROM orders WHERE symbol = ? AND side = "SELL" AND positionSide = "SHORT"',
            [position[0]],
            one=True,
        )

        coins["active"][position[0]] = [buy_long, sell_long, pbr_long, buy_short, sell_short, pbr_short]
        if position[2] == 'LONG':
            pbr_long = round(calc_pbr(position[3], position[1], position[2], float(balance[0])), 2)
            pbr_short = 0.0
        if position[2] == 'SHORT':
            pbr_short = round(calc_pbr(position[3], position[1], position[2], float(balance[0])), 2)
            pbr_long = 0.0

        if buyorders_long is not None:
            buy_long = int(buyorders_long[0])
        if sellorders_long is not None:
            sell_long = int(sellorders_long[0])
        if buyorders_short is not None:
            buy_short = int(buyorders_short[0])
        if sellorders_short is not None:
            sell_short = int(sellorders_short[0])
        if buy_long == 0 and sell_long == 0 and buy_short == 0 and sell_short == 0:
            coins["warning"] = True

        coins["active"][position[0]][0] = buy_long
        coins["active"][position[0]][1] = sell_long
        coins["active"][position[0]][2] += pbr_long
        coins["active"][position[0]][3] = buy_short
        coins["active"][position[0]][4] = sell_short
        coins["active"][position[0]][5] += pbr_short
        coins["totals"]["buys_long"] += buy_long
        coins["totals"]["sells_long"] += sell_long
        coins["totals"]["pbr_long"] += pbr_long
        coins["totals"]["buys_short"] += buy_short
        coins["totals"]["sells_short"] += sell_short
        coins["totals"]["pbr_short"] += pbr_short
        coins["active"][position[0]][2] = round(coins["active"][position[0]][2],2)
        coins["active"][position[0]][5] = round(coins["active"][position[0]][5],2)

    for symbol in all_symbols_with_pnl:
        if symbol[0] not in active_symbols:
            coins["inactive"].append(symbol[0])
            coins["totals"]["inactive"] += 1
    
    coins["totals"]["pbr_long"] = format_dp(coins["totals"]["pbr_long"])
    coins["totals"]["pbr_short"] = format_dp(coins["totals"]["pbr_short"])
    return coins


def get_lastupdate():
    lastupdate = db.query("SELECT MAX(time) FROM orders", one=True)
    if lastupdate[0] is None:
        return "-"
    return datetime.fromtimestamp(lastupdate[0] / 1000.0).strftime("%Y-%m-%d %H:%M:%S")


def timeranges():
    today = date.today()
    yesterday_start = today - timedelta(days=1)

    this_week_start = today - timedelta(days=today.weekday())
    last_week_start = this_week_start - timedelta(days=7)
    last_week_end = this_week_start - timedelta(days=1)

    this_month_start = today.replace(day=1)
    last_month_start = (this_month_start - timedelta(days=1)).replace(day=1)
    last_month_end = this_month_start - timedelta(days=1)

    this_year_start = today.replace(day=1).replace(month=1)
    last_year_start = (this_year_start - timedelta(days=1)).replace(day=1).replace(month=1)
    last_year_end = this_year_start - timedelta(days=1)

    return [
        [today.strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d")],
        [yesterday_start.strftime("%Y-%m-%d"), yesterday_start.strftime("%Y-%m-%d")],
        [this_week_start.strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d")],
        [last_week_start.strftime("%Y-%m-%d"), last_week_end.strftime("%Y-%m-%d")],
        [this_month_start.strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d")],
        [last_month_start.strftime("%Y-%m-%d"), last_month_end.strftime("%Y-%m-%d")],
        [this_year_start.strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d")],
        [last_year_start.strftime("%Y-%m-%d"), last_year_end.strftime("%Y-%m-%d")],
        [last_year_start.strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d")],
    ]


@app.route("/", methods=["GET"])
def index_page():
    daterange = request.args.get("daterange")
    ranges = timeranges()

    if daterange is not None:
        daterange = daterange.split(" - ")
        if len(daterange) == 2:
            try:
                start = (
                    datetime.combine(
                        datetime.fromisoformat(daterange[0]), datetime.min.time()
                    ).timestamp()
                    * 1000
                )
                end = (
                    datetime.combine(
                        datetime.fromisoformat(daterange[1]), datetime.max.time()
                    ).timestamp()
                    * 1000
                )
                startdate, enddate = daterange[0], daterange[1]
                return redirect(url_for("main.dashboard_page", start=startdate, end=enddate))
            except Exception:
                pass

    todaystart = (
        datetime.combine(datetime.fromisoformat(ranges[0][0]), datetime.min.time()).timestamp()
        * 1000
    )
    todayend = (
        datetime.combine(datetime.fromisoformat(ranges[0][1]), datetime.max.time()).timestamp()
        * 1000
    )
    weekstart = (
        datetime.combine(datetime.fromisoformat(ranges[2][0]), datetime.min.time()).timestamp()
        * 1000
    )
    weekend = (
        datetime.combine(datetime.fromisoformat(ranges[2][1]), datetime.max.time()).timestamp()
        * 1000
    )
    monthstart = (
        datetime.combine(datetime.fromisoformat(ranges[4][0]), datetime.min.time()).timestamp()
        * 1000
    )
    monthend = (
        datetime.combine(datetime.fromisoformat(ranges[4][1]), datetime.max.time()).timestamp()
        * 1000
    )

    start = (
        datetime.combine(datetime.fromisoformat(ranges[2][0]), datetime.min.time()).timestamp()
        * 1000
    )
    end = (
        datetime.combine(datetime.fromisoformat(ranges[2][1]), datetime.max.time()).timestamp()
        * 1000
    )
    startdate, enddate = ranges[2][0], ranges[2][1]

    balance = db.query("SELECT totalWalletBalance FROM account WHERE AID = 1", one=True)
    total = db.query(
        'SELECT SUM(income) FROM income WHERE asset <> "BNB" AND incomeType NOT IN'
        + " ({0})".format(", ".join("?" for _ in remove_incomeTypes)),
        remove_incomeTypes,
        one=True,
    )
    today = db.query(
        'SELECT SUM(income) FROM income WHERE asset <> "BNB" AND incomeType NOT IN'
        + " ({0})".format(", ".join("?" for _ in remove_incomeTypes))
        + " AND time >= ? AND time <= ?",
        remove_incomeTypes + [todaystart, todayend],
        one=True,
    )
    week = db.query(
        'SELECT SUM(income) FROM income WHERE asset <> "BNB" AND incomeType NOT IN'
        + " ({0})".format(", ".join("?" for _ in remove_incomeTypes))
        + " AND time >= ? AND time <= ?",
        remove_incomeTypes + [weekstart, weekend],
        one=True,
    )
    month = db.query(
        'SELECT SUM(income) FROM income WHERE asset <> "BNB" AND incomeType NOT IN'
        + " ({0})".format(", ".join("?" for _ in remove_incomeTypes))
        + " AND time >= ? AND time <= ?",
        remove_incomeTypes + [monthstart, monthend],
        one=True,
    )

    unrealized = db.query("SELECT SUM(unrealizedProfit) FROM positions", one=True)

    all_fees = db.query(
        'SELECT SUM(income), asset FROM income WHERE incomeType ="COMMISSION" GROUP BY asset'
    )

    by_date = db.query(
        'SELECT DATE(time / 1000, "unixepoch") AS Date, SUM(income) AS inc FROM income WHERE asset <> "BNB" AND incomeType NOT IN'
        + " ({0})".format(", ".join("?" for _ in remove_incomeTypes))
        + " AND time >= ?  AND time <= ? GROUP BY Date",
        remove_incomeTypes + [start, end],
    )

    by_symbol = db.query(
        'SELECT SUM(income) AS inc, symbol FROM income WHERE asset <> "BNB" AND incomeType NOT IN'
        + " ({0})".format(", ".join("?" for _ in remove_incomeTypes))
        + " AND time >= ? AND time <= ? GROUP BY symbol ORDER BY inc DESC",
        remove_incomeTypes + [start, end],
    )

    fees = {"USDT": 0, "BNB": 0}

    balance = float(balance[0])

    temptotal: tuple[list[float], list[float]] = ([], [])
    profit_period = balance - zero_value(week[0])

    temp: tuple[list[float], list[float]] = ([], [])
    for each in by_date:
        temp[0].append(round(float(each[1]), 2))
        temp[1].append(each[0])
        temptotal[1].append(each[0])
        temptotal[0].append(round(profit_period + float(each[1]), 2))
        profit_period += float(each[1])
    by_date = temp
    total_by_date = temptotal

    temp = ([], [])
    for each in by_symbol:
        temp[0].append(each[1])
        temp[1].append(round(float(each[0]), 2))
    by_symbol = temp

    if balance == 0.0:
        percentages = ["-", "-", "-", "-"]
    else:
        percentages = [
            format_dp(zero_value(today[0]) / balance * 100),
            format_dp(zero_value(week[0]) / balance * 100),
            format_dp(zero_value(month[0]) / balance * 100),
            format_dp(zero_value(total[0]) / balance * 100),
        ]

    for row in all_fees:
        fees[row[1]] = format_dp(abs(zero_value(row[0])), 4)

    pnl = [format_dp(zero_value(unrealized[0])), format_dp(balance)]
    totals = [
        format_dp(zero_value(total[0])),
        format_dp(zero_value(today[0])),
        format_dp(zero_value(week[0])),
        format_dp(zero_value(month[0])),
        ranges[3],
        fees,
        percentages,
        pnl,
        datetime.now().strftime("%B"),
        zero_value(week[0]),
        len(by_symbol[0]),
    ]

    return render_template(
        "home.html",
        coin_list=get_coins(),
        totals=totals,
        data=[by_date, by_symbol, total_by_date],
        timeframe="week",
        lastupdate=get_lastupdate(),
        startdate=startdate,
        enddate=enddate,
        timeranges=ranges,
        custom=current_app.config["CUSTOM"],
    )


@app.route("/dashboard/<start>/<end>", methods=["GET"])
def dashboard_page(start, end):
    ranges = timeranges()
    daterange = request.args.get("daterange")

    if daterange is not None:
        daterange = daterange.split(" - ")
        if len(daterange) == 2:
            try:
                start = (
                    datetime.combine(
                        datetime.fromisoformat(daterange[0]), datetime.min.time()
                    ).timestamp()
                    * 1000
                )
                end = (
                    datetime.combine(
                        datetime.fromisoformat(daterange[1]), datetime.max.time()
                    ).timestamp()
                    * 1000
                )
                startdate, enddate = daterange[0], daterange[1]
                return redirect(url_for("main.dashboard_page", start=startdate, end=enddate))
            except Exception:
                return redirect(url_for("main.dashboard_page", start=start, end=end))

    try:
        startdate, enddate = start, end
        start = (
            datetime.combine(datetime.fromisoformat(start), datetime.min.time()).timestamp() * 1000
        )
        end = datetime.combine(datetime.fromisoformat(end), datetime.max.time()).timestamp() * 1000
    except Exception:
        startdate, enddate = ranges[2][0], ranges[2][1]
        return redirect(url_for("main.dashboard_page", start=startdate, end=enddate))

    todaystart = (
        datetime.combine(datetime.fromisoformat(ranges[0][0]), datetime.min.time()).timestamp()
        * 1000
    )
    todayend = (
        datetime.combine(datetime.fromisoformat(ranges[0][1]), datetime.max.time()).timestamp()
        * 1000
    )
    weekstart = (
        datetime.combine(datetime.fromisoformat(ranges[2][0]), datetime.min.time()).timestamp()
        * 1000
    )
    weekend = (
        datetime.combine(datetime.fromisoformat(ranges[2][1]), datetime.max.time()).timestamp()
        * 1000
    )
    monthstart = (
        datetime.combine(datetime.fromisoformat(ranges[4][0]), datetime.min.time()).timestamp()
        * 1000
    )
    monthend = (
        datetime.combine(datetime.fromisoformat(ranges[4][1]), datetime.max.time()).timestamp()
        * 1000
    )

    balance = db.query("SELECT totalWalletBalance FROM account WHERE AID = 1", one=True)
    total = db.query(
        'SELECT SUM(income) FROM income WHERE asset <> "BNB" AND incomeType NOT IN'
        + " ({0})".format(", ".join("?" for _ in remove_incomeTypes)),
        remove_incomeTypes,
        one=True,
    )

    today = db.query(
        'SELECT SUM(income) FROM income WHERE asset <> "BNB" AND incomeType NOT IN'
        + " ({0})".format(", ".join("?" for _ in remove_incomeTypes))
        + " AND time >= ? AND time <= ?",
        remove_incomeTypes + [todaystart, todayend],
        one=True,
    )
    week = db.query(
        'SELECT SUM(income) FROM income WHERE asset <> "BNB" AND incomeType NOT IN'
        + " ({0})".format(", ".join("?" for _ in remove_incomeTypes))
        + " AND time >= ? AND time <= ?",
        remove_incomeTypes + [weekstart, weekend],
        one=True,
    )
    month = db.query(
        'SELECT SUM(income) FROM income WHERE asset <> "BNB" AND incomeType NOT IN'
        + " ({0})".format(", ".join("?" for _ in remove_incomeTypes))
        + " AND time >= ? AND time <= ?",
        remove_incomeTypes + [monthstart, monthend],
        one=True,
    )

    unrealized = db.query("SELECT SUM(unrealizedProfit) FROM positions", one=True)

    all_fees = db.query(
        'SELECT SUM(income), asset FROM income WHERE incomeType ="COMMISSION" GROUP BY asset'
    )

    by_date = db.query(
        'SELECT DATE(time / 1000, "unixepoch") AS Date, SUM(income) AS inc FROM income WHERE asset <> "BNB" AND incomeType NOT IN'
        + " ({0})".format(", ".join("?" for _ in remove_incomeTypes))
        + " AND time >= ?  AND time <= ? GROUP BY Date",
        remove_incomeTypes + [start, end],
    )

    by_symbol = db.query(
        'SELECT SUM(income) AS inc, symbol FROM income WHERE asset <> "BNB" AND incomeType NOT IN'
        + " ({0})".format(", ".join("?" for _ in remove_incomeTypes))
        + " AND time >= ? AND time <= ? GROUP BY symbol ORDER BY inc DESC",
        remove_incomeTypes + [start, end],
    )

    fees = {"USDT": 0, "BNB": 0}

    balance = float(balance[0])

    temptotal: tuple[list[float], list[float]] = ([], [])

    customframe = db.query(
        'SELECT SUM(income) FROM income WHERE asset <> "BNB" AND incomeType <> "TRANSFER" AND incomeType NOT IN'
        + " ({0})".format(", ".join("?" for _ in remove_incomeTypes))
        + " AND time >= ? AND time <= ?",
        remove_incomeTypes + [start, end],
        one=True,
    )

    profit_period = balance - zero_value(customframe[0])

    temp: tuple[list[float], list[float]] = ([], [])
    for each in by_date:
        temp[0].append(round(float(each[1]), 2))
        temp[1].append(each[0])
        temptotal[1].append(each[0])
        temptotal[0].append(round(profit_period + float(each[1]), 2))
        profit_period += float(each[1])
    by_date = temp
    total_by_date = temptotal

    temp = ([], [])
    for each in by_symbol:
        temp[0].append(each[1])
        temp[1].append(round(float(each[0]), 2))
    by_symbol = temp

    if balance == 0.0:
        percentages = ["-", "-", "-", "-"]
    else:
        percentages = [
            format_dp(zero_value(today[0]) / balance * 100),
            format_dp(zero_value(week[0]) / balance * 100),
            format_dp(zero_value(month[0]) / balance * 100),
            format_dp(zero_value(total[0]) / balance * 100),
        ]

    for row in all_fees:
        fees[row[1]] = format_dp(abs(zero_value(row[0])), 4)
    pnl = [format_dp(zero_value(unrealized[0])), format_dp(balance)]
    totals = [
        format_dp(zero_value(total[0])),
        format_dp(zero_value(today[0])),
        format_dp(zero_value(week[0])),
        format_dp(zero_value(month[0])),
        ranges[3],
        fees,
        percentages,
        pnl,
        datetime.now().strftime("%B"),
        zero_value(customframe[0]),
        len(by_symbol[0]),
    ]
    return render_template(
        "home.html",
        coin_list=get_coins(),
        totals=totals,
        data=[by_date, by_symbol, total_by_date],
        lastupdate=get_lastupdate(),
        startdate=startdate,
        enddate=enddate,
        timeranges=ranges,
        custom=current_app.config["CUSTOM"],
    )


@app.route("/positions")
def positions_page():
    coins = get_coins()
    positions = {}

    try:
        response = requests.get("https://fapi.binance.com/fapi/v1/premiumIndex", timeout=2)
        markPrices: dict
        markPrices = {}
        if response:
            temp = response.json()
            for each in temp:
                markPrices[each["symbol"]] = float(each["markPrice"])
        else:
            markPrices = {}
    except Exception:
        markPrices = {}

    for coin in coins["active"]:

        allpositions = db.query(
            "SELECT * FROM positions WHERE symbol = ?",
            [coin],
        )
        allorders = db.query(
            "SELECT * FROM orders WHERE symbol = ? ORDER BY side, price, origQty",
            [coin],
        )

        temp = []
        for position in allpositions:
            position = list(position)
            position[4] = round(float(position[4]), 5)
            temp.append(position)
        allpositions = temp

        temp = []
        buys_long = []
        sells_long = []
        buys_short = []
        sells_short = []
        for order in allorders:
            order = list(order)
            order[7] = datetime.fromtimestamp(order[7] / 1000.0).strftime("%Y-%m-%d %H:%M:%S")
            if order[3] == "BUY" and order[4] == "LONG":
                buys_long.append(order[2])
            elif order[3] == "SELL" and order[4] == "LONG":
                sells_long.append(order[2])
            elif order[3] == "BUY" and order[4] == "SHORT":
                buys_short.append(order[2])
            elif order[3] == "SELL" and order[4] == "SHORT":
                sells_short.append(order[2])
            temp.append(order)
        allorders = temp
        stats = [len(buys_long), len(sells_long), len(buys_short), len(sells_short)]
        if stats[0] == 0:
            stats.append("-")
            stats.append("-")
        else:
            stats.append(sorted(buys_long)[-1])
            if coin in markPrices:
                stats.append(round(float(markPrices[coin]) - sorted(buys_long)[-1], 5))
            else:
                stats.append("-")
        if stats[1] == 0:
            stats.append("-")
            stats.append("-")
        else:
            stats.append(sorted(sells_long)[0])
            if coin in markPrices:
                stats.append(round(float(markPrices[coin]) - sorted(sells_long)[0], 5))
            else:
                stats.append("-")
        if stats[2] == 0:
            stats.append("-")
            stats.append("-")
        else:
            stats.append(sorted(buys_short)[-1])
            if coin in markPrices:
                stats.append(round(float(markPrices[coin]) - sorted(buys_short)[-1], 5))
            else:
                stats.append("-")
        if stats[3] == 0:
            stats.append("-")
            stats.append("-")
        else:
            stats.append(sorted(sells_short)[0])
            if coin in markPrices:
                stats.append(round(float(markPrices[coin]) - sorted(sells_short)[0], 5))
            else:
                stats.append("-")
        positions[coin] = [allpositions, allorders, stats]

    return render_template(
        "positions.html",
        coin_list=get_coins(),
        positions=positions,
        custom=current_app.config["CUSTOM"],
        markprices=markPrices,
    )


@app.route("/coins/<coin>", methods=["GET"])
def coin_page(coin):
    coins = get_coins()
    if coin not in coins["inactive"] and coin not in coins["active"]:
        return (
            render_template(
                "error.html",
                coin_list=get_coins(),
                custom=current_app.config["CUSTOM"],
            ),
            404,
        )

    daterange = request.args.get("daterange")
    ranges = timeranges()

    if daterange is not None:
        daterange = daterange.split(" - ")
        if len(daterange) == 2:
            try:
                (
                    datetime.combine(
                        datetime.fromisoformat(daterange[0]), datetime.min.time()
                    ).timestamp()
                    * 1000
                )
                (
                    datetime.combine(
                        datetime.fromisoformat(daterange[1]), datetime.max.time()
                    ).timestamp()
                    * 1000
                )
                startdate, enddate = daterange[0], daterange[1]
                return redirect(
                    url_for("main.coin_page_timeframe", coin=coin, start=startdate, end=enddate)
                )
            except Exception:
                pass

    balance = db.query("SELECT totalWalletBalance FROM account WHERE AID = 1", one=True)
    if balance[0] is None:
        totals = ["-", "-", "-", "-", "-", {"USDT": 0, "BNB": 0}, ["-", "-", "-", "-"]]
    else:

        todaystart = (
            datetime.combine(datetime.fromisoformat(ranges[0][0]), datetime.min.time()).timestamp()
            * 1000
        )
        todayend = (
            datetime.combine(datetime.fromisoformat(ranges[0][1]), datetime.max.time()).timestamp()
            * 1000
        )
        weekstart = (
            datetime.combine(datetime.fromisoformat(ranges[2][0]), datetime.min.time()).timestamp()
            * 1000
        )
        weekend = (
            datetime.combine(datetime.fromisoformat(ranges[2][1]), datetime.max.time()).timestamp()
            * 1000
        )
        monthstart = (
            datetime.combine(datetime.fromisoformat(ranges[4][0]), datetime.min.time()).timestamp()
            * 1000
        )
        monthend = (
            datetime.combine(datetime.fromisoformat(ranges[4][1]), datetime.max.time()).timestamp()
            * 1000
        )

        startdate, enddate = ranges[2][0], ranges[2][1]

        total = db.query(
            'SELECT SUM(income) FROM income WHERE asset <> "BNB" AND incomeType <> "TRANSFER" AND incomeType NOT IN'
            + " ({0})".format(", ".join("?" for _ in remove_incomeTypes))
            + " AND symbol = ?",
            remove_incomeTypes + [coin],
            one=True,
        )
        today = db.query(
            'SELECT SUM(income) FROM income WHERE asset <> "BNB" AND incomeType <> "TRANSFER" AND incomeType NOT IN'
            + " ({0})".format(", ".join("?" for _ in remove_incomeTypes))
            + " AND time >= ? AND time <= ? AND symbol = ?",
            remove_incomeTypes + [todaystart, todayend, coin],
            one=True,
        )
        week = db.query(
            'SELECT SUM(income) FROM income WHERE asset <> "BNB" AND incomeType <> "TRANSFER" AND incomeType NOT IN'
            + " ({0})".format(", ".join("?" for _ in remove_incomeTypes))
            + " AND time >= ? AND time <= ? AND symbol = ?",
            remove_incomeTypes + [weekstart, weekend, coin],
            one=True,
        )
        month = db.query(
            'SELECT SUM(income) FROM income WHERE asset <> "BNB" AND incomeType <> "TRANSFER" AND incomeType NOT IN'
            + " ({0})".format(", ".join("?" for _ in remove_incomeTypes))
            + " AND time >= ? AND time <= ? AND symbol = ?",
            remove_incomeTypes + [monthstart, monthend, coin],
            one=True,
        )

        result = db.query(
            'SELECT SUM(income), asset FROM income WHERE incomeType ="COMMISSION" AND symbol = ? GROUP BY asset',
            [coin],
        )
        unrealized = db.query(
            "SELECT SUM(unrealizedProfit) FROM positions WHERE symbol = ?",
            [coin],
            one=True,
        )
        allpositions = db.query(
            "SELECT * FROM positions WHERE symbol = ? AND entryPrice > 0",
            [coin],
        )
        allorders = db.query(
            "SELECT * FROM orders WHERE symbol = ? ORDER BY side, price, origQty",
            [coin],
        )

        temp = []
        for position in allpositions:
            position = list(position)
            position[4] = round(float(position[4]), 5)
            temp.append(position)
        allpositions = temp

        averagetargets = ["-", "-", "-", "-"]
        try:
            response = requests.get(
                "https://fapi.binance.com/fapi/v1/premiumIndex?symbol=" + coin, timeout=2
            )
            markPrice: float | str
            if response:
                markPrice = float(response.json()["markPrice"])
                averagetargets = [
                    round(
                        average_down_target(
                            allpositions[0][4], allpositions[0][6], markPrice, markPrice * 1.001
                        )
                    ),
                    round(
                        average_down_target(
                            allpositions[0][4], allpositions[0][6], markPrice, markPrice * 1.005
                        )
                    ),
                    round(
                        average_down_target(
                            allpositions[0][4], allpositions[0][6], markPrice, markPrice * 1.01
                        )
                    ),
                ]
            else:
                markPrice = "-"
        except Exception:
            markPrice = "-"

        sticks = {"15m": [], "1h": [], "4h": [], "1d": []}

        for timeframe in sticks:
            try:
                response = requests.get(
                    "https://fapi.binance.com/fapi/v1/klines?symbol="
                    + coin
                    + "&interval="
                    + timeframe
                    + "&limit=1000",
                    timeout=2,
                )
                if response:
                    timestamps = []
                    candles = []
                    for candle in response.json():
                        dateconvert = candle[0]
                        timestamps.append(dateconvert)
                        candles.append(
                            [
                                dateconvert,
                                candle[1],
                                candle[2],
                                candle[3],
                                candle[4],
                                candle[5],
                            ]
                        )
                    sticks[timeframe] = [timestamps, candles]
            except:
                pass

        temp = []
        for order in allorders:
            order = list(order)
            order[7] = datetime.fromtimestamp(order[7] / 1000.0).strftime("%Y-%m-%d %H:%M:%S")
            temp.append(order)
        allorders = temp

        fees = {"USDT": 0, "BNB": 0}
        balance = float(balance[0])
        if balance == 0.0:
            percentages = ["-", "-", "-", "-"]
        else:
            percentages = [
                format_dp(zero_value(today[0]) / balance * 100),
                format_dp(zero_value(week[0]) / balance * 100),
                format_dp(zero_value(month[0]) / balance * 100),
                format_dp(zero_value(total[0]) / balance * 100),
            ]
        for row in result:
            fees[row[1]] = format_dp(abs(zero_value(row[0])), 4)
        pnl = [format_dp(zero_value(unrealized[0])), format_dp(balance)]
        totals = [
            format_dp(zero_value(total[0])),
            format_dp(zero_value(today[0])),
            format_dp(zero_value(week[0])),
            format_dp(zero_value(month[0])),
            ranges[3],
            fees,
            percentages,
            pnl,
            datetime.now().strftime("%B"),
            zero_value(week[0]),
        ]
        by_date = db.query(
            'SELECT DATE(time / 1000, "unixepoch") AS Date, SUM(income) AS inc FROM income WHERE asset <> "BNB" AND incomeType NOT IN'
            + " ({0})".format(", ".join("?" for _ in remove_incomeTypes))
            + " AND time >= ? AND time <= ? AND symbol = ? GROUP BY Date",
            remove_incomeTypes + [weekstart, weekend, coin],
        )
        temp = [[], []]
        for each in by_date:
            temp[0].append(round(float(each[1]), 2))
            temp[1].append(each[0])
        by_date = temp

    return render_template(
        "coin.html",
        coin_list=get_coins(),
        coin=coin,
        totals=totals,
        summary=[],
        data=[by_date],
        orders=[allpositions, allorders],
        lastupdate=get_lastupdate(),
        markprice=markPrice,
        startdate=startdate,
        enddate=enddate,
        timeranges=ranges,
        custom=current_app.config["CUSTOM"],
        target=averagetargets,
        candlesticks=sticks,
    )


@app.route("/coins/<coin>/<start>/<end>")
def coin_page_timeframe(coin, start, end):
    coins = get_coins()
    if coin not in coins["inactive"] and coin not in coins["active"]:
        return (
            render_template(
                "error.html",
                coin_list=get_coins(),
                custom=current_app.config["CUSTOM"],
            ),
            404,
        )

    ranges = timeranges()
    daterange = request.args.get("daterange")

    if daterange is not None:
        daterange = daterange.split(" - ")
        if len(daterange) == 2:
            try:
                start = (
                    datetime.combine(
                        datetime.fromisoformat(daterange[0]), datetime.min.time()
                    ).timestamp()
                    * 1000
                )
                end = (
                    datetime.combine(
                        datetime.fromisoformat(daterange[1]), datetime.max.time()
                    ).timestamp()
                    * 1000
                )
                startdate, enddate = daterange[0], daterange[1]
                return redirect(
                    url_for("main.coin_page_timeframe", coin=coin, start=startdate, end=enddate)
                )
            except Exception:
                return redirect(
                    url_for("main.coin_page_timeframe", coin=coin, start=start, end=end)
                )

    try:
        startdate, enddate = start, end
        start = (
            datetime.combine(datetime.fromisoformat(start), datetime.min.time()).timestamp() * 1000
        )
        end = datetime.combine(datetime.fromisoformat(end), datetime.max.time()).timestamp() * 1000
    except Exception:
        startdate, enddate = ranges[2][0], ranges[2][1]
        return redirect(
            url_for("main.coin_page_timeframe", coin=coin, start=startdate, end=enddate)
        )

    todaystart = (
        datetime.combine(datetime.fromisoformat(ranges[0][0]), datetime.min.time()).timestamp()
        * 1000
    )
    todayend = (
        datetime.combine(datetime.fromisoformat(ranges[0][1]), datetime.max.time()).timestamp()
        * 1000
    )
    weekstart = (
        datetime.combine(datetime.fromisoformat(ranges[2][0]), datetime.min.time()).timestamp()
        * 1000
    )
    weekend = (
        datetime.combine(datetime.fromisoformat(ranges[2][1]), datetime.max.time()).timestamp()
        * 1000
    )
    monthstart = (
        datetime.combine(datetime.fromisoformat(ranges[4][0]), datetime.min.time()).timestamp()
        * 1000
    )
    monthend = (
        datetime.combine(datetime.fromisoformat(ranges[4][1]), datetime.max.time()).timestamp()
        * 1000
    )

    balance = db.query("SELECT totalWalletBalance FROM account WHERE AID = 1", one=True)
    if balance[0] is None:
        totals = ["-", "-", "-", "-", "-", {"USDT": 0, "BNB": 0}, ["-", "-", "-", "-"]]
    else:
        total = db.query(
            'SELECT SUM(income) FROM income WHERE asset <> "BNB" AND incomeType NOT IN'
            + " ({0})".format(", ".join("?" for _ in remove_incomeTypes))
            + " AND symbol = ?",
            remove_incomeTypes + [coin],
            one=True,
        )
        today = db.query(
            'SELECT SUM(income) FROM income WHERE asset <> "BNB" AND incomeType <> "TRANSFER" AND incomeType NOT IN'
            + " ({0})".format(", ".join("?" for _ in remove_incomeTypes))
            + " AND time >= ? AND time <= ? AND symbol = ?",
            remove_incomeTypes + [todaystart, todayend, coin],
            one=True,
        )
        week = db.query(
            'SELECT SUM(income) FROM income WHERE asset <> "BNB" AND incomeType <> "TRANSFER" AND incomeType NOT IN'
            + " ({0})".format(", ".join("?" for _ in remove_incomeTypes))
            + " AND time >= ? AND time <= ? AND symbol = ?",
            remove_incomeTypes + [weekstart, weekend, coin],
            one=True,
        )
        month = db.query(
            'SELECT SUM(income) FROM income WHERE asset <> "BNB" AND incomeType <> "TRANSFER" AND incomeType NOT IN'
            + " ({0})".format(", ".join("?" for _ in remove_incomeTypes))
            + " AND time >= ? AND time <= ? AND symbol = ?",
            remove_incomeTypes + [monthstart, monthend, coin],
            one=True,
        )
        result = db.query(
            'SELECT SUM(income), asset FROM income WHERE incomeType ="COMMISSION" AND symbol = ? GROUP BY asset',
            [coin],
        )
        unrealized = db.query(
            "SELECT SUM(unrealizedProfit) FROM positions WHERE symbol = ?",
            [coin],
            one=True,
        )
        allpositions = db.query(
            "SELECT * FROM positions WHERE symbol = ? AND entryPrice > 0",
            [coin],
        )
        allorders = db.query(
            "SELECT * FROM orders WHERE symbol = ? ORDER BY side, price, origQty",
            [coin],
        )

        temp = []
        for position in allpositions:
            position = list(position)
            position[4] = round(float(position[4]), 5)
            temp.append(position)
        allpositions = temp

        averagetargets = ["-", "-", "-", "-"]
        try:
            response = requests.get(
                "https://fapi.binance.com/fapi/v1/premiumIndex?symbol=" + coin, timeout=2
            )
            markPrice: float | str
            if response:
                markPrice = float(response.json()["markPrice"])
                averagetargets = [
                    round(
                        average_down_target(
                            allpositions[0][4], allpositions[0][6], markPrice, markPrice * 1.001
                        )
                    ),
                    round(
                        average_down_target(
                            allpositions[0][4], allpositions[0][6], markPrice, markPrice * 1.005
                        )
                    ),
                    round(
                        average_down_target(
                            allpositions[0][4], allpositions[0][6], markPrice, markPrice * 1.01
                        )
                    ),
                ]
            else:
                markPrice = "-"
        except Exception:
            markPrice = "-"

        sticks = {"15m": [], "1h": [], "4h": [], "1d": []}

        for timeframe in sticks:
            try:
                response = requests.get(
                    "https://fapi.binance.com/fapi/v1/klines?symbol="
                    + coin
                    + "&interval="
                    + timeframe
                    + "&limit=1000",
                    timeout=2,
                )
                if response:
                    timestamps = []
                    candles = []
                    for candle in response.json():
                        dateconvert = candle[0]
                        timestamps.append(dateconvert)
                        candles.append(
                            [
                                dateconvert,
                                candle[1],
                                candle[2],
                                candle[3],
                                candle[4],
                                candle[5],
                            ]
                        )
                    sticks[timeframe] = [timestamps, candles]
            except:
                pass

        temp = []
        for order in allorders:
            order = list(order)
            order[7] = datetime.fromtimestamp(order[7] / 1000.0).strftime("%Y-%m-%d %H:%M:%S")
            temp.append(order)
        allorders = temp
        fees = {"USDT": 0, "BNB": 0}
        balance = float(balance[0])
        if balance == 0.0:
            percentages = ["-", "-", "-", "-"]
        else:
            percentages = [
                format_dp(zero_value(today[0]) / balance * 100),
                format_dp(zero_value(week[0]) / balance * 100),
                format_dp(zero_value(month[0]) / balance * 100),
                format_dp(zero_value(total[0]) / balance * 100),
            ]
        for row in result:
            fees[row[1]] = format_dp(abs(zero_value(row[0])), 4)

        by_date = db.query(
            'SELECT DATE(time / 1000, "unixepoch") AS Date, SUM(income) AS inc FROM income WHERE asset <> "BNB" AND incomeType NOT IN'
            + " ({0})".format(", ".join("?" for _ in remove_incomeTypes))
            + " AND time >= ? AND time <= ? AND symbol = ? GROUP BY Date",
            remove_incomeTypes + [start, end, coin],
        )
        temp = [[], []]
        for each in by_date:
            temp[0].append(round(float(each[1]), 2))
            temp[1].append(each[0])
        by_date = temp

        pnl = [format_dp(zero_value(unrealized[0])), format_dp(balance)]

        customframe = db.query(
            'SELECT SUM(income) FROM income WHERE asset <> "BNB" AND incomeType NOT IN'
            + " ({0})".format(", ".join("?" for _ in remove_incomeTypes))
            + " AND time >= ? AND time <= ? AND symbol = ?",
            remove_incomeTypes + [start, end, coin],
            one=True,
        )

        totals = [
            format_dp(zero_value(total[0])),
            format_dp(zero_value(today[0])),
            format_dp(zero_value(week[0])),
            format_dp(zero_value(month[0])),
            ranges[3],
            fees,
            percentages,
            pnl,
            datetime.now().strftime("%B"),
            zero_value(customframe[0]),
        ]

    return render_template(
        "coin.html",
        coin_list=get_coins(),
        coin=coin,
        totals=totals,
        summary=[],
        data=[by_date],
        orders=[allpositions, allorders],
        lastupdate=get_lastupdate(),
        markprice=markPrice,
        startdate=startdate,
        enddate=enddate,
        timeranges=ranges,
        custom=current_app.config["CUSTOM"],
        target=averagetargets,
        candlesticks=sticks,
    )


@app.route("/history")
def history_page():
    ranges = timeranges()
    history: History = {"columns": []}

    for timeframe in ranges:
        start = (
            datetime.combine(datetime.fromisoformat(timeframe[0]), datetime.min.time()).timestamp()
            * 1000
        )
        end = (
            datetime.combine(datetime.fromisoformat(timeframe[1]), datetime.max.time()).timestamp()
            * 1000
        )
        incomesummary = db.query(
            "SELECT incomeType, COUNT(IID) FROM income WHERE time >= ? AND time <= ? GROUP BY incomeType",
            [start, end],
        )
        temp = timeframe[0] + "/" + timeframe[1]
        if temp not in history:
            history[temp] = {}  # type: ignore[misc]
            history[temp]["total"] = 0  # type: ignore[misc]
            history[temp]["start"] = timeframe[0]
            history[temp]["end"] = timeframe[1]

        for totals in incomesummary:
            history[temp][totals[0]] = int(totals[1])  # type: ignore[misc]
            history[temp]["total"] += int(totals[1])  # type: ignore[misc]
            if totals[0] not in history["columns"]:
                history["columns"].append(totals[0])
    for timeframe in ranges:
        temp = timeframe[0] + "/" + timeframe[1]
        for column in history["columns"]:
            if column not in history[temp]:  # type: ignore[misc]
                history[temp][column] = 0  # type: ignore[misc]

    history["columns"].sort()
    previous_files = []
    for file in os.listdir(os.path.join(app.root_path, "static", "csv")):
        if file.endswith(".csv"):
            previous_files.append("csv/" + file)

    return render_template(
        "history.html",
        coin_list=get_coins(),
        history=history,
        filename="-",
        files=previous_files,
        custom=current_app.config["CUSTOM"],
    )


@app.route("/history/<start>/<end>")
def history_page_timeframe(start, end):
    try:
        startdate, enddate = start, end
        start = (
            datetime.combine(datetime.fromisoformat(start), datetime.min.time()).timestamp() * 1000
        )
        end = datetime.combine(datetime.fromisoformat(end), datetime.max.time()).timestamp() * 1000
    except Exception:
        return redirect(url_for("main.history_page"))

    ranges = timeranges()

    history = db.query(
        "SELECT * FROM income WHERE time >= ? AND time <= ? ORDER BY time desc",
        [start, end],
    )

    history_temp = []
    for inc in history:
        inc = list(inc)
        inc[7] = datetime.fromtimestamp(inc[7] / 1000.0).strftime("%Y-%m-%d %H:%M:%S")
        history_temp.append(inc)
    history = history_temp

    filename = (
        datetime.now().strftime("%Y-%m-%dT%H%M%S") + "_income_" + startdate + "_" + enddate + ".csv"
    )

    with open(os.path.join(app.root_path, "static", "csv", filename), "w", newline="") as csvfile:
        spamwriter = csv.writer(csvfile, delimiter=",")
        spamwriter.writerow(
            [
                "sqliteID",
                "TransactionId",
                "Symbol",
                "IncomeType",
                "Income",
                "Asset",
                "Info",
                "Time",
                "TradeId",
            ]
        )
        spamwriter.writerows(history)

    history = {"columns": []}

    temp: tuple[str, str]
    for timeframe in ranges:
        start = (
            datetime.combine(datetime.fromisoformat(timeframe[0]), datetime.min.time()).timestamp()
            * 1000
        )
        end = (
            datetime.combine(datetime.fromisoformat(timeframe[1]), datetime.max.time()).timestamp()
            * 1000
        )
        incomesummary = db.query(
            "SELECT incomeType, COUNT(IID) FROM income WHERE time >= ? AND time <= ? GROUP BY incomeType",
            [start, end],
        )
        temp = timeframe[0] + "/" + timeframe[1]
        if temp not in history:
            history[temp] = {}
            history[temp]["total"] = 0
            history[temp]["start"] = timeframe[0]
            history[temp]["end"] = timeframe[1]

        for totals in incomesummary:
            history[temp][totals[0]] = int(totals[1])
            history[temp]["total"] += int(totals[1])
            if totals[0] not in history["columns"]:
                history["columns"].append(totals[0])
    for timeframe in ranges:
        temp = timeframe[0] + "/" + timeframe[1]
        for column in history["columns"]:
            if column not in history[temp]:
                history[temp][column] = 0

    history["columns"].sort()

    filename = "csv/" + filename

    previous_files = []
    for file in os.listdir(os.path.join(app.root_path, "static", "csv")):
        if file.endswith(".csv"):
            previous_files.append("csv/" + file)

    return render_template(
        "history.html",
        coin_list=get_coins(),
        history=history,
        fname=filename,
        files=previous_files,
        custom=current_app.config["CUSTOM"],
    )


@app.route("/projection")
def projection_page():
    balance = db.query("SELECT totalWalletBalance FROM account WHERE AID = 1", one=True)
    projections: Projections = {
        "dates": [],
        "proj": {},
        "pcustom": [],
        "pcustom_value": 0.0,
    }
    if balance[0] is not None:

        ranges = timeranges()

        todayend = (
            datetime.combine(datetime.fromisoformat(ranges[0][1]), datetime.max.time()).timestamp()
            * 1000
        )
        minus_7_start = (
            datetime.combine(
                datetime.fromisoformat((date.today() - timedelta(days=7)).strftime("%Y-%m-%d")),
                datetime.max.time(),
            ).timestamp()
            * 1000
        )

        week = db.query(
            'SELECT SUM(income) FROM income WHERE asset <> "BNB" AND incomeType NOT IN'
            + " ({0})".format(", ".join("?" for _ in remove_incomeTypes))
            + " AND time >= ? AND time <= ?",
            remove_incomeTypes + [minus_7_start, todayend],
            one=True,
        )
        custom = round(week[0] / balance[0] * 100 / 7, 2)
        projections["pcustom_value"] = custom
        today = date.today()
        x = 1
        config_projections = current_app.config["CUSTOM"]["PROJECTIONS"]
        while x < 365:
            nextday = today + timedelta(days=x)
            projections["dates"].append(nextday.strftime("%Y-%m-%d"))

            for each_projection in config_projections:
                if each_projection not in projections["proj"]:
                    projections["proj"][each_projection] = []

                if len(projections["proj"][each_projection]) < 1:
                    newbalance = balance[0]
                    projections["proj"][each_projection].append(newbalance)
                else:
                    newbalance = projections["proj"][each_projection][-1]

                projections["proj"][each_projection].append(newbalance * each_projection)

            if len(projections["pcustom"]) < 1:
                newbalance = balance[0]
            else:
                newbalance = projections["pcustom"][-1]

            projections["pcustom"].append(newbalance * (1 + (week[0] / balance[0]) / 7))

            x += 1

    return render_template(
        "projection.html",
        coin_list=get_coins(),
        data=projections,
        custom=current_app.config["CUSTOM"],
    )


@app.errorhandler(404)
def not_found(error):
    return (
        render_template(
            "error.html",
            coin_list=get_coins(),
            custom=current_app.config["CUSTOM"],
        ),
        404,
    )
