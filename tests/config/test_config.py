import logging
import os
import tempfile
from pathlib import Path

import pytest

from keprep import config

_fs_license = os.getenv("FS_LICENSE")
if not _fs_license and os.getenv("FREESURFER_HOME"):
    _fs_home = os.getenv("FREESURFER_HOME")
    if _fs_home and (Path(_fs_home) / "license.txt").is_file():
        _fs_license = str(Path(_fs_home) / "license.txt")
    del _fs_home


@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdirname:
        yield Path(tmpdirname)


def test_environment_config():
    assert config.environment.cpu_count == os.cpu_count()
    assert config.environment.exec_env is not None
    assert config.environment.nipype_version is not None
    assert config.environment.version is not None


def test_nipype_config():
    assert config.nipype.crashfile_format == "txt"
    assert config.nipype.get_linked_libs is False
    assert config.nipype.memory_gb is None
    assert config.nipype.nprocs == os.cpu_count()
    assert config.nipype.plugin == "MultiProc"
    assert config.nipype.plugin_args == {
        "maxtasksperchild": 1,
        "raise_insufficient": False,
    }


def test_execution_config():
    assert config.execution.anat_derivatives is None
    assert config.execution.bids_dir is None
    assert config.execution.bids_database_dir is None
    assert config.execution.debug == []
    if _fs_license is not None:
        assert config.execution.fs_license_file is not None
    else:
        assert config.execution.fs_license_file is None
    assert config.execution.work_dir == Path("work").absolute()


def test_workflow_config():
    assert config.workflow.anat_only is False
    assert config.workflow.dwi2t1w_dof == 6
    assert config.workflow.skull_strip_template == "OASIS30ANTs"


def test_seeds_config():
    assert config.seeds.master is None
    assert config.seeds.ants is None
    assert config.seeds.numpy is None


def test_from_dict(temp_dir):
    bids_dir = temp_dir / "bids"
    bids_dir.mkdir(exist_ok=True, parents=True)
    settings = {
        "bids_dir": bids_dir,
        "work_dir": temp_dir / "work",
        "nprocs": 4,
        "plugin": "Linear",
    }
    config.from_dict(settings, init=False)
    assert config.execution.bids_dir == Path(temp_dir / "bids").absolute()
    assert config.execution.work_dir == Path(temp_dir / "work").absolute()
    assert config.nipype.nprocs == 4
    assert config.nipype.plugin == "Linear"


def test_to_filename_load(temp_dir):
    bids_dir = temp_dir / "bids"
    work_dir = temp_dir / "work"
    bids_dir.mkdir()
    work_dir.mkdir()

    settings = {
        "bids_dir": bids_dir,
        "work_dir": work_dir,
        "nprocs": 4,
        "plugin": "Linear",
    }

    with tempfile.TemporaryDirectory() as tmpdirname:
        config_file = Path(tmpdirname) / "test_config.toml"
        config.from_dict(settings, init=False)
        config.to_filename(config_file)

        assert config_file.exists()

        config.load(config_file, init=False)
        assert config.execution.bids_dir == Path(bids_dir).absolute()
        assert config.execution.work_dir == Path(work_dir).absolute()
        assert config.nipype.nprocs == 4
        assert config.nipype.plugin == "Linear"


def test_init_spaces():
    config.execution.output_spaces = "MNI152NLin2009cAsym"
    config.init_spaces()
    assert "MNI152NLin2009cAsym" in config.workflow.spaces.get_spaces(
        nonstandard=False, dim=(3,)
    )


def test_logging_levels():
    assert logging.getLevelName(25) == "IMPORTANT"
    assert logging.getLevelName(15) == "VERBOSE"
