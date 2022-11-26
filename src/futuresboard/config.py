from __future__ import annotations

import copy
import enum
import json
import pathlib
from typing import List
from typing import Optional

from pydantic import BaseModel
from pydantic import DirectoryPath
from pydantic import Field
from pydantic import IPvAnyInterface
from pydantic import root_validator
from pydantic import validator


class NavbarBG(enum.Enum):
    BG_DARK = "bg-dark"
    BG_PRIMARY = "bg-primary"
    BG_SECONDARY = "bg-secondary"
    BG_SUCCESS = "bg-success"
    BG_DANGER = "bg-danger"
    BG_WARNING = "bg-warning"
    BG_INFO = "bg-info"
    BG_LIGHT = "bg-light"


class Exchanges(enum.Enum):
    BINANCE = "binance"
    BYBIT = "bybit"


class Custom(BaseModel):
    NAVBAR_TITLE: Optional[str] = Field("Futuresboard", min_length=1, max_length=50)
    NAVBAR_BG: Optional[NavbarBG] = NavbarBG.BG_DARK
    PROJECTIONS: List[float] = Field([1.003, 1.005, 1.01, 1.012], min_items=1, max_items=10)

    @validator("PROJECTIONS", each_item=True)
    @classmethod
    def _validate_projections(cls, value):
        if not isinstance(value, float):
            try:
                value = float(value)
            except TypeError:
                raise ValueError(f"Cannot cast {value!r} to a float")
        if value < -3.0:
            raise ValueError("The lower allowed projection value is -3.0")
        if value > 3.0:
            raise ValueError("The upper allowed projection value is 3.0")
        return value


class Config(BaseModel):
    CONFIG_DIR: DirectoryPath = pathlib.Path.cwd()
    DATABASE: Optional[pathlib.Path]
    EXCHANGE: Optional[Exchanges] = Exchanges.BINANCE
    TEST_MODE: Optional[bool] = False
    API_BASE_URL: Optional[str]
    AUTO_SCRAPE_INTERVAL: int = 300
    DISABLE_AUTO_SCRAPE: bool = False
    HOST: Optional[IPvAnyInterface] = IPvAnyInterface.validate("0.0.0.0")  # type: ignore[assignment]
    PORT: Optional[int] = Field(5000, ge=1, le=65535)
    API_KEY: str
    API_SECRET: str

    CUSTOM: Optional[Custom] = Custom()

    @validator("DATABASE", always=True)
    @classmethod
    def _validate_database(cls, value, values):
        if not value:
            value = values["CONFIG_DIR"] / "futures.db"
        return value.resolve()

    @validator("API_BASE_URL", always=True)
    @classmethod
    def _validate_api_base_url(cls, value, values):
        if not value:
            if values["EXCHANGE"] == Exchanges.BINANCE:
                if values["TEST_MODE"]:
                    value = "https://testnet.binancefuture.com"
                else:
                    value = "https://fapi.binance.com"
            elif values["EXCHANGE"] == Exchanges.BYBIT:
                if values["TEST_MODE"]:
                    value = "https://api-testnet.bybit.com"
                else:
                    value = "https://api.bybit.com"
        return value

    @validator("AUTO_SCRAPE_INTERVAL")
    @classmethod
    def _validate_projections(cls, value):
        if value < 60:
            raise ValueError("The lower allowed value is 60")
        if value > 3600:
            raise ValueError("The upper allowed value is 3600")
        return value

    @root_validator(pre=True)
    @classmethod
    def _capitalize_all_keys(cls, fields):
        def _capitalize_keys(c):
            if not isinstance(c, dict):
                return c
            for key, value in copy.deepcopy(c).items():
                if isinstance(value, dict):
                    _capitalize_keys(value)
                c[key.upper()] = value
                if not key.isupper():
                    c.pop(key)

        for key, value in copy.deepcopy(fields).items():
            _capitalize_keys(value)
            fields[key.upper()] = value
            if not key.isupper():
                fields.pop(key)

        return fields

    @classmethod
    def from_config_dir(cls, config_dir: pathlib.Path) -> Config:
        config_file = config_dir / "config.json"
        if config_file.exists():
            config_dict = json.loads(config_file.read_text())
        else:
            config_dict = {}
        config_dict["CONFIG_DIR"] = config_dir
        return cls.parse_obj(config_dict)
