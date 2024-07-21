import nipype.pipeline.engine as pe
from nipype.interfaces import mrtrix3 as mrt
from nipype.interfaces import utility as niu

from keprep import config
from keprep.interfaces.mrtrix3 import TckSift
from keprep.workflows.dwi.stages.coregister import init_5tt_coreg_wf


def estimate_tractography_parameters(
    in_file: str,
    stepscale: float = 0.5,
    lenscale_min: int = 30,
    lenscale_max: int = 500,
):
    """
    Estimate parameters for tractography by normalizing them to the
    pixel size of the image.

    Parameters
    ----------
    in_file : str
        Path to the input file.
    stepscale : float
        Step size in mm.
    lenscale_min : int
        Minimum length of the tract in mm.
    lenscale_max : int
        Maximum length of the tract in mm.

    Returns
    -------
    stepscale : float
        Step size in mm.
    lenscale_min : int
        Minimum length of the tract in mm.
    lenscale_max : int
        Maximum length of the tract in mm.
    """
    import nibabel as nib

    from keprep import config

    data = nib.load(in_file)
    pixdim = data.header["pixdim"][1]  # type: ignore[index]
    stepscale = config.workflow.tracking_stepscale * pixdim
    lenscale_min = config.workflow.tracking_lenscale_min * pixdim
    lenscale_max = config.workflow.tracking_lenscale_max * pixdim
    return stepscale, lenscale_min, lenscale_max


def init_tractography_wf(name: str = "tractography_wf") -> pe.Workflow:
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
                "dwi_mif",
                "dwi_nifti",
                "dwi_reference",
                "t1w_to_dwi_transform",
                "t1w_file",
                "mask_file",
                "five_tissue_type",
            ]
        ),
        name="inputnode",
    )

    outputnode = pe.Node(
        niu.IdentityInterface(
            fields=[
                "wm_response",
                "gm_response",
                "csf_response",
                "wm_fod",
                "gm_fod",
                "csf_fod",
                "predicted_signal",
                "unsifted_tck",
                "sifted_tck",
            ]
        ),
        name="outputnode",
    )

    coreg_5tt_wf = init_5tt_coreg_wf()
    workflow.connect(
        [
            (
                inputnode,
                coreg_5tt_wf,
                [
                    ("dwi_reference", "inputnode.dwi_reference"),
                    ("t1w_to_dwi_transform", "inputnode.t1w_to_dwi_transform"),
                    ("t1w_file", "inputnode.t1w_file"),
                    ("five_tissue_type", "inputnode.5tt_file"),
                ],
            )
        ]
    )

    # Estimate the response functions
    dwi2response_node = pe.Node(
        mrt.ResponseSD(
            algorithm=config.workflow.response_algorithm,
            wm_file="wm_response.txt",
            gm_file="gm_response.txt",
            csf_file="csf_response.txt",
        ),
        name="dwi2response",
    )

    # Estimate the fiber orientation distribution
    dwi2fod_node = pe.Node(
        mrt.ConstrainedSphericalDeconvolution(
            algorithm=config.workflow.fod_algorithm,
            wm_odf="wm_fod.mif",
            gm_odf="gm_fod.mif",
            csf_odf="csf_fod.mif",
            predicted_signal="predicted_signal.mif",
            nthreads=config.nipype.omp_nthreads,
        ),
        name="dwi2fod",
    )

    workflow.connect(
        [
            (
                inputnode,
                dwi2response_node,
                [
                    ("dwi_mif", "in_file"),
                    ("mask_file", "in_mask"),
                ],
            ),
            (
                inputnode,
                dwi2fod_node,
                [
                    ("dwi_mif", "in_file"),
                    ("mask_file", "mask_file"),
                ],
            ),
            (
                dwi2response_node,
                dwi2fod_node,
                [
                    ("wm_file", "wm_txt"),
                    ("gm_file", "gm_txt"),
                    ("csf_file", "csf_txt"),
                ],
            ),
            (
                dwi2response_node,
                outputnode,
                [
                    ("wm_file", "wm_response"),
                    ("gm_file", "gm_response"),
                    ("csf_file", "csf_response"),
                ],
            ),
            (
                dwi2fod_node,
                outputnode,
                [
                    ("wm_odf", "wm_fod"),
                    ("gm_odf", "gm_fod"),
                    ("csf_odf", "csf_fod"),
                    ("predicted_signal", "predicted_signal"),
                ],
            ),
        ]
    )

    tractography = pe.Node(
        mrt.Tractography(
            algorithm=config.workflow.tracking_algorithm,
            angle=config.workflow.tracking_max_angle,
            select=config.workflow.n_raw_tracts,
            out_file="tracks.tck",
            nthreads=config.nipype.omp_nthreads,
        ),
        name="tractography",
    )

    estimate_tracts_parameters_node = pe.Node(
        niu.Function(
            function=estimate_tractography_parameters,
            input_names=["in_file"],
            output_names=["stepscale", "lenscale_min", "lenscale_max"],
        ),
        name="estimate_tractography_parameters",
    )

    tcksift_node = pe.Node(
        TckSift(
            nthreads=config.nipype.omp_nthreads,
            out_file="sift.tck",
            out_csv="sift.csv",
            out_mu="sift_mu.txt",
            term_number=config.workflow.n_tracts,
            fd_scale_gm=config.workflow.fs_scale_gm,
        ),
        name="tcksift",
    )
    if config.workflow.debug_sift:
        tcksift_node.inputs.output_debug = "sift_debug"

    workflow.connect(
        [
            (
                inputnode,
                estimate_tracts_parameters_node,
                [
                    ("dwi_nifti", "in_file"),
                ],
            ),
            (
                estimate_tracts_parameters_node,
                tractography,
                [
                    ("stepscale", "step_size"),
                    ("lenscale_min", "min_length"),
                    ("lenscale_max", "max_length"),
                ],
            ),
            (
                inputnode,
                tractography,
                [("mask_file", "seed_image")],
            ),
            (
                coreg_5tt_wf,
                tractography,
                [
                    ("outputnode.5tt_coreg", "act_file"),
                ],
            ),
            (
                dwi2fod_node,
                tractography,
                [
                    ("wm_odf", "in_file"),
                ],
            ),
            (
                dwi2fod_node,
                tcksift_node,
                [
                    ("wm_odf", "in_fod"),
                ],
            ),
            (coreg_5tt_wf, tcksift_node, [("outputnode.5tt_coreg", "act_file")]),
            (
                tractography,
                tcksift_node,
                [
                    ("out_file", "in_file"),
                ],
            ),
            (
                tractography,
                outputnode,
                [
                    ("out_file", "unsifted_tck"),
                ],
            ),
            (
                tcksift_node,
                outputnode,
                [
                    ("out_file", "sifted_tck"),
                ],
            ),
        ]
    )

    return workflow
