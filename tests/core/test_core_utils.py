import unittest

import requests  # type: ignore
import responses
from freezegun import freeze_time

from futuresboard.core.utils import (
    BlankResponse,
    HTTPRequestError,
    end_datetime_ago,
    end_milliseconds_ago,
    send_public_request,
    start_datetime_ago,
    start_milliseconds_ago,
)


class TestCoreUtils(unittest.TestCase):
    def test_BlankResponse(self):
        blank = BlankResponse()
        assert blank.content == ""

    @freeze_time("2022-12-25")
    def test_start_datetime_ago(self):
        assert start_datetime_ago(5) == "2022-12-20 00:00:00"

    @freeze_time("2022-12-25")
    def test_end_datetime_ago(self):
        assert end_datetime_ago(5) == "2022-12-20 23:59:59"

    @freeze_time("2022-12-25")
    def test_start_milliseconds_ago(self):
        assert start_milliseconds_ago(5) == 1671494400000

    @freeze_time("2022-12-25")
    def test_end_millseconds_ago(self):
        assert end_milliseconds_ago(5) == 1671580799999

    @responses.activate
    def test_payload(self):
        responses.get(
            url="http://api.futuresboard.com/test?limit=5",
            body='{"value": "5"}',
            status=200,
            content_type="application/json",
            headers={"X-MBX-USED-WEIGHT-1M": "1"},
        )
        headers, json_response = send_public_request(
            url="http://api.futuresboard.com/", url_path="test", payload={"limit": 5}
        )
        assert headers == {
            "Content-Type": "application/json",
            "X-MBX-USED-WEIGHT-1M": "1",
        }
        assert json_response == {"value": "5"}

    def test_HTTPRequestError_direct(self):
        error = HTTPRequestError(
            url="http://api.futuresboard.com/error", code=429, msg="Rate limited"
        )
        assert (
            error.__str__()
            == "Request to 'http://api.futuresboard.com/error' failed. Code: 429; Message: Rate limited"
        )

    @responses.activate
    def test_HTTPRequestError_indirect(self):
        responses.get(
            url="http://api.futuresboard.com/error",
            body='{"code": "429", "msg": "Rate limited"}',
            status=200,
            content_type="application/json",
            headers={"X-MBX-USED-WEIGHT-1M": "1"},
        )
        header, response = send_public_request(
            url="http://api.futuresboard.com/", url_path="error"
        )
        assert header == ""
        assert response == ""

    @responses.activate
    def test_Timeout_exception(self):
        responses.get(
            url="http://api.futuresboard.com/error",
            body=requests.exceptions.Timeout(),
            status=200,
            content_type="application/json",
            headers={"X-MBX-USED-WEIGHT-1M": "1"},
        )
        headers, json_response = send_public_request(
            url="http://api.futuresboard.com/", url_path="error"
        )
        assert headers == ""
        assert json_response == ""

    @responses.activate
    def test_toomanyredirects_exception(self):
        responses.get(
            url="http://api.futuresboard.com/error",
            body=requests.exceptions.TooManyRedirects(),
            status=200,
            content_type="application/json",
            headers={"X-MBX-USED-WEIGHT-1M": "1"},
        )
        headers, json_response = send_public_request(
            url="http://api.futuresboard.com/", url_path="error"
        )
        assert headers == ""
        assert json_response == ""

    @responses.activate
    def test_request_exception(self):
        responses.get(
            url="http://api.futuresboard.com/error",
            body=requests.exceptions.RequestException(),
            status=200,
            content_type="application/json",
            headers={"X-MBX-USED-WEIGHT-1M": "1"},
        )
        headers, json_response = send_public_request(
            url="http://api.futuresboard.com/", url_path="error"
        )
        assert headers == ""
        assert json_response == ""


if __name__ == "__main__":
    unittest.main()
