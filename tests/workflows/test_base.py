import os
from pathlib import Path

import pytest

_fs_license = os.getenv("FS_LICENSE")
if not _fs_license and os.getenv("FREESURFER_HOME"):
    _fs_home = os.getenv("FREESURFER_HOME")
    if _fs_home and (Path(_fs_home) / "license.txt").is_file():
        _fs_license = str(Path(_fs_home) / "license.txt")
    del _fs_home


@pytest.fixture
def test_bids_dataset():
    return Path(__file__).parent.parent / "data" / "bids_test"
