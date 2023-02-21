#
from __future__ import annotations

import pathlib

PACKAGE_ROOT = pathlib.Path(__file__).resolve().parent
try:
    from .version import __version__
except ImportError:  # pragma: no cover
    __version__ = "0.0.0.not-installed"
    try:
        from importlib.metadata import PackageNotFoundError, version

        try:
            __version__ = version("futuresboard")
        except PackageNotFoundError:
            # package is not installed
            pass
    except ImportError:
        try:
            from pkg_resources import (  # type: ignore
                DistributionNotFound,
                get_distribution,
            )

            try:
                __version__ = get_distribution("futuresboard").version
            except DistributionNotFound:
                # package is not installed
                pass
        except ImportError:
            # pkg resources isn't even available?!
            pass
