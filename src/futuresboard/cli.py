from __future__ import annotations

import argparse
import json
import logging
import pathlib
import sys
import threading
import time

from xyzboard import __version__
from xyzboard import scraper
from xyzboard.app import app

log = logging.getLogger(__name__)


def auto_scrape():
    while True:
        app.logger.info("Auto scrape routines starting")
        scraper.scrape(auto_scrape=True)
        app.logger.info(
            "Auto scrape routines terninated. Sleeping %s seconds...",
            app.config["AUTO_SCRAPE_INTERVAL"],
        )
        time.sleep(app.config["AUTO_SCRAPE_INTERVAL"])


def main():
    parser = argparse.ArgumentParser(prog="xyzboard")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument(
        "-c",
        "--config-dir",
        type=pathlib.Path,
        default=None,
        help="Path to configuration directory. Defaults to the `config/` sub-directory on the current directory",
    )
    parser.add_argument(
        "--scrape-only", default=False, action="store_true", help="Run only the scraper code"
    )
    parser.add_argument(
        "--disable-auto-scraper",
        default=False,
        action="store_true",
        help="Disable the routines which scrape while the webservice is running",
    )
    server_settings = parser.add_argument_group("Server Settings")
    server_settings.add_argument("--host", default="0.0.0.0", help="Server host. Default: %default")
    server_settings.add_argument(
        "--port", type=int, default=5000, help="Server port. Default: %default"
    )
    args = parser.parse_args()

    app.logger.setLevel(logging.INFO)
    if args.config_dir is None:
        args.config_dir = pathlib.Path.cwd() / "config"
    else:
        args.config_dir = args.config_dir.resolve()
    app.config["CONFIG_DIR"] = args.config_dir

    config_file = args.config_dir / "config.json"
    for key, value in json.loads(config_file.read_text()).items():
        if key == "database":
            value = pathlib.Path(value).resolve()
        app.config[key.upper()] = value

    if "DATABASE" not in app.config:
        app.config["DATABASE"] = f"{args.config_dir / 'futures.db'}"

    if "API_BASE_URL" not in app.config:
        base_url = "https://fapi.binance.com"  # production base url
        # base_url = 'https://testnet.binancefuture.com' # testnet base url
        app.config["API_BASE_URL"] = base_url

    if "AUTO_SCRAPE_INTERVAL" not in app.config:
        app.config["AUTO_SCRAPE_INTERVAL"] = 5 * 60

    if args.scrape_only:
        scraper.scrape()
        sys.exit(0)

    if args.disable_auto_scraper is False:
        thread = threading.Thread(target=auto_scrape)
        thread.daemon = True
        thread.start()

    # Run the application
    app.run(host=args.host, port=args.port)
