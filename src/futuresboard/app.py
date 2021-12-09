from __future__ import annotations

import json
import logging
import pathlib
from typing import Any

from flask import Flask
from flask import redirect
from flask import request

import futuresboard.scraper
from futuresboard import blueprint
from futuresboard import db


def clear_trailing():
    rp = request.path
    if rp != "/" and rp.endswith("/"):
        return redirect(rp[:-1])


def init_app(config: dict[str, Any] | None = None):
    if config is None:
        config_dir = pathlib.Path.cwd()
        config = {"CONFIG_DIR": config_dir, "DISABLE_AUTO_SCRAPE": False}

        config_file = config_dir / "config.json"
        for key, value in json.loads(config_file.read_text()).items():
            if key == "database":
                value = pathlib.Path(value).resolve()
            config[key.upper()] = value

        if "DATABASE" not in config:
            config["DATABASE"] = f"{config_dir / 'futures.db'}"

        if "EXCHANGE" not in config:
            base_url = "https://fapi.binance.com"
        else:
            if config["EXCHANGE"] == "binance":
                base_url = "https://fapi.binance.com"
            else:
                base_url = "https://fapi.binance.com"  # alternatives here later

        config["API_BASE_URL"] = base_url

        if "AUTO_SCRAPE_INTERVAL" not in config:
            config["AUTO_SCRAPE_INTERVAL"] = 5 * 60
        else:
            try:
                interval = int(config["AUTO_SCRAPE_INTERVAL"])
                if interval < 60 or interval > 3600:
                    config["AUTO_SCRAPE_INTERVAL"] = 5 * 60
            except TypeError:
                config["AUTO_SCRAPE_INTERVAL"] = 5 * 60

        if "CUSTOM" not in config:
            config["CUSTOM"]["NAVBAR_TITLE"] = "Futuresboard"
            config["CUSTOM"]["NAVBAR_BG"] = "bg-dark"
            config["CUSTOM"]["PROJECTIONS"] = [1.003, 1.005, 1.01, 1.012]
        else:
            if len(config["CUSTOM"]["NAVBAR_TITLE"]) < 1 or len(config["NAVBAR_TITLE"]) > 50:
                config["CUSTOM"]["NAVBAR_TITLE"] = "Futuresboard"
            if config["CUSTOM"]["NAVBAR_BG"] not in [
                "bg-primary",
                "bg-secondary",
                "bg-success",
                "bg-danger",
                "bg-warning",
                "bg-info",
                "bg-light",
            ]:
                config["CUSTOM"]["NAVBAR_BG"] = "bg-dark"
            if not isinstance(config["CUSTOM"]["PROJECTIONS"], list):
                config["CUSTOM"]["PROJECTIONS"] = [1.003, 1.005, 1.01, 1.012]
            else:
                temp = []
                for percentage in config["CUSTOM"]["PROJECTIONS"]:
                    try:
                        percentage = float(percentage)
                        if percentage > -3.0 and percentage < 3.0:
                            temp.append(percentage)
                    except TypeError:
                        pass
                config["CUSTOM"]["PROJECTIONS"] = temp

    app = Flask(__name__)
    app.config.from_mapping(**config)
    app.url_map.strict_slashes = False
    db.init_app(app)
    app.before_request(clear_trailing)
    app.register_blueprint(blueprint.app)

    if config["DISABLE_AUTO_SCRAPE"] is False:
        futuresboard.scraper.auto_scrape(app)

    app.logger.setLevel(logging.INFO)

    return app
