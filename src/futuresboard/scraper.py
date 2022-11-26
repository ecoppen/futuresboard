# https://github.com/binance/binance-signature-examples
from __future__ import annotations

import datetime
import hashlib
import hmac
import sqlite3
import threading
import time
from datetime import timedelta
from sqlite3 import Error
from urllib.parse import urlencode
from collections import OrderedDict

import requests
from flask import current_app


class HTTPRequestError(Exception):
    def __init__(self, url, code, msg=None):
        self.url = url
        self.code = code
        self.msg = msg

    def __str__(self) -> str:
        """
        Convert the exception into a printable string
        """
        return f"Request to {self.url!r} failed. Code: {self.code}; Message: {self.msg}"


def auto_scrape(app):
    thread = threading.Thread(target=_auto_scrape, args=(app,))
    thread.daemon = True
    thread.start()


def _auto_scrape(app):
    with app.app_context():
        interval = app.config["AUTO_SCRAPE_INTERVAL"]
        while True:
            app.logger.info("Auto scrape routines starting")
            scrape(app=app)
            app.logger.info("Auto scrape routines terminated. Sleeping %s seconds...", interval)
            time.sleep(interval)


def hashing(query_string):
    return hmac.new(
        current_app.config["API_SECRET"].encode("utf-8"),
        query_string.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def get_timestamp():
    return int(time.time() * 1000)


def dispatch_request(http_method):
    session = requests.Session()
    session.headers.update(
        {
            "Content-Type": "application/json;charset=utf-8",
            "X-MBX-APIKEY": current_app.config["API_KEY"],
        }
    )
    return {
        "GET": session.get,
        "DELETE": session.delete,
        "PUT": session.put,
        "POST": session.post,
    }.get(http_method, "GET")


# used for sending request requires the signature
def send_signed_request(http_method, url_path, payload={}, signature="signature"):
    payload["timestamp"] = get_timestamp()
    query_string = urlencode(OrderedDict(sorted(payload.items())))
    query_string = query_string.replace("%27", "%22")  # replace single quote to double quote

    url = (
        current_app.config["API_BASE_URL"]
        + url_path
        + "?"
        + query_string
        + "&"
        + signature
        + "="
        + hashing(query_string)
    )

    # print("{} {}".format(http_method, url))
    params = {"url": url, "params": {}}
    try:
        response = dispatch_request(http_method)(**params)
        headers = response.headers
        json_response = response.json()
        if "code" in json_response:
            raise HTTPRequestError(url=url, code=json_response["code"], msg=json_response["msg"])
        return headers, json_response
    except requests.exceptions.ConnectionError as e:
        raise HTTPRequestError(url=url, code=-1, msg=str(e))


# used for sending public data request
def send_public_request(url_path, payload={}):
    query_string = urlencode(payload, True)
    url = current_app.config["API_BASE_URL"] + url_path
    if query_string:
        url = url + "?" + query_string
    # print("{}".format(url))
    try:
        response = dispatch_request("GET")(url=url)
        headers = response.headers
        json_response = response.json()
        if "code" in json_response:
            raise HTTPRequestError(url=url, code=json_response["code"], msg=json_response["msg"])
        return headers, json_response
    except requests.exceptions.ConnectionError as e:
        raise HTTPRequestError(url=url, code=-2, msg=str(e))


def create_connection(db_file):
    conn = None
    try:
        conn = sqlite3.connect(db_file)
    except Error as e:
        print(e)

    return conn


def create_table(conn, create_table_sql):
    try:
        c = conn.cursor()
        c.execute(create_table_sql)
    except Error as e:
        print(e)


def db_setup(database):
    sql_create_income_table = """ CREATE TABLE IF NOT EXISTS income (
                                        IID integer PRIMARY KEY AUTOINCREMENT,
                                        tranId integer,
                                        symbol text,
                                        incomeType text,
                                        income real,
                                        asset text,
                                        info text,
                                        time integer,
                                        tradeId integer,
                                        UNIQUE(tranId, incomeType) ON CONFLICT REPLACE
                                    ); """

    sql_create_position_table = """ CREATE TABLE IF NOT EXISTS positions (
                                        PID integer PRIMARY KEY AUTOINCREMENT,
                                        symbol text,
                                        unrealizedProfit real,
                                        leverage integer,
                                        entryPrice real,
                                        positionSide text,
                                        positionAmt real
                                    ); """

    sql_create_account_table = """ CREATE TABLE IF NOT EXISTS account (
                                        AID integer PRIMARY KEY,
                                        totalWalletBalance real,
                                        totalUnrealizedProfit real,
                                        totalMarginBalance real,
                                        availableBalance real,
                                        maxWithdrawAmount real
                                    ); """

    sql_create_orders_table = """ CREATE TABLE IF NOT EXISTS orders (
                                        OID integer PRIMARY KEY AUTOINCREMENT,
                                        origQty real,
                                        price real,
                                        side text,
                                        positionSide text,
                                        status text,
                                        symbol text,
                                        time integer,
                                        type text
                                    ); """
    # create a database connection
    conn = create_connection(database)

    # create tables
    if conn is not None:
        create_table(conn, sql_create_income_table)
        create_table(conn, sql_create_position_table)
        create_table(conn, sql_create_account_table)
        create_table(conn, sql_create_orders_table)
    else:
        print("Error! cannot create the database connection.")


# income interactions
def create_income(conn, income):
    sql = """ INSERT INTO income(tranId, symbol, incomeType, income, asset, info, time, tradeId)
              VALUES(?,?,?,?,?,?,?,?) """
    cur = conn.cursor()
    cur.execute(sql, income)


def select_latest_income(conn):
    cur = conn.cursor()
    cur.execute("SELECT time FROM income ORDER BY time DESC LIMIT 0, 1")
    return cur.fetchone()


def select_latest_income_symbol(conn, symbol):
    cur = conn.cursor()
    cur.execute("SELECT time FROM income WHERE symbol = ? ORDER BY time DESC LIMIT 0, 1", (symbol,))
    return cur.fetchone()


# position interactions
def create_position(conn, position):
    sql = """ INSERT INTO positions(unrealizedProfit, leverage, entryPrice, positionAmt, symbol, positionSide) VALUES(?,?,?,?,?,?) """
    cur = conn.cursor()
    cur.execute(sql, position)


def update_position(conn, position):
    sql = """ UPDATE positions SET unrealizedProfit = ?, leverage = ?, entryPrice = ?, positionAmt = ? WHERE symbol = ? AND positionSide = ? """
    cur = conn.cursor()
    cur.execute(sql, position)

    
def delete_all_positions(conn):
    sql = """ DELETE FROM positions """
    cur = conn.cursor()
    cur.execute(sql)
    conn.commit()
    

def select_position(conn, symbol):
    cur = conn.cursor()
    cur.execute("SELECT unrealizedProfit FROM positions WHERE symbol = ? AND positionSide = ? LIMIT 0, 1", (symbol[0], symbol[1], ))
    return cur.fetchone()


# account interactions
def create_account(conn, account):
    sql = """ INSERT INTO account(totalWalletBalance, totalUnrealizedProfit, totalMarginBalance, availableBalance, maxWithdrawAmount, AID) VALUES(?,?,?,?,?,?) """
    cur = conn.cursor()
    cur.execute(sql, account)


def update_account(conn, account):
    sql = """ UPDATE account SET totalWalletBalance = ?, totalUnrealizedProfit = ?, totalMarginBalance = ?, availableBalance = ?, maxWithdrawAmount = ? WHERE AID = ?"""
    cur = conn.cursor()
    cur.execute(sql, account)


def select_account(conn):
    cur = conn.cursor()
    cur.execute("SELECT totalWalletBalance FROM account LIMIT 0, 1")
    return cur.fetchone()


# orders interactions
def delete_all_orders(conn):
    sql = """ DELETE FROM orders """
    cur = conn.cursor()
    cur.execute(sql)
    conn.commit()


def create_orders(conn, orders):
    sql = """ INSERT INTO orders(origQty, price, side, positionSide, status, symbol, time, type) VALUES(?,?,?,?,?,?,?,?) """
    cur = conn.cursor()
    cur.execute(sql, orders)


def scrape(app=None):
    try:
        _scrape(app=app)
    except HTTPRequestError as exc:
        if app is None:
            print(exc)
        else:
            app.logger.error(str(exc))


def _scrape(app=None):
    start = time.time()
    db_setup(current_app.config["DATABASE"])

    up_to_date = False
    weightused = 0
    processed, updated_positions, new_positions, updated_orders, sleeps = 0, 0, 0, 0, 0

    if current_app.config["EXCHANGE"].lower() == "binance":
        if weightused < 800:
            responseHeader, responseJSON = send_signed_request("GET", "/fapi/v1/openOrders")
            weightused = int(responseHeader["X-MBX-USED-WEIGHT-1M"])

            with create_connection(current_app.config["DATABASE"]) as conn:
                delete_all_orders(conn)
                for order in responseJSON:
                    updated_orders += 1
                    row = (
                        float(order["origQty"]),
                        float(order["price"]),
                        order["side"],
                        order["positionSide"],
                        order["status"],
                        order["symbol"],
                        int(order["time"]),
                        order["type"],
                    )
                    create_orders(conn, row)
                conn.commit()

        responseHeader, responseJSON = send_signed_request("GET", "/fapi/v2/account")
        weightused = int(responseHeader["X-MBX-USED-WEIGHT-1M"])

        overweight = False
        try:
            positions = responseJSON["positions"]
        except Exception:
            overweight = True

        if not overweight:
            with create_connection(current_app.config["DATABASE"]) as conn:
                totals_row = (
                    float(responseJSON["totalWalletBalance"]),
                    float(responseJSON["totalUnrealizedProfit"]),
                    float(responseJSON["totalMarginBalance"]),
                    float(responseJSON["availableBalance"]),
                    float(responseJSON["maxWithdrawAmount"]),
                    1,
                )
                accountCheck = select_account(conn)
                if accountCheck is None:
                    create_account(conn, totals_row)
                elif float(accountCheck[0]) != float(responseJSON["totalWalletBalance"]):
                    update_account(conn, totals_row)
                    
                delete_all_positions(conn)
                
                for position in positions:
                    position_row = (
                        float(position["unrealizedProfit"]),
                        int(position["leverage"]),
                        float(position["entryPrice"]),
                        float(position["positionAmt"]),
                        position["symbol"],
                        position["positionSide"],
                    )

                    create_position(conn, position_row)
                    updated_positions += 1

                conn.commit()

        while not up_to_date:
            if weightused > 800:
                print(f"Weight used: {weightused}/800\nProcessed: {processed}\nSleep: 1 minute")
                sleeps += 1
                time.sleep(60)

            with create_connection(current_app.config["DATABASE"]) as conn:
                startTime = select_latest_income(conn)
                if startTime is None:
                    startTime = int(
                        datetime.datetime.fromisoformat("2020-01-01 00:00:00+00:00").timestamp()
                        * 1000
                    )
                else:
                    startTime = startTime[0]

                params = {"startTime": startTime + 1, "limit": 1000}

                responseHeader, responseJSON = send_signed_request("GET", "/fapi/v1/income", params)
                weightused = int(responseHeader["X-MBX-USED-WEIGHT-1M"])

                if len(responseJSON) == 0:
                    up_to_date = True
                else:
                    for income in responseJSON:
                        if len(income["tradeId"]) == 0:
                            income["tradeId"] = 0
                        income_row = (
                            int(income["tranId"]),
                            income["symbol"],
                            income["incomeType"],
                            income["income"],
                            income["asset"],
                            income["info"],
                            int(income["time"]),
                            int(income["tradeId"]),
                        )
                        create_income(conn, income_row)
                        processed += 1

                    conn.commit()
    elif current_app.config["EXCHANGE"].lower() == "bybit":
        all_symbols = []
        exec_type = {
            "Trade": "REALIZED_PNL",
            "Funding": "FUNDING_FEE",
            "AdlTrade": "ADLTRADE",
            "BustTrade": "BUSTTRADE",
        }

        params = {"api_key": current_app.config["API_KEY"]}
        responseHeader, responseJSON = send_signed_request(
            "GET", "/private/linear/position/list", params, signature="sign"
        )
        if "rate_limit_status" in responseJSON:
            weightused = int(responseJSON["rate_limit_status"])

        with create_connection(current_app.config["DATABASE"]) as conn:
            delete_all_orders(conn)
            delete_all_positions(conn)
            
            for position in responseJSON["result"]:
                if weightused < 10:
                    print(
                        f"Weight used: {weightused}/{120-weightused}\nProcessed: {updated_positions + new_positions + updated_orders}\nSleep: 1 minute"
                    )
                    sleeps += 1
                    time.sleep(60)

                if position["data"]["symbol"] not in all_symbols:
                    all_symbols.append(position["data"]["symbol"])
                    
                if position["data"]["size"] > 0:
                    if position["data"]["side"].lower() == "buy":
                        positionside = "LONG"
                    else:
                        positionside = "SHORT"
                    
                    position_row = (
                        float(position["data"]["unrealised_pnl"]),
                        int(position["data"]["leverage"]),
                        float(position["data"]["entry_price"]),
                        float(position["data"]["size"]),
                        position["data"]["symbol"],
                        positionside,
                    )

                    create_position(conn, position_row)
                    updated_positions += 1

                    params = {
                        "symbol": position["data"]["symbol"],
                        "api_key": current_app.config["API_KEY"],
                    }
                    responseHeader, responseJSON = send_signed_request(
                        "GET", "/private/linear/order/search", params, signature="sign"
                    )
                    if "rate_limit_status" in responseJSON:
                        weightused = int(responseJSON["rate_limit_status"])

                    for order in responseJSON["result"]:

                        updated_orders += 1

                        if order["side"].lower() == "buy":
                            orderside = "BUY"
                        else:
                            orderside = "SELL"

                        time_format = datetime.datetime.strptime(
                            order["created_time"], "%Y-%m-%dT%H:%M:%SZ"
                        )

                        row = (
                            float(order["qty"]),
                            float(order["price"]),
                            orderside,
                            positionside,
                            order["order_status"],
                            order["symbol"],
                            int(time_format.timestamp() * 1000),
                            order["order_type"],
                        )
                        create_orders(conn, row)

            params = {"api_key": current_app.config["API_KEY"], "coin": "USDT"}
            responseHeader, responseJSON = send_signed_request(
                "GET", "/v2/private/wallet/balance", params, signature="sign"
            )

            totals_row = (
                float(responseJSON["result"]["USDT"]["wallet_balance"]),
                float(responseJSON["result"]["USDT"]["unrealised_pnl"]),
                float(responseJSON["result"]["USDT"]["used_margin"]),
                float(responseJSON["result"]["USDT"]["available_balance"]),
                float(0),
                1,
            )

            accountCheck = select_account(conn)
            if accountCheck is None:
                create_account(conn, totals_row)
            elif float(accountCheck[0]) != float(responseJSON["result"]["USDT"]["wallet_balance"]):
                update_account(conn, totals_row)

            conn.commit()

        all_symbols = sorted(all_symbols)

        for symbol in all_symbols:
            trades = {}
            params = {"api_key": current_app.config["API_KEY"], "symbol": symbol, "limit": 50}
            with create_connection(current_app.config["DATABASE"]) as conn:
                startTime = select_latest_income_symbol(conn, symbol)
                if startTime is None:
                    startTime = int(
                        datetime.datetime.fromisoformat("2020-01-01 00:00:00+00:00").timestamp()
                    )
                    params["start_time"] = startTime
                else:
                    startTime = int(startTime[0]) / 1000
                    params["start_time"] = int(startTime + 1)

            for page in range(1, 50):
                if weightused < 20:
                    print(f"Weight used: {weightused}/100\nProcessed: {processed}\nSleep: 1 minute")
                    sleeps += 1
                    time.sleep(60)
                params["page"] = page
                responseHeader, responseJSON = send_signed_request(
                    "GET", "/private/linear/trade/closed-pnl/list", params, signature="sign"
                )
                if "rate_limit_status" in responseJSON:
                    weightused = int(responseJSON["rate_limit_status"])

                if responseJSON["result"] is not None:
                    if responseJSON["result"]["data"] is not None:
                        for trade in responseJSON["result"]["data"]:
                            trades[trade["created_at"]] = [
                                trade["id"],
                                trade["exec_type"],
                                trade["closed_pnl"],
                                trade["order_id"],
                            ]
                        if len(responseJSON["result"]["data"]) < 50:
                            break
                    else:
                        break
                else:
                    break

            if len(trades) > 0:
                trades = OrderedDict(sorted(trades.items()))
                with create_connection(current_app.config["DATABASE"]) as conn:
                    for trade in trades:
                        income_row = (
                            int(trades[trade][0]),
                            symbol,
                            exec_type[trades[trade][1]],
                            trades[trade][2],
                            "USDT",
                            exec_type[trades[trade][1]],
                            int(trade * 1000),
                            int(trades[trade][0]),
                        )

                        create_income(conn, income_row)
                        processed += 1
                    conn.commit()
    else:
        current_app.logger.info(
            "Exchange; %s is not currently supported", current_app.config["EXCHANGE"]
        )

    elapsed = time.time() - start
    if app is not None:
        current_app.logger.info(
            "Orders updated: %s; Positions updated: %s (new: %s); Trades processed: %s; Time elapsed: %s; Sleeps: %s",
            updated_orders,
            updated_positions,
            new_positions,
            processed,
            timedelta(seconds=elapsed),
            sleeps,
        )
    else:
        print(
            "Orders updated: {}\nPositions updated: {} (new: {})\nTrades processed: {}\nTime elapsed: {}\nSleeps: {}".format(
                updated_orders,
                updated_positions,
                new_positions,
                processed,
                timedelta(seconds=elapsed),
                sleeps,
            )
        )
