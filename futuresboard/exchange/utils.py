import logging
from enum import Enum

import requests  # type: ignore

log = logging.getLogger(__name__)


class Exchanges(str, Enum):
    BINANCE = "binance"
    BYBIT = "bybit"


class Markets(str, Enum):
    FUTURES = "FUTURES"


class Intervals(str, Enum):
    ONE_MINUTE = "1m"
    FIVE_MINUTES = "5m"
    FIFTEEN_MINUTES = "15m"
    ONE_HOUR = "1h"
    FOUR_HOURS = "4h"
    ONE_DAY = "1d"
    ONE_WEEK = "1w"
