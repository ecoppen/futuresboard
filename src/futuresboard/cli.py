from __future__ import annotations

import argparse
import logging
import pathlib
import sys

import futuresboard.app
import futuresboard.scraper
from futuresboard import __version__  # type: ignore[attr-defined]
from futuresboard.config import Config

log = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(prog="futuresboard")
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
    server_settings.add_argument(
        "--host", default='0.0.0.0', help="Server host. Default: 0.0.0.0"
    )
    server_settings.add_argument(
        "--port", type=int, default=None, help="Server port. Default: 5000"
    )
    args = parser.parse_args()

    if args.config_dir is None:
        args.config_dir = pathlib.Path.cwd() / "config"
    else:
        args.config_dir = args.config_dir.resolve()

    config = Config.from_config_dir(args.config_dir)
    if not args.host:
        args.host = config.HOST
    if not args.port:
        args.port = config.PORT

    # Run the application
    app = futuresboard.app.init_app(config)

    if args.scrape_only:
        with app.app_context():
            futuresboard.scraper.scrape()
        sys.exit(0)

    app.run(host=args.host, port=args.port)
