from __future__ import annotations

import json
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

        if "API_BASE_URL" not in config:
            base_url = "https://fapi.binance.com"  # production base url
            # base_url = 'https://testnet.binancefuture.com' # testnet base url
            config["API_BASE_URL"] = base_url

        if "AUTO_SCRAPE_INTERVAL" not in config:
            config["AUTO_SCRAPE_INTERVAL"] = 5 * 60

    app = Flask(__name__)
    app.config.from_mapping(**config)
    app.url_map.strict_slashes = False
    db.init_app(app)
    app.before_request(clear_trailing)
    app.register_blueprint(blueprint.app)

    if config["DISABLE_AUTO_SCRAPE"] is False:
        futuresboard.scraper.auto_scrape(app)

    return app
