from __future__ import annotations

import hashlib
import hmac
import json
import logging
import re
import time
from collections import OrderedDict
from datetime import date, datetime, timedelta
from urllib.parse import urlencode

import requests  # type: ignore

log = logging.getLogger(__name__)


class HTTPRequestError(Exception):
    def __init__(self, url, code, msg=None):
        self.url = url
        self.code = code
        self.msg = msg

    def __str__(self) -> str:
        return f"Request to {self.url!r} failed. Code: {self.code}; Message: {self.msg}"


class BlankResponse:
    def __init__(self):
        self.content = ""


def get_timestamp():
    return int(time.time() * 1000)


def hashing(
    query_string: str,
    exchange: str = "binance",
    timestamp: int = -1,
    keys: dict | None = None,
):
    if keys is None:
        keys = {"key": "", "secret": ""}
    if exchange == "bybit":
        query_string = f"{timestamp}{keys['key']}5000" + query_string
        return hmac.new(
            bytes(keys["secret"].encode("utf-8")),
            query_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
    return hmac.new(
        bytes(keys["secret"].encode("utf-8")),
        query_string.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def dispatch_request(
    http_method: str,
    key: str = "",
    signature: str = "",
    timestamp: int = -1,
):
    session = requests.Session()
    session.headers.update(
        {
            "Content-Type": "application/json;charset=utf-8",
            "X-MBX-APIKEY": f"{key}",
            "X-BAPI-API-KEY": f"{key}",
            "X-BAPI-SIGN": f"{signature}",
            "X-BAPI-SIGN-TYPE": "2",
            "X-BAPI-TIMESTAMP": f"{timestamp}",
            "X-BAPI-RECV-WINDOW": "5000",
        }
    )
    return {
        "GET": session.get,
        "DELETE": session.delete,
        "PUT": session.put,
        "POST": session.post,
    }.get(http_method, "GET")


def send_public_request(
    url: str,
    method: str = "GET",
    url_path: str | None = None,
    payload: dict | None = None,
    json: bool = True,
):
    empty_response = BlankResponse().content
    if url_path is not None:
        url += url_path
    if payload is None:
        payload = {}
    query_string = urlencode(payload, True)
    if query_string:
        url = url + "?" + query_string

    log.debug(f"Requesting {url}")

    try:
        response = dispatch_request(method)(
            url=url,
            timeout=5,
        )
        headers = response.headers
        if not json:
            return headers, response.text
        json_response = response.json()
        if "code" in json_response and "msg" in json_response:
            if len(json_response["msg"]) > 0:
                raise HTTPRequestError(
                    url=url, code=json_response["code"], msg=json_response["msg"]
                )
        if "retCode" in json_response:
            if json_response["retCode"] != 0:
                raise HTTPRequestError(
                    url=url, code=json_response["retCode"], msg=json_response["retMsg"]
                )
        return headers, json_response
    except requests.exceptions.ConnectionError:
        log.warning("Connection error")
    except requests.exceptions.Timeout:
        log.warning("Request timed out")
    except requests.exceptions.TooManyRedirects:
        log.warning("Too many redirects")
    except requests.exceptions.JSONDecodeError as e:
        log.warning(f"JSON decode error: {e}")
    except requests.exceptions.RequestException as e:
        log.warning(f"Request exception: {e}")
    except HTTPRequestError as e:
        log.warning(f"HTTP Request error: {e}")
    return empty_response, empty_response


def send_signed_request(
    http_method: str,
    url_path: str,
    payload: dict | None = None,
    exchange: str = "binance",
    base_url=str,
    keys: dict | None = None,
):
    empty_response = BlankResponse().content
    if keys is None:
        keys = {"key": "", "secret": ""}
    if payload is None:
        payload = {}
    timestamp = get_timestamp()
    if exchange == "binance":
        payload["timestamp"] = timestamp

    query_string = urlencode(OrderedDict(sorted(payload.items())))
    query_string = query_string.replace("%27", "%22")

    url = f"{base_url}{url_path}?{query_string}"
    if exchange == "binance":
        url += f"&signature={hashing(query_string=query_string, exchange=exchange, keys=keys)}"
    params = {"url": url, "params": {}}

    log.debug(f"Requesting {url}")
    try:
        response = dispatch_request(
            http_method=http_method,
            key=keys["key"],
            signature=hashing(
                query_string=query_string,
                exchange=exchange,
                timestamp=timestamp,
                keys=keys,
            ),
            timestamp=timestamp,
        )(**params)
        headers = response.headers
        json_response = response.json()
        if "code" in json_response:
            raise HTTPRequestError(
                url=url, code=json_response["code"], msg=json_response["msg"]
            )
        if "retCode" in json_response:
            if json_response["retCode"] != 0:
                raise HTTPRequestError(
                    url=url, code=json_response["retCode"], msg=json_response["retMsg"]
                )
        return headers, json_response
    except requests.exceptions.ConnectionError:
        log.warning("Connection error")
    except requests.exceptions.Timeout:
        log.warning("Request timed out")
    except requests.exceptions.TooManyRedirects:
        log.warning("Too many redirects")
    except requests.exceptions.RequestException as e:
        log.warning(f"Request exception: {e}")
    except requests.exceptions.JSONDecodeError as e:
        log.warning(f"JSON decode error: {e}")
    except HTTPRequestError as e:
        log.warning(f"HTTP Request error: {e}")
    return empty_response, empty_response


def start_datetime_ago(days: int) -> str:
    start_datetime = datetime.combine(
        datetime.now() - timedelta(days=days), datetime.min.time()
    )
    return start_datetime.strftime("%Y-%m-%d %H:%M:%S")


def end_datetime_ago(days: int) -> str:
    start_datetime = datetime.combine(
        datetime.now() - timedelta(days=days), datetime.max.time()
    )
    return start_datetime.strftime("%Y-%m-%d %H:%M:%S")


def start_milliseconds_ago(days: int) -> int:
    start_datetime = datetime.combine(
        datetime.now() - timedelta(days=days), datetime.min.time()
    )
    return int(start_datetime.timestamp() * 1000)


def end_milliseconds_ago(days: int) -> int:
    start_datetime = datetime.combine(
        datetime.now() - timedelta(days=days), datetime.max.time()
    )
    return int(start_datetime.timestamp() * 1000)


def find_in_string(
    string: str,
    start_substring: str,
    end_substring: str | None = None,
    return_json: bool = False,
):
    text = ""
    start_index = string.find(start_substring)
    if start_index > -1:
        if end_substring is None:
            text = string[start_index + len(start_substring) :]
        else:
            end_index = string.find(end_substring, start_index + len(start_substring))
            if end_index > -1:
                text = string[start_index + len(start_substring) : end_index]
        if len(text) > 0 and return_json:
            try:
                text = json.loads(text)
            except ValueError as e:
                log.warning(f"JSON decode error: {e}")
    return text


def find_all_occurrences_in_string(
    string: str, start_substring: str, end_substring: str
) -> list:
    occurences = []
    start_index = string.find(start_substring)
    while start_index > -1:
        end_index = string.find(end_substring, start_index + len(start_substring))
        if end_index == -1:
            break
        text = string[start_index + len(start_substring) : end_index]
        occurences.append(text)
        start_index = string.find(start_substring, start_index + 1)
    return occurences


def remove_non_alphanumeric(string: str) -> str:
    return re.sub("[^0-9a-zA-Z ]+", "", string)


def dt_to_ts(date) -> int:
    return int(date.timestamp() * 1000)


def string_to_dt(string: str, format: str = "%Y-%m-%d %H:%M:%S"):
    return datetime.strptime(string, format)


def start_end_timerange_helper(start, end) -> dict:
    template = {
        "start_string": start.strftime("%Y-%m-%d 00:00:00"),
        "end_string": end.strftime("%Y-%m-%d 23:59:59"),
        "start_ts": 0,
        "end_ts": 0,
    }
    template["start_ts"] = dt_to_ts(date=string_to_dt(string=template["start_string"]))
    template["end_ts"] = dt_to_ts(date=string_to_dt(string=template["end_string"]))
    return template


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
    last_year_start = (
        (this_year_start - timedelta(days=1)).replace(day=1).replace(month=1)
    )
    last_year_end = this_year_start - timedelta(days=1)

    return {
        "today": start_end_timerange_helper(start=today, end=today),
        "yesterday": start_end_timerange_helper(
            start=yesterday_start, end=yesterday_start
        ),
        "this_week": start_end_timerange_helper(start=this_week_start, end=today),
        "last_week": start_end_timerange_helper(
            start=last_week_start, end=last_week_end
        ),
        "this_month": start_end_timerange_helper(start=this_month_start, end=today),
        "last_month": start_end_timerange_helper(
            start=last_month_start, end=last_month_end
        ),
        "this_year": start_end_timerange_helper(start=this_year_start, end=today),
        "last_year": start_end_timerange_helper(
            start=last_year_start, end=last_year_end
        ),
    }
