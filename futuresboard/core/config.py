from __future__ import annotations

import json
from enum import Enum

from pydantic import BaseModel, Field, IPvAnyAddress, ValidationError, validator

from futuresboard.exchange.utils import Exchanges


class Databases(Enum):
    POSTGRES = "postgres"
    SQLITE = "sqlite"


class Database(BaseModel):
    engine: str = Databases.SQLITE.value  # type: ignore
    username: str | None
    password: str | None
    host: IPvAnyAddress = IPvAnyAddress.validate("127.0.0.1")  # type: ignore
    port: int = Field(5432, ge=1, le=65535)
    name: str = "futuresboard"


class Account(BaseModel):
    id: int = Field(0, const=True)
    name: str
    exchange: str = Exchanges.BINANCE.value  # type: ignore
    api_key: str = Field(min_length=5)
    api_secret: str = Field(min_length=5)


class Config(BaseModel):
    accounts: list[Account]
    scrape_interval: int = 600
    database: Database
    dashboard_name: str = "futuresboard"
    log_level: str = "info"
    news_source: list[Exchanges] = ["binance", "bybit", "okx"]  # type: ignore

    @validator("accounts")
    def duplicate_accounts(cls, v):
        names = [acc.name for acc in v]
        unique_names = set(names)
        if len(names) != len(unique_names):
            raise ValueError("Each account must be uniquely named")
        return v

    @validator("news_source")
    def duplicate_news_source(cls, v):
        unique_sources = set(v)
        if len(v) != len(unique_sources):
            raise ValueError("Each news source must be uniquely named")
        return v

    @validator("scrape_interval")
    def interval_amount(cls, v):
        if v < 60:
            raise ValueError("Scraping interval lower limit is 60 (1 minute)")
        return v


def load_config(path):
    if not path.is_file():
        raise ValueError(f"{path} does not exist")
    else:
        f = open(path)
        try:
            data = json.load(f)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"ERROR: Invalid JSON: {exc.msg}, line {exc.lineno}, column {exc.colno}"
            )
        try:
            return Config(**data)
        except ValidationError as e:
            raise ValueError(f"{e}")
