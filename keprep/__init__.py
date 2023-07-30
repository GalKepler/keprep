# mypy: disable-error-code="attr-defined"
"""Pre-processing for TheBase's dMRI data."""

from importlib import metadata as importlib_metadata

from keprep.__about__ import __copyright__, __credits__, __packagename__, __version__


def get_version() -> str:
    try:
        return importlib_metadata.version(__name__)
    except importlib_metadata.PackageNotFoundError:  # pragma: no cover
        return "unknown"


version: str = get_version()

"""Top-module metadata."""


__all__ = [
    "__copyright__",
    "__credits__",
    "__packagename__",
    "__version__",
]
