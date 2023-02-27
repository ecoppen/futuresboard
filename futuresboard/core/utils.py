from __future__ import annotations

import logging
from datetime import datetime, timedelta
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


def dispatch_request(http_method, key=None):
    session = requests.Session()
    session.headers.update(
        {
            "Content-Type": "application/json;charset=utf-8",
            "X-MBX-APIKEY": key,
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
):
    empty_response = BlankResponse().content
    if url_path is not None:
        url += url_path
    if payload is None:
        payload = {}
    query_string = urlencode(payload, True)
    if query_string:
        url = url + "?" + query_string

    log.info(f"Requesting {url}")

    try:
        response = dispatch_request(method)(
            url=url,
            timeout=5,
        )
        headers = response.headers
        json_response = response.json()
        if "code" in json_response and "msg" in json_response:
            if len(json_response["msg"]) > 0:
                raise HTTPRequestError(
                    url=url, code=json_response["code"], msg=json_response["msg"]
                )
        return headers, json_response
    except requests.exceptions.Timeout:
        log.info("Request timed out")
        return empty_response, empty_response
    except requests.exceptions.TooManyRedirects:
        log.info("Too many redirects")
        return empty_response, empty_response
    except requests.exceptions.RequestException as e:
        log.info(f"Request exception: {e}")
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
