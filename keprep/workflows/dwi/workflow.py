from pathlib import Path
from typing import Union

from nipype.interfaces import utility as niu
from nipype.pipeline import engine as pe

from keprep import config
from keprep.interfaces.bids import get_fieldmap
from keprep.workflows.dwi.stages.eddy import init_eddy_wf
from keprep.workflows.dwi.stages.post_eddy import init_post_eddy_wf


def init_dwi_preproc_wf(dwi_file: Union[str, Path]):
    """
    Build the dwi preprocessing workflow.

    Parameters
    ----------
    dwi_file : Union[str,Path]
        path to DWI file
    """
    from nipype.interfaces import mrtrix3 as mrt
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
    dwi_conversion_to_mif_node = pe.Node(
        interface=mrt.MRConvert(
            out_file="dwi.mif", nthreads=config.nipype.omp_nthreads
        ),
        name="dwi_mifconv",
    )
    fmap_conversion_to_mif_node = pe.Node(
        interface=mrt.MRConvert(
            out_file="fmap.mif", nthreads=config.nipype.omp_nthreads
        ),
        name="fmap_mifconv",
    )
    workflow.connect(
        [
            (
                inputnode,
                dwi_conversion_to_mif_node,
                [
                    ("dwi_file", "in_file"),
                    ("dwi_bvec", "in_bvec"),
                    ("dwi_bval", "in_bval"),
                    ("dwi_json", "json_import"),
                ],
            ),
            (
                inputnode,
                fmap_conversion_to_mif_node,
                [
                    ("fmap_file", "in_file"),
                    ("fmap_json", "json_import"),
                ],
            ),
        ]
    )

    # Denoise DWI using MP-PCA
    dwi_denoise_node = pe.Node(
        interface=mrt.DWIDenoise(
            out_file="dwi_denoised.mif",
            noise="noise.mif",
            nthreads=config.nipype.omp_nthreads,
        ),
        name="dwi_denoise",
    )
    workflow.connect(
        [
            (
                dwi_conversion_to_mif_node,
                dwi_denoise_node,
                [("out_file", "in_file")],
            ),
        ]
    )

    eddy_wf = init_eddy_wf()
    workflow.connect(
        [
            (inputnode, eddy_wf, [("dwi_json", "inputnode.dwi_json")]),
            (
                dwi_denoise_node,
                eddy_wf,
                [
                    ("out_file", "inputnode.dwi_file"),
                ],
            ),
            (
                fmap_conversion_to_mif_node,
                eddy_wf,
                [
                    ("out_file", "inputnode.fmap_file"),
                ],
            ),
        ]
    )

    post_eddy = init_post_eddy_wf()

    workflow.connect(
        [
            (
                eddy_wf,
                post_eddy,
                [
                    ("outputnode.dwi_preproc", "inputnode.dwi_preproc"),
                ],
            ),
        ]
    )

    return workflow


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
