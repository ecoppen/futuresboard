from flask import Flask, render_template, request
import sqlite3
from flask import g
from datetime import datetime, date, timedelta

app = Flask(__name__)


def get_db():
    db = getattr(g, "_database", None)
    if db is None:
        db = g._database = sqlite3.connect(app.config["DATABASE"])
    return db


@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, "_database", None)
    if db is not None:
        db.close()


def query_db(query, args=(), one=False):
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv


def get_coins():
    result = query_db(
        'SELECT DISTINCT(symbol) FROM income WHERE incomeType ="REALIZED_PNL" AND symbol <> "" ORDER BY symbol ASC'
    )
    coins = []
    for row in result:
        coins.append(row[0])
    return coins


def zero_value(x):
    if x is None:
        return 0
    else:
        return x


def timeranges():
    today = date.today()
    midnight_today = datetime.combine(today, datetime.min.time())
    midnight_7days = midnight_today - timedelta(days=7)
    midnight_quarter = midnight_today - timedelta(days=3 * 30)
    midnight_start = midnight_today - timedelta(days=3 * 365)
    start_of_month = datetime.combine(today.replace(day=1), datetime.min.time())
    start_of_year = datetime.combine(
        today.replace(day=1).replace(month=1), datetime.min.time()
    )
    return [
        midnight_today.timestamp() * 1000,
        midnight_7days.timestamp() * 1000,
        start_of_month.timestamp() * 1000,
        datetime.now().strftime("%B"),
        midnight_quarter.timestamp() * 1000,
        start_of_year.timestamp() * 1000,
        midnight_start.timestamp() * 1000,
    ]


@app.route("/")
def index_page():
    ranges = timeranges()
    balance = query_db("SELECT totalWalletBalance FROM account WHERE AID = 1", one=True)
    total = query_db(
        'SELECT SUM(income) FROM income WHERE incomeType ="REALIZED_PNL"', one=True
    )
    today = query_db(
        'SELECT SUM(income) FROM income WHERE incomeType ="REALIZED_PNL" AND time >= ?',
        [ranges[0]],
        one=True,
    )
    week = query_db(
        'SELECT SUM(income) FROM income WHERE incomeType ="REALIZED_PNL" AND time >= ?',
        [ranges[1]],
        one=True,
    )
    month = query_db(
        'SELECT SUM(income) FROM income WHERE incomeType ="REALIZED_PNL" AND time >= ?',
        [ranges[2]],
        one=True,
    )

    unrealized = query_db("SELECT SUM(unrealizedProfit) FROM positions", one=True)
    lastupdate = query_db("SELECT time FROM orders ORDER BY time DESC LIMIT 0, 1", one=True)
    if lastupdate is None:
        lastupdate = "-"
    else:
        lastupdate = datetime.fromtimestamp(lastupdate[0] / 1000.0).strftime(
                "%Y-%m-%d %H:%M:%S"
            )

    all_fees = query_db(
        'SELECT SUM(income), asset FROM income WHERE incomeType ="COMMISSION" GROUP BY asset'
    )

    by_date = query_db(
        'SELECT DATE(time / 1000, "unixepoch") AS Date, SUM(income) AS inc FROM income WHERE incomeType ="REALIZED_PNL" AND time >= ? GROUP BY Date',
        [ranges[1]],
    )

    by_symbol = query_db(
        'SELECT SUM(income) AS inc, symbol FROM income WHERE incomeType ="REALIZED_PNL" AND time >= ? GROUP BY symbol ORDER BY inc DESC',
        [ranges[1]],
    )

    fees = {"USDT": 0, "BNB": 0}

    temp = [[], []]
    for each in by_date:
        temp[0].append(round(float(each[1]),2))
        temp[1].append(each[0])
    by_date = temp

    temp = [[], []]
    for each in by_symbol:
        temp[0].append(each[1])
        temp[1].append(round(float(each[0]),2))
    by_symbol = temp

    balance = float(balance[0])
    percentages = [
        round(zero_value(today[0]) / balance * 100, 2),
        round(zero_value(week[0]) / balance * 100, 2),
        round(zero_value(month[0]) / balance * 100, 2),
        round(zero_value(total[0]) / balance * 100, 2),
    ]
    for row in all_fees:
        fees[row[1]] = abs(round(zero_value(row[0]), 4))

    pnl = [round(zero_value(unrealized[0]), 2), round(balance, 2)]
    totals = [
        round(zero_value(total[0]), 2),
        round(zero_value(today[0]), 2),
        round(zero_value(week[0]), 2),
        round(zero_value(month[0]), 2),
        ranges[3],
        fees,
        percentages,
        pnl,
    ]
    return render_template(
        "home.html",
        coin_list=get_coins(),
        totals=totals,
        data=[by_date, by_symbol],
        timeframe="week",
        lastupdate=lastupdate,
    )


@app.route("/dashboard/<timeframe>")
def dashboard(timeframe):
    if timeframe not in ["today", "week", "month", "quarter", "year", "all"]:
        return render_template("error.html"), 404

    ranges = timeranges()
    times = {"today": 0, "week": 1, "month": 2, "quarter": 4, "year": 5, "all": 6}
    balance = query_db("SELECT totalWalletBalance FROM account WHERE AID = 1", one=True)
    total = query_db(
        'SELECT SUM(income) FROM income WHERE incomeType ="REALIZED_PNL"', one=True
    )
    today = query_db(
        'SELECT SUM(income) FROM income WHERE incomeType ="REALIZED_PNL" AND time >= ?',
        [ranges[0]],
        one=True,
    )
    week = query_db(
        'SELECT SUM(income) FROM income WHERE incomeType ="REALIZED_PNL" AND time >= ?',
        [ranges[1]],
        one=True,
    )
    month = query_db(
        'SELECT SUM(income) FROM income WHERE incomeType ="REALIZED_PNL" AND time >= ?',
        [ranges[2]],
        one=True,
    )

    unrealized = query_db("SELECT SUM(unrealizedProfit) FROM positions", one=True)
    lastupdate = query_db("SELECT time FROM orders ORDER BY time DESC LIMIT 0, 1", one=True)

    all_fees = query_db(
        'SELECT SUM(income), asset FROM income WHERE incomeType ="COMMISSION" GROUP BY asset'
    )

    by_date = query_db(
        'SELECT DATE(time / 1000, "unixepoch") AS Date, SUM(income) AS inc FROM income WHERE incomeType ="REALIZED_PNL" AND time >= ? GROUP BY Date',
        [ranges[times[timeframe]]],
    )

    by_symbol = query_db(
        'SELECT SUM(income) AS inc, symbol FROM income WHERE incomeType ="REALIZED_PNL" AND time >= ? GROUP BY symbol ORDER BY inc DESC',
        [ranges[times[timeframe]]],
    )

    if lastupdate is None:
        lastupdate = "-"
    else:
        lastupdate = datetime.fromtimestamp(lastupdate[0] / 1000.0).strftime(
                "%Y-%m-%d %H:%M:%S"
            )

    fees = {"USDT": 0, "BNB": 0}

    temp = [[], []]
    for each in by_date:
        temp[0].append(round(float(each[1]),2))
        temp[1].append(each[0])
    by_date = temp

    temp = [[], []]
    for each in by_symbol:
        temp[0].append(each[1])
        temp[1].append(round(float(each[0]),2))
    by_symbol = temp

    balance = float(balance[0])
    percentages = [
        round(zero_value(today[0]) / balance * 100, 2),
        round(zero_value(week[0]) / balance * 100, 2),
        round(zero_value(month[0]) / balance * 100, 2),
        round(zero_value(total[0]) / balance * 100, 2),
    ]
    for row in all_fees:
        fees[row[1]] = abs(round(zero_value(row[0]), 4))
    pnl = [round(zero_value(unrealized[0]), 2), round(balance, 2)]
    totals = [
        round(zero_value(total[0]), 2),
        round(zero_value(today[0]), 2),
        round(zero_value(week[0]), 2),
        round(zero_value(month[0]), 2),
        ranges[3],
        fees,
        percentages,
        pnl,
    ]
    return render_template(
        "home.html",
        coin_list=get_coins(),
        totals=totals,
        timeframe=timeframe,
        data=[by_date, by_symbol],
        lastupdate = lastupdate,
    )


@app.route("/coins/")
def list_all_coins():
    # show the selected coin stats
    return render_template(
        "showall.html", coin_list=get_coins(), metric="coins", showall=get_coins()
    )


@app.route("/coins/<coin>")
def show_individual_coin(coin):
    # show the selected coin stats
    if coin not in get_coins():
        return render_template("error.html"), 404

    ranges = timeranges()
    balance = query_db("SELECT totalWalletBalance FROM account WHERE AID = 1", one=True)
    if balance[0] is None:
        totals = ["-", "-", "-", "-", "-", {"USDT": 0, "BNB": 0}, ["-", "-", "-", "-"]]
    else:
        total = query_db(
            'SELECT SUM(income) FROM income WHERE incomeType ="REALIZED_PNL" AND symbol = ?',
            [coin],
            one=True,
        )
        today = query_db(
            'SELECT SUM(income) FROM income WHERE incomeType ="REALIZED_PNL" AND time >= ? AND symbol = ?',
            [ranges[0], coin],
            one=True,
        )
        week = query_db(
            'SELECT SUM(income) FROM income WHERE incomeType ="REALIZED_PNL" AND time >= ? AND symbol = ?',
            [ranges[1], coin],
            one=True,
        )
        month = query_db(
            'SELECT SUM(income) FROM income WHERE incomeType ="REALIZED_PNL" AND time >= ? AND symbol = ?',
            [ranges[2], coin],
            one=True,
        )
        result = query_db(
            'SELECT SUM(income), asset FROM income WHERE incomeType ="COMMISSION" AND symbol = ? GROUP BY asset',
            [coin],
        )
        unrealized = query_db(
            "SELECT SUM(unrealizedProfit) FROM positions WHERE symbol = ?",
            [coin],
            one=True,
        )
        allpositions = query_db(
            "SELECT * FROM positions WHERE symbol = ?",
            [coin],
        )
        allorders = query_db(
            "SELECT * FROM orders WHERE symbol = ? ORDER BY side, price, origQty",
            [coin],
        )

        lastupdate = query_db("SELECT time FROM orders ORDER BY time DESC LIMIT 0, 1", one=True)
        if lastupdate is None:
            lastupdate = "-"
        else:
            lastupdate = datetime.fromtimestamp(lastupdate[0] / 1000.0).strftime(
                    "%Y-%m-%d %H:%M:%S"
                )

        temp = []
        for order in allorders:
            order = list(order)
            order[7] = datetime.fromtimestamp(order[7] / 1000.0).strftime(
                "%Y-%m-%d %H:%M:%S"
            )
            temp.append(order)
        allorders = temp

        fees = {"USDT": 0, "BNB": 0}
        balance = float(balance[0])
        percentages = [
            round(zero_value(today[0]) / balance * 100, 2),
            round(zero_value(week[0]) / balance * 100, 2),
            round(zero_value(month[0]) / balance * 100, 2),
            round(zero_value(total[0]) / balance * 100, 2),
        ]
        for row in result:
            fees[row[1]] = abs(round(zero_value(row[0]), 4))
        pnl = [round(zero_value(unrealized[0]), 2), round(balance, 2)]
        totals = [
            round(zero_value(total[0]), 2),
            round(zero_value(today[0]), 2),
            round(zero_value(week[0]), 2),
            round(zero_value(month[0]), 2),
            ranges[3],
            fees,
            percentages,
            pnl,
        ]
        by_date = query_db(
            'SELECT DATE(time / 1000, "unixepoch") AS Date, SUM(income) AS inc FROM income WHERE incomeType ="REALIZED_PNL" AND time >= ? AND symbol = ? GROUP BY Date',
            [ranges[1], coin],
        )
        temp = [[], []]
        for each in by_date:
            temp[0].append(round(each[1],2))
            temp[1].append(each[0])
        by_date = temp
    return render_template(
        "coin.html",
        coin_list=get_coins(),
        coin=coin,
        totals=totals,
        summary=[],
        timeframe="week",
        data=[by_date],
        orders=[allpositions, allorders],
        lastupdate=lastupdate,
    )


@app.route("/coins/<coin>/<timeframe>")
def show_individual_coin_timeframe(coin, timeframe):
    # show the selected coin stats
    if coin not in get_coins() or timeframe not in [
        "today",
        "week",
        "month",
        "quarter",
        "year",
        "all",
    ]:
        return render_template("error.html"), 404

    ranges = timeranges()
    times = {"today": 0, "week": 1, "month": 2, "quarter": 4, "year": 5, "all": 6}
    balance = query_db("SELECT totalWalletBalance FROM account WHERE AID = 1", one=True)
    if balance[0] is None:
        totals = ["-", "-", "-", "-", "-", {"USDT": 0, "BNB": 0}, ["-", "-", "-", "-"]]
    else:
        total = query_db(
            'SELECT SUM(income) FROM income WHERE incomeType ="REALIZED_PNL" AND symbol = ?',
            [coin],
            one=True,
        )
        today = query_db(
            'SELECT SUM(income) FROM income WHERE incomeType ="REALIZED_PNL" AND time >= ? AND symbol = ?',
            [ranges[0], coin],
            one=True,
        )
        week = query_db(
            'SELECT SUM(income) FROM income WHERE incomeType ="REALIZED_PNL" AND time >= ? AND symbol = ?',
            [ranges[1], coin],
            one=True,
        )
        month = query_db(
            'SELECT SUM(income) FROM income WHERE incomeType ="REALIZED_PNL" AND time >= ? AND symbol = ?',
            [ranges[2], coin],
            one=True,
        )
        result = query_db(
            'SELECT SUM(income), asset FROM income WHERE incomeType ="COMMISSION" AND symbol = ? GROUP BY asset',
            [coin],
        )
        unrealized = query_db(
            "SELECT SUM(unrealizedProfit) FROM positions WHERE symbol = ?",
            [coin],
            one=True,
        )
        allpositions = query_db(
            "SELECT * FROM positions WHERE symbol = ?",
            [coin],
        )
        allorders = query_db(
            "SELECT * FROM orders WHERE symbol = ? ORDER BY side, price, origQty",
            [coin],
        )

        lastupdate = query_db("SELECT time FROM orders ORDER BY time DESC LIMIT 0, 1", one=True)
        if lastupdate is None:
            lastupdate = "-"
        else:
            lastupdate = datetime.fromtimestamp(lastupdate[0] / 1000.0).strftime(
                    "%Y-%m-%d %H:%M:%S"
                    )
        temp = []
        for order in allorders:
            order = list(order)
            order[7] = datetime.fromtimestamp(order[7] / 1000.0).strftime(
                "%Y-%m-%d %H:%M:%S"
            )
            temp.append(order)
        allorders = temp
        fees = {"USDT": 0, "BNB": 0}
        balance = float(balance[0])
        percentages = [
            round(zero_value(today[0]) / balance * 100, 2),
            round(zero_value(week[0]) / balance * 100, 2),
            round(zero_value(month[0]) / balance * 100, 2),
            round(zero_value(total[0]) / balance * 100, 2),
        ]
        for row in result:
            fees[row[1]] = abs(round(zero_value(row[0]), 4))
        pnl = [round(zero_value(unrealized[0]), 2), round(balance, 2)]
        totals = [
            round(zero_value(total[0]), 2),
            round(zero_value(today[0]), 2),
            round(zero_value(week[0]), 2),
            round(zero_value(month[0]), 2),
            ranges[3],
            fees,
            percentages,
            pnl,
        ]

        by_date = query_db(
            'SELECT DATE(time / 1000, "unixepoch") AS Date, SUM(income) AS inc FROM income WHERE incomeType ="REALIZED_PNL" AND time >= ? AND symbol = ? GROUP BY Date',
            [ranges[times[timeframe]], coin],
        )
        temp = [[], []]
        for each in by_date:
            temp[0].append(round(each[1],2))
            temp[1].append(each[0])
        by_date = temp
    return render_template(
        "coin.html",
        coin_list=get_coins(),
        coin=coin,
        totals=totals,
        summary=[],
        timeframe=timeframe,
        data=[by_date],
        orders=[allpositions, allorders],
        lastupdate=lastupdate,
    )


@app.route("/orders/")
def list_all_orders():
    # show the selected coin stats
    return render_template(
        "showall.html", coin_list=get_coins(), metric="orders", showall=[]
    )


@app.errorhandler(404)
def not_found(error):
    return render_template("error.html"), 404
