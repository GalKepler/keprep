from pathlib import Path
from typing import Union

from nipype.interfaces import utility as niu
from nipype.pipeline import engine as pe

from keprep import config
from keprep.interfaces.bids import get_fieldmap


def init_dwi_preproc_wf(dwi_file: Union[str, Path]):
    """
    Build the dwi preprocessing workflow.

    Parameters
    ----------
    dwi_file : Union[str,Path]
        path to DWI file
    """
    from niworkflows.interfaces.reportlets.registration import (
        SimpleBeforeAfterRPT as SimpleBeforeAfter,
    )

    layout = config.execution.layout
    config.loggers.workflow.debug(
        "Creating DWI preprocessing workflow for <%s>" % dwi_file
    )
    fieldmap = get_fieldmap(dwi_file, layout)
    if not fieldmap:  # currently, fieldmap in necessary
        raise FileNotFoundError(f"No fieldmap found for <{dwi_file}>")

    # Build workflow
    workflow = pe.Workflow(name=_get_wf_name(dwi_file))

    inputnode = pe.Node(
        niu.IdentityInterface(
            fields=[
                # DWI related
                "dwi_file",
                "dwi_bvec",
                "dwi_bval",
                "dwi_json",
                # Fieldmap related
                "fmap_file",
                "fmap_json",
                # Anatomical
                "t1w_preproc",
                "t1w_mask",
            ]
        ),
        name="inputnode",
    )
    # Set up DWI
    inputnode.inputs.dwi_file = Path(dwi_file)
    inputnode.inputs.dwi_bvec = Path(layout.get_bvec(dwi_file))
    inputnode.inputs.dwi_bval = Path(layout.get_bval(dwi_file))
    inputnode.inputs.dwi_json = Path(layout.get_nearest(dwi_file, extension="json"))
    # Set up fieldmap
    inputnode.inputs.fmap_file = Path(fieldmap)
    inputnode.inputs.fmap_json = Path(layout.get_nearest(fieldmap, extension="json"))

    outputnode = pe.Node(
        niu.IdentityInterface(
            fields=["dwi_preproc", "dwi_reference", "dwi_mask"],
        ),
        name="outputnode",
    )

    return fieldmap


def _get_wf_name(filename):
    """
    Derive the workflow name for supplied DWI file.

    Examples
    --------
    >>> _get_wf_name("/completely/made/up/path/sub-01_dir-AP_acq-64grad_dwi.nii.gz")
    'dwi_preproc_dir_AP_acq_64grad_wf'

    >>> _get_wf_name("/completely/made/up/path/sub-01_dir-RL_run-01_echo-1_dwi.nii.gz")
    'dwi_preproc_dir_RL_run_01_echo_1_wf'

    """
    from pathlib import Path

    fname = Path(filename).name.rpartition(".nii")[0].replace("_dwi", "_wf")
    fname_nosub = "_".join(fname.split("_")[1:])
    return f"dwi_preproc_{fname_nosub.replace('.', '_').replace(' ', '').replace('-', '_')}"
