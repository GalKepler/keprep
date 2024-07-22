import tempfile
from pathlib import Path

import nipype.pipeline.engine as pe
import pytest
from nipype.interfaces.base import TraitError

from keprep import config
from keprep.workflows.anatomical.post_smriprep import (
    init_post_anatomical_wf,
    locate_fs_subject_dir,
)


@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdirname:
        yield Path(tmpdirname)


@pytest.fixture
def anatomical_wf():
    config.nipype.omp_nthreads = 1
    return init_post_anatomical_wf()


def test_fail_init_anatomical_wf():
    with pytest.raises(TraitError):
        init_post_anatomical_wf()


def test_init_anatomical_wf(anatomical_wf):
    wf = init_post_anatomical_wf()
    assert isinstance(wf, pe.Workflow)


def test_locate_fs_directory(temp_dir):
    subject_freesurfer_dir = temp_dir / "test"
    subject_freesurfer_dir.mkdir()
    located_fs_directory = locate_fs_subject_dir("test", str(temp_dir))
    assert located_fs_directory == str(subject_freesurfer_dir)


def test_wf_with_algo_fsl(anatomical_wf):
    config.workflow.five_tissue_type_algorithm = "fsl"
    anatomical_wf = init_post_anatomical_wf()
    assert isinstance(anatomical_wf, pe.Workflow)


def test_wf_with_algo_hsvs(anatomical_wf):
    config.workflow.five_tissue_type_algorithm = "hsvs"
    anatomical_wf = init_post_anatomical_wf()
    assert isinstance(anatomical_wf, pe.Workflow)
