# https://github.com/binance/binance-signature-examples

import hmac
import time
import hashlib
import requests
import json
import datetime
import sqlite3

from datetime import timedelta
from sqlite3 import Error
from urllib.parse import urlencode

with open("config.json") as json_file:
    data = json.load(json_file)

KEY = data["api_key"]
SECRET = data["api_secret"]
BASE_URL = "https://fapi.binance.com"  # production base url
# BASE_URL = 'https://testnet.binancefuture.com' # testnet base url


def hashing(query_string):
    return hmac.new(
        SECRET.encode("utf-8"), query_string.encode("utf-8"), hashlib.sha256
    ).hexdigest()


def get_timestamp():
    return int(time.time() * 1000)


def dispatch_request(http_method):
    session = requests.Session()
    session.headers.update(
        {"Content-Type": "application/json;charset=utf-8", "X-MBX-APIKEY": KEY}
    )
    return {
        "GET": session.get,
        "DELETE": session.delete,
        "PUT": session.put,
        "POST": session.post,
    }.get(http_method, "GET")


# used for sending request requires the signature
def send_signed_request(http_method, url_path, payload={}):
    query_string = urlencode(payload)
    # replace single quote to double quote
    query_string = query_string.replace("%27", "%22")
    if query_string:
        query_string = "{}&timestamp={}".format(query_string, get_timestamp())
    else:
        query_string = "timestamp={}".format(get_timestamp())

    url = (
        BASE_URL + url_path + "?" + query_string + "&signature=" + hashing(query_string)
    )
    # print("{} {}".format(http_method, url))
    params = {"url": url, "params": {}}
    response = dispatch_request(http_method)(**params)
    return response.headers, response.json()


# used for sending public data request
def send_public_request(url_path, payload={}):
    query_string = urlencode(payload, True)
    url = BASE_URL + url_path
    if query_string:
        url = url + "?" + query_string
    # print("{}".format(url))
    response = dispatch_request("GET")(url=url)
    return response.headers, response.json()


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
                                        tradeId integer
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


# position interactions
def create_position(conn, position):
    sql = """ INSERT INTO positions(unrealizedProfit, leverage, entryPrice, positionAmt, symbol, positionSide) VALUES(?,?,?,?,?,?) """
    cur = conn.cursor()
    cur.execute(sql, position)


def update_position(conn, position):
    sql = """ UPDATE positions SET unrealizedProfit = ?, leverage = ?, entryPrice = ?, positionAmt = ? WHERE symbol = ? AND positionSide = ? """
    cur = conn.cursor()
    cur.execute(sql, position)


def select_position(conn, symbol):
    cur = conn.cursor()
    cur.execute(
        "SELECT unrealizedProfit FROM positions WHERE symbol = ? LIMIT 0, 1", (symbol,)
    )
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


if __name__ == "__main__":
    start = time.time()
    database = r"futures.db"
    db_setup(database)

    up_to_date = False
    weightused = 0
    processed, updated_positions, new_positions, updated_orders = 0, 0, 0, 0
    sleeps = 0

    if weightused < 800:
        responseHeader, responseJSON = send_signed_request("GET", "/fapi/v1/openOrders")
        weightused = int(responseHeader["X-MBX-USED-WEIGHT-1M"])

        conn = create_connection(database)
        with conn:
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
    positions = responseJSON["positions"]

    conn = create_connection(database)
    with conn:
        row = (
            float(responseJSON["totalWalletBalance"]),
            float(responseJSON["totalUnrealizedProfit"]),
            float(responseJSON["totalMarginBalance"]),
            float(responseJSON["availableBalance"]),
            float(responseJSON["maxWithdrawAmount"]),
            1,
        )
        accountCheck = select_account(conn)
        if accountCheck is None:
            create_account(conn, row)
        elif float(accountCheck[0]) != float(responseJSON["totalWalletBalance"]):
            update_account(conn, row)

        for position in positions:
            row = (
                float(position["unrealizedProfit"]),
                int(position["leverage"]),
                float(position["entryPrice"]),
                float(position["positionAmt"]),
                position["symbol"],
                position["positionSide"],
            )
            unrealizedProfit = select_position(conn, position["symbol"])
            if unrealizedProfit is None:
                create_position(conn, row)
                new_positions += 1
            elif float(unrealizedProfit[0]) != float(position["unrealizedProfit"]):
                update_position(conn, row)
                updated_positions += 1

        conn.commit()

    while not up_to_date:
        if weightused > 800:
            print(
                "Weight used: {}/800\nProcessed: {}\nSleep: 1 minute".format(
                    weightused, processed
                )
            )
            sleeps += 1
            time.sleep(60)

        conn = create_connection(database)
        with conn:
            startTime = select_latest_income(conn)
            if startTime == None:
                startTime = int(
                    datetime.datetime.fromisoformat(
                        "2020-01-01 00:00:00+00:00"
                    ).timestamp()
                    * 1000
                )
            else:
                startTime = startTime[0]
            params = {"startTime": startTime + 1, "limit": 1000}

            responseHeader, responseJSON = send_signed_request(
                "GET", "/fapi/v1/income", params
            )
            weightused = int(responseHeader["X-MBX-USED-WEIGHT-1M"])

            if len(responseJSON) == 0:
                up_to_date = True
            else:
                for income in responseJSON:
                    if len(income["tradeId"]) == 0:
                        income["tradeId"] = 0
                    row = (
                        int(income["tranId"]),
                        income["symbol"],
                        income["incomeType"],
                        income["income"],
                        income["asset"],
                        income["info"],
                        int(income["time"]),
                        int(income["tradeId"]),
                    )
                    create_income(conn, row)
                    processed += 1

                conn.commit()

    elapsed = time.time() - start
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
