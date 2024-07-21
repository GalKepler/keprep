import nipype.pipeline.engine as pe
from nipype.interfaces import mrtrix3 as mrt
from nipype.interfaces import utility as niu

from keprep import config
from keprep.workflows.dwi.stages.extract_b0 import init_extract_b0_wf


def init_eddy_wf(name: str = "eddy_wf") -> pe.Workflow:
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
    workflow = pe.Workflow(name=name)

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
        niu.IdentityInterface(fields=["dwi_preproc", "dwi_reference_distorted"]),
        name="outputnode",
    )

    dwi_b0_extractor = init_extract_b0_wf(name="dwi_b0_extractor")
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
            (
                listify_b0,
                prep_pe_pair,
                [
                    ("out", "in_files"),
                ],
            ),
        ]
    )

    query_pe_dir = pe.Node(
        niu.Function(
            input_names=["json_file"],
            output_names=["pe_dir"],
            function=get_pe_from_json,
        ),
        name="query_pe_dir",
    )

    dwifslpreproc = pe.Node(
        mrt.DWIPreproc(
            eddy_options=" --fwhm=0 --flm='quadratic'",
            rpe_options="pair",
            align_seepi=True,
            nthreads=config.nipype.omp_nthreads,
            eddyqc_all="eddyqc",
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
                ],
            ),
        ]
    )
    return workflow


def get_pe_from_json(json_file: str) -> str:
    """
    Query the phase encoding direction from a json file.

    Parameters
    ----------
    json_file : str
        path to json file

    Returns
    -------
    str
        phase encoding direction
    """
    import json

    with open(json_file) as f:
        data = json.load(f)
    return data["PhaseEncodingDirection"]
