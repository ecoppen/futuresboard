from flask import Flask, render_template, request
import sqlite3
from flask import g
from datetime import datetime, date, timedelta
import requests
import csv
import os

app = Flask(__name__)


def zero_value(x):
    if x is None:
        return 0
    else:
        return x


def format_dp(value, dp=2):
    return "{:.{}f}".format(value, dp)

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

def calc_pbr(volume, price, side, balance):
    if price > 0.0:
        if side == "SHORT":
            return abs(volume / price) / balance
        elif side == "LONG":
            return abs(volume * price) / balance
    return 0.0

def get_coins():
    all_symbols_with_pnl = query_db(
        'SELECT DISTINCT(symbol) FROM income WHERE (incomeType = "REALIZED_PNL" OR incomeType = "FUNDING_FEE") AND symbol <> "" ORDER BY symbol ASC'
    )
    coins = {"active": {}, "inactive": [], "totals": {"active": 0, "inactive": 0, "buys":0, "sells":0, "pbr":0}}
    
    balance = query_db("SELECT totalWalletBalance FROM account WHERE AID = 1", one=True)
    
    for symbol in all_symbols_with_pnl:
        buyorders = query_db(
            'SELECT COUNT(OID) FROM orders WHERE symbol = ? AND side = "BUY"', [symbol[0]], one=True
        )
        sellorders = query_db(
            'SELECT COUNT(OID) FROM orders WHERE symbol = ? AND side = "SELL"',
            [symbol[0]],
            one=True,
        )
        
        if buyorders is None or sellorders is None:
            coins["inactive"].append(symbol[0])
            coins["totals"]["inactive"] += 1
        elif int(buyorders[0]) + int(sellorders[0]) == 0:
            coins["inactive"].append(symbol[0])
            coins["totals"]["inactive"] += 1
        else:
            allpositions = query_db(
                "SELECT entryPrice, positionSide, positionAmt FROM positions WHERE symbol = ? AND positionAmt > 0",
                [symbol[0]],
            )
                
            pbr = round(calc_pbr(allpositions[0][2],allpositions[0][0], allpositions[0][1], float(balance[0])),2)
            
            coins["active"][symbol[0]] = [int(buyorders[0]), int(sellorders[0]), pbr]
            coins["totals"]["active"] += 1
            coins["totals"]["buys"] += int(buyorders[0])
            coins["totals"]["sells"] += int(sellorders[0])
            coins["totals"]["pbr"] += pbr
    coins["totals"]["pbr"] = format_dp(coins["totals"]["pbr"])
    return coins


def get_lastupdate():
    lastupdate = query_db("SELECT MAX(time) FROM orders", one=True)
    if lastupdate is None:
        return "-"
    return datetime.fromtimestamp(lastupdate[0] / 1000.0).strftime("%Y-%m-%d %H:%M:%S")

def timeranges():
    today = date.today()
    midnight_today = datetime.combine(today, datetime.min.time())
    midnight_7days = midnight_today - timedelta(days=7)
    midnight_quarter = midnight_today - timedelta(days=3 * 30)
    midnight_start = midnight_today - timedelta(days=3 * 365)
    start_of_month = datetime.combine(today.replace(day=1), datetime.min.time())
    start_of_year = datetime.combine(today.replace(day=1).replace(month=1), datetime.min.time())
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
    total = query_db('SELECT SUM(income) FROM income WHERE incomeType = "REALIZED_PNL" OR incomeType = "FUNDING_FEE"', one=True)
    today = query_db(
        'SELECT SUM(income) FROM income WHERE (incomeType = "REALIZED_PNL" OR incomeType = "FUNDING_FEE") AND time >= ?',
        [ranges[0]],
        one=True,
    )
    week = query_db(
        'SELECT SUM(income) FROM income WHERE (incomeType = "REALIZED_PNL" OR incomeType = "FUNDING_FEE") AND time >= ?',
        [ranges[1]],
        one=True,
    )
    month = query_db(
        'SELECT SUM(income) FROM income WHERE (incomeType = "REALIZED_PNL" OR incomeType = "FUNDING_FEE") AND time >= ?',
        [ranges[2]],
        one=True,
    )

    unrealized = query_db("SELECT SUM(unrealizedProfit) FROM positions", one=True)

    all_fees = query_db(
        'SELECT SUM(income), asset FROM income WHERE incomeType ="COMMISSION" GROUP BY asset'
    )

    by_date = query_db(
        'SELECT DATE(time / 1000, "unixepoch") AS Date, SUM(income) AS inc FROM income WHERE (incomeType = "REALIZED_PNL" OR incomeType = "FUNDING_FEE") AND time >= ? GROUP BY Date',
        [ranges[1]],
    )

    by_symbol = query_db(
        'SELECT SUM(income) AS inc, symbol FROM income WHERE (incomeType = "REALIZED_PNL" OR incomeType = "FUNDING_FEE") AND time >= ? GROUP BY symbol ORDER BY inc DESC',
        [ranges[1]],
    )

    fees = {"USDT": 0, "BNB": 0}

    balance = float(balance[0])
    
    temptotal = [[],[]]
    profit_period = balance - zero_value(week[0])

    temp = [[], []]
    for each in by_date:
        temp[0].append(round(float(each[1]), 2))
        temp[1].append(each[0])
        temptotal[1].append(each[0])
        temptotal[0].append(round(profit_period + float(each[1]),2))
        profit_period += float(each[1])
    by_date = temp
    total_by_date = temptotal

    temp = [[], []]
    for each in by_symbol:
        temp[0].append(each[1])
        temp[1].append(round(float(each[0]), 2))
    by_symbol = temp

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
    ]
    return render_template(
        "home.html",
        coin_list=get_coins(),
        totals=totals,
        data=[by_date, by_symbol],
        timeframe="week",
        lastupdate=get_lastupdate(),
    )


@app.route("/dashboard/<timeframe>")
def dashboard(timeframe):
    if timeframe not in ["today", "week", "month", "quarter", "year", "all"]:
        return render_template("error.html", coin_list=get_coins()), 404

    ranges = timeranges()
    times = {"today": 0, "week": 1, "month": 2, "quarter": 4, "year": 5, "all": 6}
    balance = query_db("SELECT totalWalletBalance FROM account WHERE AID = 1", one=True)
    total = query_db('SELECT SUM(income) FROM income WHERE (incomeType = "REALIZED_PNL" OR incomeType = "FUNDING_FEE")', one=True)
    today = query_db(
        'SELECT SUM(income) FROM income WHERE (incomeType = "REALIZED_PNL" OR incomeType = "FUNDING_FEE") AND time >= ?',
        [ranges[0]],
        one=True,
    )
    week = query_db(
        'SELECT SUM(income) FROM income WHERE (incomeType = "REALIZED_PNL" OR incomeType = "FUNDING_FEE") AND time >= ?',
        [ranges[1]],
        one=True,
    )
    month = query_db(
        'SELECT SUM(income) FROM income WHERE (incomeType = "REALIZED_PNL" OR incomeType = "FUNDING_FEE") AND time >= ?',
        [ranges[2]],
        one=True,
    )

    unrealized = query_db("SELECT SUM(unrealizedProfit) FROM positions", one=True)

    all_fees = query_db(
        'SELECT SUM(income), asset FROM income WHERE incomeType ="COMMISSION" GROUP BY asset'
    )

    by_date = query_db(
        'SELECT DATE(time / 1000, "unixepoch") AS Date, SUM(income) AS inc FROM income WHERE (incomeType = "REALIZED_PNL" OR incomeType = "FUNDING_FEE") AND time >= ? GROUP BY Date',
        [ranges[times[timeframe]]],
    )

    by_symbol = query_db(
        'SELECT SUM(income) AS inc, symbol FROM income WHERE (incomeType = "REALIZED_PNL" OR incomeType = "FUNDING_FEE") AND time >= ? GROUP BY symbol ORDER BY inc DESC',
        [ranges[times[timeframe]]],
    )

    fees = {"USDT": 0, "BNB": 0}

    temp = [[], []]
    for each in by_date:
        temp[0].append(round(float(each[1]), 2))
        temp[1].append(each[0])
    by_date = temp

    temp = [[], []]
    for each in by_symbol:
        temp[0].append(each[1])
        temp[1].append(round(float(each[0]), 2))
    by_symbol = temp

    balance = float(balance[0])
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
    ]
    return render_template(
        "home.html",
        coin_list=get_coins(),
        totals=totals,
        timeframe=timeframe,
        data=[by_date, by_symbol],
        lastupdate=get_lastupdate(),
    )


@app.route("/coins/<coin>")
def show_individual_coin(coin):
    # show the selected coin stats
    coins = get_coins()
    if coin not in coins["inactive"] and coin not in coins["active"]:
        return render_template("error.html", coin_list=get_coins()), 404

    try:
        response = requests.get(
            "https://fapi.binance.com/fapi/v1/premiumIndex?symbol=" + coin, timeout=1
        )
        if response:
            markPrice = round(float(response.json()["markPrice"]), 5)
        else:
            markPrice = "-"
    except:
        markPrice = "-"

    ranges = timeranges()
    balance = query_db("SELECT totalWalletBalance FROM account WHERE AID = 1", one=True)
    if balance[0] is None:
        totals = ["-", "-", "-", "-", "-", {"USDT": 0, "BNB": 0}, ["-", "-", "-", "-"]]
    else:
        total = query_db(
            'SELECT SUM(income) FROM income WHERE (incomeType = "REALIZED_PNL" OR incomeType = "FUNDING_FEE") AND symbol = ?',
            [coin],
            one=True,
        )
        today = query_db(
            'SELECT SUM(income) FROM income WHERE (incomeType = "REALIZED_PNL" OR incomeType = "FUNDING_FEE") AND time >= ? AND symbol = ?',
            [ranges[0], coin],
            one=True,
        )
        week = query_db(
            'SELECT SUM(income) FROM income WHERE (incomeType = "REALIZED_PNL" OR incomeType = "FUNDING_FEE") AND time >= ? AND symbol = ?',
            [ranges[1], coin],
            one=True,
        )
        month = query_db(
            'SELECT SUM(income) FROM income WHERE (incomeType = "REALIZED_PNL" OR incomeType = "FUNDING_FEE") AND time >= ? AND symbol = ?',
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

        temp = []
        for position in allpositions:
            position = list(position)
            position[4] = round(float(position[4]), 5)
            temp.append(position)
        allpositions = temp

        temp = []
        for order in allorders:
            order = list(order)
            order[7] = datetime.fromtimestamp(order[7] / 1000.0).strftime("%Y-%m-%d %H:%M:%S")
            temp.append(order)
        allorders = temp

        fees = {"USDT": 0, "BNB": 0}
        balance = float(balance[0])
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
        ]
        by_date = query_db(
            'SELECT DATE(time / 1000, "unixepoch") AS Date, SUM(income) AS inc FROM income WHERE (incomeType = "REALIZED_PNL" OR incomeType = "FUNDING_FEE") AND time >= ? AND symbol = ? GROUP BY Date',
            [ranges[1], coin],
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
        timeframe="week",
        data=[by_date],
        orders=[allpositions, allorders],
        lastupdate=get_lastupdate(),
        markprice=markPrice,
    )


@app.route("/coins/<coin>/<timeframe>")
def show_individual_coin_timeframe(coin, timeframe):
    coins = get_coins()
    if (coin not in coins["inactive"] and coin not in coins["active"]) or timeframe not in [
        "today",
        "week",
        "month",
        "quarter",
        "year",
        "all",
    ]:
        return render_template("error.html", coin_list=get_coins()), 404

    try:
        response = requests.get(
            "https://fapi.binance.com/fapi/v1/premiumIndex?symbol=" + coin, timeout=1
        )
        if response:
            markPrice = round(float(response.json()["markPrice"]), 5)
        else:
            markPrice = "-"
    except:
        markPrice = "-"

    ranges = timeranges()
    times = {"today": 0, "week": 1, "month": 2, "quarter": 4, "year": 5, "all": 6}
    balance = query_db("SELECT totalWalletBalance FROM account WHERE AID = 1", one=True)
    if balance[0] is None:
        totals = ["-", "-", "-", "-", "-", {"USDT": 0, "BNB": 0}, ["-", "-", "-", "-"]]
    else:
        total = query_db(
            'SELECT SUM(income) FROM income WHERE (incomeType = "REALIZED_PNL" OR incomeType = "FUNDING_FEE") AND symbol = ?',
            [coin],
            one=True,
        )
        today = query_db(
            'SELECT SUM(income) FROM income WHERE (incomeType = "REALIZED_PNL" OR incomeType = "FUNDING_FEE") AND time >= ? AND symbol = ?',
            [ranges[0], coin],
            one=True,
        )
        week = query_db(
            'SELECT SUM(income) FROM income WHERE (incomeType = "REALIZED_PNL" OR incomeType = "FUNDING_FEE") AND time >= ? AND symbol = ?',
            [ranges[1], coin],
            one=True,
        )
        month = query_db(
            'SELECT SUM(income) FROM income WHERE (incomeType = "REALIZED_PNL" OR incomeType = "FUNDING_FEE") AND time >= ? AND symbol = ?',
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

        temp = []
        for position in allpositions:
            position = list(position)
            position[4] = round(float(position[4]), 5)
            temp.append(position)
        allpositions = temp

        temp = []
        for order in allorders:
            order = list(order)
            order[7] = datetime.fromtimestamp(order[7] / 1000.0).strftime("%Y-%m-%d %H:%M:%S")
            temp.append(order)
        allorders = temp
        fees = {"USDT": 0, "BNB": 0}
        balance = float(balance[0])
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
        ]

        by_date = query_db(
            'SELECT DATE(time / 1000, "unixepoch") AS Date, SUM(income) AS inc FROM income WHERE (incomeType = "REALIZED_PNL" OR incomeType = "FUNDING_FEE") AND time >= ? AND symbol = ? GROUP BY Date',
            [ranges[times[timeframe]], coin],
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
        timeframe=timeframe,
        data=[by_date],
        orders=[allpositions, allorders],
        lastupdate=get_lastupdate(),
        markprice=markPrice,
    )


@app.route("/history/")
def show_history():
    ranges = timeranges()
    times = {"today": 0, "week": 1, "month": 2, "quarter": 4, "year": 5, "all": 6}
    history = {"today": {"total":0}, "week": {"total":0}, "month": {"total":0}, "quarter": {"total":0}, "year": {"total":0}, "all": {"total":0}, "columns":[]}
    
    for timeframe in times: 
        incomesummary = query_db(
            'SELECT incomeType, COUNT(IID) FROM income WHERE time >= ? GROUP BY incomeType',
            [ranges[times[timeframe]]],
        )
        for totals in incomesummary:
            history[timeframe][totals[0]] = int(totals[1])
            history[timeframe]["total"] += int(totals[1])
            if totals[0] not in history["columns"]:
                history["columns"].append(totals[0])
    for timeframe in times:
        for column in history["columns"]:
            if column not in history[timeframe]:
                history[timeframe][column] = 0
                
    history["columns"].sort()

    return render_template("history.html", coin_list=get_coins(), timeframe="-", history=history, filename="-")

@app.route("/history/<timeframe>")
def show_all_history(timeframe):
    if timeframe not in ["today", "week", "month", "quarter", "year", "all"]:
        return render_template("error.html", coin_list=get_coins()), 404

    ranges = timeranges()
    times = {"today": 0, "week": 1, "month": 2, "quarter": 4, "year": 5, "all": 6}
    
    history = query_db(
        'SELECT * FROM income WHERE time >= ? ORDER BY time desc',
        [ranges[times[timeframe]]],
    )

    temp = []
    for inc in history:
        inc = list(inc)
        inc[7] = datetime.fromtimestamp(inc[7] / 1000.0).strftime("%Y-%m-%d %H:%M:%S")
        temp.append(inc)
    history = temp  
    
    filename = datetime.now().strftime("%Y-%m-%dT%H%M%S") + "_income_"+timeframe + ".csv"
    
    with open(os.path.join(app.root_path, 'static', 'csv', filename), 'w', newline='') as csvfile:
        spamwriter = csv.writer(csvfile, delimiter=',')
        spamwriter.writerow(["sqliteID", "TransactionId", "Symbol", "IncomeType", "Income", "Asset", "Info", "Time", "TradeId"])
        spamwriter.writerows(history)

    history = {"today": {"total":0}, "week": {"total":0}, "month": {"total":0}, "quarter": {"total":0}, "year": {"total":0}, "all": {"total":0}, "columns":[]}
    
    for timeframe in times: 
        incomesummary = query_db(
            'SELECT incomeType, COUNT(IID) FROM income WHERE time >= ? GROUP BY incomeType',
            [ranges[times[timeframe]]],
        )
        for totals in incomesummary:
            history[timeframe][totals[0]] = int(totals[1])
            history[timeframe]["total"] += int(totals[1])
            if totals[0] not in history["columns"]:
                history["columns"].append(totals[0])
    for timeframe in times:
        for column in history["columns"]:
            if column not in history[timeframe]:
                history[timeframe][column] = 0
                
    history["columns"].sort()
    
    filename = "csv/" + filename
    
    return render_template("history.html", coin_list=get_coins(), timeframe=timeframe, history=history,fname=filename)

@app.errorhandler(404)
def not_found(error):
    return render_template("error.html", coin_list=get_coins()), 404
