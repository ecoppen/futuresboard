from flask import Flask, render_template, request, g, redirect
import sqlite3
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
    coins = {"active": {}, "inactive": [], "totals": {"active": 0, "inactive": 0, "buys":0, "sells":0, "pbr":0}, "warning":False}

    all_active_positions = query_db(
        'SELECT symbol, entryPrice, positionSide, positionAmt FROM positions WHERE positionAmt > 0 ORDER BY symbol ASC'
    )

    all_symbols_with_pnl = query_db(
        'SELECT DISTINCT(symbol) FROM income WHERE asset <> "BNB" AND symbol <> "" AND incomeType <> "TRANSFER" ORDER BY symbol ASC'
    )
    
    balance = query_db("SELECT totalWalletBalance FROM account WHERE AID = 1", one=True)

    active_symbols = []

    for position in all_active_positions:
        active_symbols.append(position[0])

        pbr = round(calc_pbr(position[3], position[1], position[2], float(balance[0])),2)

        buy, sell = 0, 0

        buyorders = query_db(
            'SELECT COUNT(OID) FROM orders WHERE symbol = ? AND side = "BUY"', [position[0]], one=True
        )

        sellorders = query_db(
            'SELECT COUNT(OID) FROM orders WHERE symbol = ? AND side = "SELL"',
            [position[0]],
            one=True,
        )

        if buyorders is not None:
            buy = int(buyorders[0])
            if buy == 0:
                coins["warning"] = True
        if sellorders is not None:
            sell = int(sellorders[0])

        coins["active"][position[0]] = [buy, sell, pbr]
        coins["totals"]["active"] += 1
        coins["totals"]["buys"] += buy
        coins["totals"]["sells"] += sell
        coins["totals"]["pbr"] += pbr

    for symbol in all_symbols_with_pnl:
        if symbol[0] not in active_symbols:
            coins["inactive"].append(symbol[0])
            coins["totals"]["inactive"] += 1
    
    coins["totals"]["pbr"] = format_dp(coins["totals"]["pbr"])
    return coins


def get_lastupdate():
    lastupdate = query_db("SELECT MAX(time) FROM orders", one=True)
    if lastupdate is None:
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
    
    two_year_start = (last_year_start - timedelta(days=1)).replace(day=1).replace(month=1)
    
    return [
        [today.strftime('%Y-%m-%d'), today.strftime('%Y-%m-%d')],
        [yesterday_start.strftime('%Y-%m-%d'), yesterday_start.strftime('%Y-%m-%d')],
        [this_week_start.strftime('%Y-%m-%d'), today.strftime('%Y-%m-%d')],
        [last_week_start.strftime('%Y-%m-%d'), last_week_end.strftime('%Y-%m-%d')],
        [this_month_start.strftime('%Y-%m-%d'), today.strftime('%Y-%m-%d')],
        [last_month_start.strftime('%Y-%m-%d'), last_month_end.strftime('%Y-%m-%d')],
        [this_year_start.strftime('%Y-%m-%d'), today.strftime('%Y-%m-%d')],
        [last_year_start.strftime('%Y-%m-%d'), last_year_end.strftime('%Y-%m-%d')],
        [last_year_start.strftime('%Y-%m-%d'), today.strftime('%Y-%m-%d')]
    ]

@app.route("/", methods=['GET'])
def index_page():
    daterange = request.args.get('daterange')
    ranges = timeranges()
    
    if daterange is not None:
        daterange = daterange.split(" - ")
        if len(daterange) == 2:
            try:
                start = datetime.combine(datetime.fromisoformat(daterange[0]), datetime.min.time()).timestamp() * 1000
                end = datetime.combine(datetime.fromisoformat(daterange[1]), datetime.max.time()).timestamp() * 1000
                startdate, enddate = daterange[0], daterange[1]
                return redirect('/dashboard/' + startdate + "/" + enddate)
            except:
                pass

    todaystart = datetime.combine(datetime.fromisoformat(ranges[0][0]), datetime.min.time()).timestamp() * 1000
    todayend = datetime.combine(datetime.fromisoformat(ranges[0][1]), datetime.max.time()).timestamp() * 1000
    weekstart = datetime.combine(datetime.fromisoformat(ranges[2][0]), datetime.min.time()).timestamp() * 1000
    weekend = datetime.combine(datetime.fromisoformat(ranges[2][1]), datetime.max.time()).timestamp() * 1000
    monthstart = datetime.combine(datetime.fromisoformat(ranges[4][0]), datetime.min.time()).timestamp() * 1000
    monthend = datetime.combine(datetime.fromisoformat(ranges[4][1]), datetime.max.time()).timestamp() * 1000            
            
    start = datetime.combine(datetime.fromisoformat(ranges[2][0]), datetime.min.time()).timestamp() * 1000 
    end = datetime.combine(datetime.fromisoformat(ranges[2][1]), datetime.max.time()).timestamp() * 1000 
    startdate, enddate = ranges[2][0], ranges[2][1]
    
    balance = query_db("SELECT totalWalletBalance FROM account WHERE AID = 1", one=True)
    total = query_db('SELECT SUM(income) FROM income WHERE asset <> "BNB" AND incomeType <> "TRANSFER"', one=True)
    today = query_db(
        'SELECT SUM(income) FROM income WHERE asset <> "BNB" AND incomeType <> "TRANSFER" AND time >= ? AND time <= ?',
        [todaystart, todayend],
        one=True,
    )
    week = query_db(
        'SELECT SUM(income) FROM income WHERE asset <> "BNB" AND incomeType <> "TRANSFER" AND time >= ? AND time <= ?',
        [weekstart, weekend],
        one=True,
    )
    month = query_db(
        'SELECT SUM(income) FROM income WHERE asset <> "BNB" AND incomeType <> "TRANSFER" AND time >= ? AND time <= ?',
        [monthstart, monthend],
        one=True,
    )

    unrealized = query_db("SELECT SUM(unrealizedProfit) FROM positions", one=True)

    all_fees = query_db(
        'SELECT SUM(income), asset FROM income WHERE incomeType ="COMMISSION" GROUP BY asset'
    )

    by_date = query_db(
        'SELECT DATE(time / 1000, "unixepoch") AS Date, SUM(income) AS inc FROM income WHERE asset <> "BNB" AND incomeType <> "TRANSFER" AND time >= ?  AND time <= ? GROUP BY Date',
        [start, end],
    )

    by_symbol = query_db(
        'SELECT SUM(income) AS inc, symbol FROM income WHERE asset <> "BNB" AND incomeType <> "TRANSFER" AND time >= ? AND time <= ? GROUP BY symbol ORDER BY inc DESC',
        [start, end],
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
        datetime.now().strftime("%B"),
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
        
    )


@app.route("/dashboard/<start>/<end>", methods=['GET'])
def dashboard(start, end):
    ranges = timeranges()
    daterange = request.args.get('daterange')
    
    if daterange is not None:
        daterange = daterange.split(" - ")
        if len(daterange) == 2:
            try:
                start = datetime.combine(datetime.fromisoformat(daterange[0]), datetime.min.time()).timestamp() * 1000
                end = datetime.combine(datetime.fromisoformat(daterange[1]), datetime.max.time()).timestamp() * 1000
                startdate, enddate = daterange[0], daterange[1]
                return redirect('/dashboard/' + startdate + "/" + enddate)
            except:
                return redirect('/dashboard/' + start + "/" + end)
    
    try:
        startdate, enddate = start, end
        start = datetime.combine(datetime.fromisoformat(start), datetime.min.time()).timestamp() * 1000
        end = datetime.combine(datetime.fromisoformat(end), datetime.max.time()).timestamp() * 1000
    except:
        startdate, enddate = ranges[2][0], ranges[2][1]
        return redirect('/dashboard/' + startdate + "/" + enddate)

    todaystart = datetime.combine(datetime.fromisoformat(ranges[0][0]), datetime.min.time()).timestamp() * 1000
    todayend = datetime.combine(datetime.fromisoformat(ranges[0][1]), datetime.max.time()).timestamp() * 1000
    weekstart = datetime.combine(datetime.fromisoformat(ranges[2][0]), datetime.min.time()).timestamp() * 1000
    weekend = datetime.combine(datetime.fromisoformat(ranges[2][1]), datetime.max.time()).timestamp() * 1000
    monthstart = datetime.combine(datetime.fromisoformat(ranges[4][0]), datetime.min.time()).timestamp() * 1000
    monthend = datetime.combine(datetime.fromisoformat(ranges[4][1]), datetime.max.time()).timestamp() * 1000
    
    times = {"today": 0, "week": 1, "month": 2, "quarter": 4, "year": 5, "all": 6}
    balance = query_db("SELECT totalWalletBalance FROM account WHERE AID = 1", one=True)
    total = query_db('SELECT SUM(income) FROM income WHERE asset <> "BNB" AND incomeType <> "TRANSFER"', one=True)

    today = query_db(
        'SELECT SUM(income) FROM income WHERE asset <> "BNB" AND incomeType <> "TRANSFER" AND time >= ? AND time <= ?',
        [todaystart, todayend],
        one=True,
    )
    week = query_db(
        'SELECT SUM(income) FROM income WHERE asset <> "BNB" AND incomeType <> "TRANSFER" AND time >= ? AND time <= ?',
        [weekstart, weekend],
        one=True,
    )
    month = query_db(
        'SELECT SUM(income) FROM income WHERE asset <> "BNB" AND incomeType <> "TRANSFER" AND time >= ? AND time <= ?',
        [monthstart, monthend],
        one=True,
    )

    unrealized = query_db("SELECT SUM(unrealizedProfit) FROM positions", one=True)

    all_fees = query_db(
        'SELECT SUM(income), asset FROM income WHERE incomeType ="COMMISSION" GROUP BY asset'
    )

    by_date = query_db(
        'SELECT DATE(time / 1000, "unixepoch") AS Date, SUM(income) AS inc FROM income WHERE asset <> "BNB" AND incomeType <> "TRANSFER" AND time >= ?  AND time <= ? GROUP BY Date',
        [start, end],
    )

    by_symbol = query_db(
        'SELECT SUM(income) AS inc, symbol FROM income WHERE asset <> "BNB" AND incomeType <> "TRANSFER" AND time >= ? AND time <= ? GROUP BY symbol ORDER BY inc DESC',
        [start, end],
    )

    fees = {"USDT": 0, "BNB": 0}

    balance = float(balance[0])
    
    temptotal = [[],[]]
    
    customframe = query_db(
        'SELECT SUM(income) FROM income WHERE asset <> "BNB" AND incomeType <> "TRANSFER" AND time >= ? AND time <= ?',
        [start, end],
        one=True,
    )
    
    profit_period = balance - zero_value(customframe[0])

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
        datetime.now().strftime("%B")
    ]
    return render_template(
        "home.html",
        coin_list=get_coins(),
        totals=totals,
        data=[by_date, by_symbol, total_by_date],
        lastupdate=get_lastupdate(),
        startdate=startdate,
        enddate=enddate,
        timeranges=ranges
    )

@app.route("/positions")
def positions_page():
    coins = get_coins()
    positions = {}
    for coin in coins['active']:
        
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
        
        positions[coin] = [allpositions, allorders]

    return render_template(
        "positions.html",
        coin_list=get_coins(),
        positions = positions
    )
    

@app.route("/coins/<coin>", methods=['GET'])
def show_individual_coin(coin):
    coins = get_coins()
    if coin not in coins["inactive"] and coin not in coins["active"]:
        return render_template("error.html", coin_list=get_coins()), 404

    daterange = request.args.get('daterange')
    ranges = timeranges()
    
    if daterange is not None:
        daterange = daterange.split(" - ")
        if len(daterange) == 2:
            try:
                start = datetime.combine(datetime.fromisoformat(daterange[0]), datetime.min.time()).timestamp() * 1000
                end = datetime.combine(datetime.fromisoformat(daterange[1]), datetime.max.time()).timestamp() * 1000
                startdate, enddate = daterange[0], daterange[1]
                return redirect('/coins/' + coin + '/' + startdate + '/' + enddate)
            except:
                pass    
    
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

    balance = query_db("SELECT totalWalletBalance FROM account WHERE AID = 1", one=True)
    if balance[0] is None:
        totals = ["-", "-", "-", "-", "-", {"USDT": 0, "BNB": 0}, ["-", "-", "-", "-"]]
    else:
        
        todaystart = datetime.combine(datetime.fromisoformat(ranges[0][0]), datetime.min.time()).timestamp() * 1000
        todayend = datetime.combine(datetime.fromisoformat(ranges[0][1]), datetime.max.time()).timestamp() * 1000
        weekstart = datetime.combine(datetime.fromisoformat(ranges[2][0]), datetime.min.time()).timestamp() * 1000
        weekend = datetime.combine(datetime.fromisoformat(ranges[2][1]), datetime.max.time()).timestamp() * 1000
        monthstart = datetime.combine(datetime.fromisoformat(ranges[4][0]), datetime.min.time()).timestamp() * 1000
        monthend = datetime.combine(datetime.fromisoformat(ranges[4][1]), datetime.max.time()).timestamp() * 1000            
        
        startdate, enddate = ranges[2][0], ranges[2][1]
        
        total = query_db(
            'SELECT SUM(income) FROM income WHERE asset <> "BNB" AND incomeType <> "TRANSFER" AND symbol = ?',
            [coin],
            one=True,
        )
        today = query_db(
            'SELECT SUM(income) FROM income WHERE asset <> "BNB" AND incomeType <> "TRANSFER" AND time >= ? AND time <= ? AND symbol = ?',
            [todaystart, todayend, coin],
            one=True,
        )
        week = query_db(
            'SELECT SUM(income) FROM income WHERE asset <> "BNB" AND incomeType <> "TRANSFER" AND time >= ? AND time <= ? AND symbol = ?',
            [weekstart, weekend, coin],
            one=True,
        )
        month = query_db(
            'SELECT SUM(income) FROM income WHERE asset <> "BNB" AND incomeType <> "TRANSFER" AND time >= ? AND time <= ? AND symbol = ?',
            [monthstart, monthend, coin],
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
            datetime.now().strftime("%B")
        ]
        by_date = query_db(
            'SELECT DATE(time / 1000, "unixepoch") AS Date, SUM(income) AS inc FROM income WHERE asset <> "BNB" AND incomeType <> "TRANSFER" AND time >= ? AND time <= ? AND symbol = ? GROUP BY Date',
            [weekstart, weekend, coin],
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
        timeranges=ranges
    )


@app.route("/coins/<coin>/<start>/<end>")
def show_individual_coin_timeframe(coin, start, end):
    coins = get_coins()
    if (coin not in coins["inactive"] and coin not in coins["active"]):
        return render_template("error.html", coin_list=get_coins()), 404

    ranges = timeranges()
    daterange = request.args.get('daterange')
    
    if daterange is not None:
        daterange = daterange.split(" - ")
        if len(daterange) == 2:
            try:
                start = datetime.combine(datetime.fromisoformat(daterange[0]), datetime.min.time()).timestamp() * 1000
                end = datetime.combine(datetime.fromisoformat(daterange[1]), datetime.max.time()).timestamp() * 1000
                startdate, enddate = daterange[0], daterange[1]
                return redirect('/coins/' + coin + '/' + startdate + '/' + enddate)
            except:
                return redirect('/coins/' + coin + '/' + start + '/' + end)
    
    try:
        startdate, enddate = start, end
        start = datetime.combine(datetime.fromisoformat(start), datetime.min.time()).timestamp() * 1000
        end = datetime.combine(datetime.fromisoformat(end), datetime.max.time()).timestamp() * 1000
    except:
        startdate, enddate = ranges[2][0], ranges[2][1]
        return redirect('/coins/' + coin + '/' + startdate + '/' + enddate)

    todaystart = datetime.combine(datetime.fromisoformat(ranges[0][0]), datetime.min.time()).timestamp() * 1000
    todayend = datetime.combine(datetime.fromisoformat(ranges[0][1]), datetime.max.time()).timestamp() * 1000
    weekstart = datetime.combine(datetime.fromisoformat(ranges[2][0]), datetime.min.time()).timestamp() * 1000
    weekend = datetime.combine(datetime.fromisoformat(ranges[2][1]), datetime.max.time()).timestamp() * 1000
    monthstart = datetime.combine(datetime.fromisoformat(ranges[4][0]), datetime.min.time()).timestamp() * 1000
    monthend = datetime.combine(datetime.fromisoformat(ranges[4][1]), datetime.max.time()).timestamp() * 1000               
    
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

    balance = query_db("SELECT totalWalletBalance FROM account WHERE AID = 1", one=True)
    if balance[0] is None:
        totals = ["-", "-", "-", "-", "-", {"USDT": 0, "BNB": 0}, ["-", "-", "-", "-"]]
    else:
        total = query_db(
            'SELECT SUM(income) FROM income WHERE asset <> "BNB" AND incomeType <> "TRANSFER" AND symbol = ?',
            [coin],
            one=True,
        )
        today = query_db(
            'SELECT SUM(income) FROM income WHERE asset <> "BNB" AND incomeType <> "TRANSFER" AND time >= ? AND time <= ? AND symbol = ?',
            [todaystart, todayend, coin],
            one=True,
        )
        week = query_db(
            'SELECT SUM(income) FROM income WHERE asset <> "BNB" AND incomeType <> "TRANSFER" AND time >= ? AND time <= ? AND symbol = ?',
            [weekstart, weekend, coin],
            one=True,
        )
        month = query_db(
            'SELECT SUM(income) FROM income WHERE asset <> "BNB" AND incomeType <> "TRANSFER" AND time >= ? AND time <= ? AND symbol = ?',
            [monthstart, monthend, coin],
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
            datetime.now().strftime("%B")
        ]

        by_date = query_db(
            'SELECT DATE(time / 1000, "unixepoch") AS Date, SUM(income) AS inc FROM income WHERE asset <> "BNB" AND incomeType <> "TRANSFER" AND time >= ? AND time <= ? AND symbol = ? GROUP BY Date',
            [start, end, coin],
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
        timeranges=ranges
    )


@app.route("/history/")
def show_history():
    ranges = timeranges()
    history = {"columns":[]}
    
    for timeframe in ranges: 
        start = datetime.combine(datetime.fromisoformat(timeframe[0]), datetime.min.time()).timestamp() * 1000
        end = datetime.combine(datetime.fromisoformat(timeframe[1]), datetime.max.time()).timestamp() * 1000
        incomesummary = query_db(
            'SELECT incomeType, COUNT(IID) FROM income WHERE time >= ? AND time <= ? GROUP BY incomeType',
            [start, end],
        )
        temp = timeframe[0] + "/" +timeframe[1]
        if temp not in history:
            history[temp] = {}
            history[temp]['total'] = 0
            
        for totals in incomesummary:
            history[temp][totals[0]] = int(totals[1])
            history[temp]["total"] += int(totals[1])
            if totals[0] not in history["columns"]:
                history["columns"].append(totals[0])
    for timeframe in ranges:
        temp = timeframe[0] + "/" +timeframe[1]
        for column in history["columns"]:
            if column not in history[temp]:
                history[temp][column] = 0
                
    history["columns"].sort()
    
    previous_files = []
    for file in os.listdir(os.path.join(app.root_path, 'static', 'csv')):
        if file.endswith(".csv"):
            previous_files.append("csv/" + file)

    return render_template("history.html", coin_list=get_coins(), history=history, filename="-", files=previous_files)

@app.route("/history/<start>/<end>")
def show_all_history(start,end):
    try:
        startdate, enddate = start, end
        start = datetime.combine(datetime.fromisoformat(start), datetime.min.time()).timestamp() * 1000
        end = datetime.combine(datetime.fromisoformat(end), datetime.max.time()).timestamp() * 1000
    except:
        return redirect('/history/')    

    ranges = timeranges()
    
    history = query_db(
        'SELECT * FROM income WHERE time >= ? AND time <= ? ORDER BY time desc',
        [start, end],
    )

    temp = []
    for inc in history:
        inc = list(inc)
        inc[7] = datetime.fromtimestamp(inc[7] / 1000.0).strftime("%Y-%m-%d %H:%M:%S")
        temp.append(inc)
    history = temp  
    
    filename = datetime.now().strftime("%Y-%m-%dT%H%M%S") + "_income_" + startdate + "_" + enddate + ".csv"
    
    with open(os.path.join(app.root_path, 'static', 'csv', filename), 'w', newline='') as csvfile:
        spamwriter = csv.writer(csvfile, delimiter=',')
        spamwriter.writerow(["sqliteID", "TransactionId", "Symbol", "IncomeType", "Income", "Asset", "Info", "Time", "TradeId"])
        spamwriter.writerows(history)

    history = {"columns":[]}
    
    for timeframe in ranges: 
        start = datetime.combine(datetime.fromisoformat(timeframe[0]), datetime.min.time()).timestamp() * 1000
        end = datetime.combine(datetime.fromisoformat(timeframe[1]), datetime.max.time()).timestamp() * 1000
        incomesummary = query_db(
            'SELECT incomeType, COUNT(IID) FROM income WHERE time >= ? AND time <= ? GROUP BY incomeType',
            [start, end],
        )
        temp = timeframe[0] + "/" +timeframe[1]
        if temp not in history:
            history[temp] = {}
            history[temp]['total'] = 0
            
        for totals in incomesummary:
            history[temp][totals[0]] = int(totals[1])
            history[temp]["total"] += int(totals[1])
            if totals[0] not in history["columns"]:
                history["columns"].append(totals[0])
    for timeframe in ranges:
        temp = timeframe[0] + "/" +timeframe[1]
        for column in history["columns"]:
            if column not in history[temp]:
                history[temp][column] = 0
                
    history["columns"].sort()
    
    filename = "csv/" + filename
    
    previous_files = []
    for file in os.listdir(os.path.join(app.root_path, 'static', 'csv')):
        if file.endswith(".csv"):
            previous_files.append("csv/" + file)
    
    return render_template("history.html", coin_list=get_coins(), history=history, fname=filename, files=previous_files)

@app.route("/projection")
def projection():
    balance = query_db("SELECT totalWalletBalance FROM account WHERE AID = 1", one=True)
    if balance[0] is None:
        projections = [[[], []], [[], []],[[], []],[[], []],[[], []]]
    else:
        projections = [[[], []], [[], []],[[], []],[[], []],[[], []]]
        
        ranges = timeranges()
        
        todayend = datetime.combine(datetime.fromisoformat(ranges[0][1]), datetime.max.time()).timestamp() * 1000
        minus_7_start = datetime.combine(datetime.fromisoformat((date.today() - timedelta(days=7)).strftime('%Y-%m-%d')), datetime.max.time()).timestamp() * 1000
        
        week = query_db(
            'SELECT SUM(income) FROM income WHERE asset <> "BNB" AND incomeType <> "TRANSFER" AND time >= ? AND time <= ?',
            [minus_7_start, todayend],
            one=True,
        )
        custom = round(week[0] / balance[0]*100/7, 2)
        projections[4].append(custom)               
        today= date.today()
        x = 1
        while x < 365:
            nextday = today + timedelta(days=x)
            projections[0][1].append(nextday.strftime("%Y-%m-%d"))
            #projections[1][1].append(nextday.strftime("%Y-%m-%d"))
            #projections[2][1].append(nextday.strftime("%Y-%m-%d"))
            #projections[3][1].append(nextday.strftime("%Y-%m-%d"))
            if len(projections[0][0]) < 1:
                newbalance = balance[0]
            else:
                newbalance = projections[0][0][-1]
            projections[0][0].append(newbalance*1.003)
            
            if len(projections[1][0]) < 1:
                newbalance = balance[0]
            else:
                newbalance = projections[1][0][-1]
            projections[1][0].append(newbalance*1.005)
            
            if len(projections[2][0]) < 1:
                newbalance = balance[0]
            else:
                newbalance = projections[2][0][-1]
            projections[2][0].append(newbalance*1.01)
            
            if len(projections[3][0]) < 1:
                newbalance = balance[0]
            else:
                newbalance = projections[3][0][-1]
            projections[3][0].append(newbalance*1.012)
            
            if len(projections[4][0]) < 1:
                newbalance = balance[0]
            else:
                newbalance = projections[4][0][-1]
            projections[4][0].append(newbalance * (1+(week[0] / balance[0])/7))   
            
            x+=1
        
    return render_template("projection.html", coin_list=get_coins(), data=projections)

@app.errorhandler(404)
def not_found(error):
    return render_template("error.html", coin_list=get_coins()), 404
