"""Base module variables."""

try:
    from keprep._version import __version__
except ImportError:
    __version__ = "0.0.2"

__packagename__ = "keprep"
__copyright__ = "Copyright 2023, Gal Kepler"
__credits__ = (
    "Contributors: please check the ``.zenodo.json`` file at the top-level folder"
    "of the repository"
)
__url__ = "https://github.com/GalKepler/keprep"

DOWNLOAD_URL = f"https://github.com/GalKepler/keprep/{__packagename__}/archive/{__version__}.tar.gz"
