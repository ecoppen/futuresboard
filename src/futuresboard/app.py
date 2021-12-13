from __future__ import annotations

import json
import logging
import pathlib

from flask import Flask
from flask import redirect
from flask import request

import futuresboard.scraper
from futuresboard import blueprint
from futuresboard import db
from futuresboard.config import Config


def clear_trailing():
    rp = request.path
    if rp != "/" and rp.endswith("/"):
        return redirect(rp[:-1])


def init_app(config: Config | None = None):
    if config is None:
        config = Config.from_config_dir(pathlib.Path.cwd())

    app = Flask(__name__)
    app.config.from_mapping(**json.loads(config.json()))
    app.url_map.strict_slashes = False
    db.init_app(app)
    app.before_request(clear_trailing)
    app.register_blueprint(blueprint.app)

    if config.DISABLE_AUTO_SCRAPE is False:
        futuresboard.scraper.auto_scrape(app)

    app.logger.setLevel(logging.INFO)

    return app
