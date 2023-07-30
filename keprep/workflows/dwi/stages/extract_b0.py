import nipype.pipeline.engine as pe
from nipype.interfaces import mrtrix3 as mrt
from nipype.interfaces import utility as niu

from keprep import config


def init_extract_b0_wf(name: str = "extract_b0_wf") -> pe.Workflow:
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
            ]
        ),
        name="inputnode",
    )

    outputnode = pe.Node(
        niu.IdentityInterface(fields=["dwi_reference"]),
        name="outputnode",
    )

    b0_extractor = pe.Node(
        mrt.DWIExtract(
            bzero=True,
            out_file="dwi_b0.mif",
            nthreads=config.nipype.omp_nthreads,
        ),
        name="b0_extractor",
    )

    mean_b0 = pe.Node(
        mrt.MRMath(operation="mean", axis=3, out_file="dwi_b0_mean.mif"),
        name="mean_b0",
    )

    workflow.connect(
        [
            (
                inputnode,
                b0_extractor,
                [
                    ("dwi_file", "in_file"),
                ],
            ),
            (
                b0_extractor,
                mean_b0,
                [
                    ("out_file", "in_file"),
                ],
            ),
            (
                mean_b0,
                outputnode,
                [
                    ("out_file", "dwi_reference"),
                ],
            ),
        ]
    )
    return workflow
