import nipype.pipeline.engine as pe
from nipype.interfaces import mrtrix3 as mrt
from nipype.interfaces import utility as niu
from niworkflows.engine.workflows import LiterateWorkflow as Workflow

from keprep import config
from keprep.interfaces.mrtrix3 import MRConvert
from keprep.workflows.dwi.descriptions.post_eddy import DWIBIASCORRECT
from keprep.workflows.dwi.stages.extract_b0 import init_extract_b0_wf
from keprep.workflows.dwi.utils import plot_eddy_qc


def init_post_eddy_wf(name: str = "post_eddy_wf") -> pe.Workflow:
    """
    Bias correction and convert to Nifti workflow.

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
    workflow.__desc__ = DWIBIASCORRECT
    inputnode = pe.Node(
        niu.IdentityInterface(
            fields=[
                "dwi_preproc",
                "eddy_qc",
            ]
        ),
        name="inputnode",
    )

    outputnode = pe.Node(
        niu.IdentityInterface(
            fields=[
                "dwi_mif",
                "dwi_preproc",
                "dwi_grad",
                "dwi_bvec",
                "dwi_bval",
                "dwi_json",
                "dwi_reference",
                "dwi_reference_json",
                "eddy_qc_plot",
            ]
        ),
        name="outputnode",
    )

    plot_eddy_qc_node = pe.Node(
        niu.Function(
            input_names=["eddy_qc", "out_file"],
            output_names=["out_file"],
            function=plot_eddy_qc,
        ),
        name="plot_eddy_qc",
    )
    plot_eddy_qc_node.inputs.out_file = "eddy_qc_plot.svg"
    workflow.connect(
        [
            (
                inputnode,
                plot_eddy_qc_node,
                [
                    ("eddy_qc", "eddy_qc"),
                ],
            ),
            (
                plot_eddy_qc_node,
                outputnode,
                [
                    ("out_file", "eddy_qc_plot"),
                ],
            ),
        ]
    )

    mrconvert_dwi = pe.Node(
        MRConvert(
            out_file="dwi.nii.gz",
            out_mrtrix_grad="dwi.b",
            out_bval="dwi.bval",
            out_bvec="dwi.bvec",
            json_export="dwi.json",
            nthreads=config.nipype.omp_nthreads,
        ),
        name="mrconvert_dwi",
    )
    if config.workflow.dwi_no_biascorr:
        workflow.connect(
            [
                (
                    inputnode,
                    mrconvert_dwi,
                    [
                        ("dwi_preproc", "in_file"),
                    ],
                ),
                (
                    inputnode,
                    outputnode,
                    [("dwi_preproc", "dwi_mif")],
                ),
            ]
        )
    else:
        bias_correct = pe.Node(
            mrt.DWIBiasCorrect(
                out_file="bias_corrected.mif",
                use_ants=True,
                nthreads=config.nipype.omp_nthreads,
            ),
            name="bias_correct",
        )
        workflow.connect(
            [
                (
                    inputnode,
                    bias_correct,
                    [
                        ("dwi_preproc", "in_file"),
                    ],
                ),
                (
                    bias_correct,
                    mrconvert_dwi,
                    [
                        ("out_file", "in_file"),
                    ],
                ),
                (
                    bias_correct,
                    outputnode,
                    [
                        ("out_file", "dwi_mif"),
                    ],
                ),
            ]
        )

    workflow.connect(
        [
            (
                mrconvert_dwi,
                outputnode,
                [
                    ("out_file", "dwi_preproc"),
                    ("out_mrtrix_grad", "dwi_grad"),
                    ("out_bval", "dwi_bval"),
                    ("out_bvec", "dwi_bvec"),
                    ("json_export", "dwi_json"),
                ],
            ),
        ]
    )

    b0_extractor = init_extract_b0_wf()
    mrconvert_dwiref = pe.Node(
        MRConvert(
            out_file="dwi_reference.nii.gz",
            json_export="dwi_reference.json",
            nthreads=config.nipype.omp_nthreads,
        ),
        name="mrconvert_dwiref",
    )
    workflow.connect(
        [
            (
                bias_correct,
                b0_extractor,
                [
                    ("out_file", "inputnode.dwi_file"),
                ],
            ),
            (
                b0_extractor,
                mrconvert_dwiref,
                [
                    ("outputnode.dwi_reference", "in_file"),
                ],
            ),
            (
                mrconvert_dwiref,
                outputnode,
                [
                    ("out_file", "dwi_reference"),
                    ("json_export", "dwi_reference_json"),
                ],
            ),
        ]
    )

    return workflow
