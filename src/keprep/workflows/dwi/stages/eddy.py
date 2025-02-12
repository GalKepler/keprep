import nipype.pipeline.engine as pe
from nipype.interfaces import mrtrix3 as mrt
from nipype.interfaces import utility as niu
from niworkflows.engine.workflows import LiterateWorkflow as Workflow

from keprep import config
from keprep.interfaces.mrtrix3 import DWIPreproc
from keprep.workflows.dwi.descriptions.eddy import RPE_DESCRIPTION, RPE_DWIFSLPREPROC
from keprep.workflows.dwi.stages.extract_b0 import init_extract_b0_wf
from keprep.workflows.dwi.utils import read_field_from_json


def init_eddy_wf(
    name: str = "eddy_wf", fieldmap_is_4d: bool = True, fmap_is_dwi: bool = True
) -> pe.Workflow:
    """
    Build the SDC and motion correction workflow.

    Parameters
    ----------
    name : str, optional
        name of the workflow (default: "eddy_wf")

    Returns
    -------
    pe.Workflow
        the workflow
    """
    workflow = Workflow(name=name)
    workflow.__desc__ = RPE_DESCRIPTION + RPE_DWIFSLPREPROC
    inputnode = pe.Node(
        niu.IdentityInterface(
            fields=[
                "dwi_file",
                "dwi_json",
                "fmap_file",
            ]
        ),
        name="inputnode",
    )

    outputnode = pe.Node(
        niu.IdentityInterface(
            fields=["dwi_preproc", "dwi_reference_distorted", "eddy_qc"]
        ),
        name="outputnode",
    )

    dwi_b0_extractor = init_extract_b0_wf(name="dwi_b0_extractor")
    if fieldmap_is_4d:
        fmap_b0_extractor = init_extract_b0_wf(name="fmap_b0_extractor")

    # node to listify opposite phase encoding directions
    listify_b0 = pe.Node(niu.Merge(2), name="listify_b0")

    prep_pe_pair = pe.Node(mrt.MRCat(axis=3), name="prep_pe_pair")

    convert_b0_to_nii = pe.Node(
        mrt.MRConvert(out_file="b0.nii.gz"),
        name="convert_b0_to_nii",
    )

    workflow.connect(
        [
            (
                inputnode,
                dwi_b0_extractor,
                [
                    ("dwi_file", "inputnode.dwi_file"),
                ],
            ),
            (
                dwi_b0_extractor,
                convert_b0_to_nii,
                [
                    ("outputnode.dwi_reference", "in_file"),
                ],
            ),
            (
                convert_b0_to_nii,
                outputnode,
                [
                    ("out_file", "dwi_reference_distorted"),
                ],
            ),
            (
                dwi_b0_extractor,
                listify_b0,
                [
                    ("outputnode.dwi_reference", "in1"),
                ],
            ),
            (
                listify_b0,
                prep_pe_pair,
                [
                    ("out", "in_files"),
                ],
            ),
        ]
    )
    if fieldmap_is_4d:
        workflow.connect(
            [
                (
                    inputnode,
                    fmap_b0_extractor,
                    [
                        ("fmap_file", "inputnode.dwi_file"),
                    ],
                ),
                (
                    fmap_b0_extractor,
                    listify_b0,
                    [
                        ("outputnode.dwi_reference", "in2"),
                    ],
                ),
            ]
        )
    else:
        workflow.connect(
            [
                (
                    inputnode,
                    listify_b0,
                    [
                        ("fmap_file", "in2"),
                    ],
                )
            ]
        )

    query_pe_dir = pe.Node(
        niu.Function(
            input_names=["json_file", "field"],
            output_names=["pe_dir"],
            function=read_field_from_json,
        ),
        name="query_pe_dir",
    )
    query_pe_dir.inputs.field = "PhaseEncodingDirection"

    dwifslpreproc = pe.Node(
        DWIPreproc(
            eddy_options=f" {config.workflow.eddy_config}",
            rpe_options="pair",
            align_seepi=True,
            nthreads=config.nipype.omp_nthreads,
            eddyqc_all="eddyqc",
            args="-nocleanup",
        ),
        name="dwifslpreproc",
    )

    workflow.connect(
        [
            (
                inputnode,
                query_pe_dir,
                [
                    ("dwi_json", "json_file"),
                ],
            ),
            (query_pe_dir, dwifslpreproc, [("pe_dir", "pe_dir")]),
            (
                prep_pe_pair,
                dwifslpreproc,
                [
                    ("out_file", "in_epi"),
                ],
            ),
            (
                inputnode,
                dwifslpreproc,
                [
                    ("dwi_file", "in_file"),
                ],
            ),
            (
                dwifslpreproc,
                outputnode,
                [
                    ("out_file", "dwi_preproc"),
                    ("eddyqc_all", "eddy_qc"),
                ],
            ),
        ]
    )
    return workflow
