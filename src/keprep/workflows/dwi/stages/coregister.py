import nipype.pipeline.engine as pe
from nipype.interfaces import fsl
from nipype.interfaces import mrtrix3 as mrt
from nipype.interfaces import utility as niu
from niworkflows.engine.workflows import LiterateWorkflow as Workflow

from keprep import config
from keprep.workflows.dwi.descriptions.coregister import COREG_EPIREG, COREG_FLIRT


def init_dwi_coregister_wf(name: str = "dwi_coregister_wf") -> pe.Workflow:
    """
    Coregister DWI to T1w.

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
    inputnode = pe.Node(
        niu.IdentityInterface(
            fields=[
                # DWI related
                "dwi_reference",
                # Anatomical
                "t1w_preproc",
                "t1w_mask",
            ]
        ),
        name="inputnode",
    )

    outputnode = pe.Node(
        niu.IdentityInterface(
            fields=[
                "dwi2t1w_aff",
                "t1w2dwi_aff",
                "t1w_preproc_brain",
                "dwi_brain_mask",
                "dwi_in_t1w",
            ]
        ),
        name="outputnode",
    )

    apply_mask = pe.Node(
        fsl.ApplyMask(
            out_file="t1w_brain.nii.gz",
        ),
        name="apply_mask",
    )

    convert_xfm = pe.Node(
        fsl.ConvertXFM(
            invert_xfm=True,
            out_file="t1w2dwi.mat",
        ),
        name="convert_xfm",
    )

    apply_xfm = pe.Node(
        fsl.ApplyXFM(
            out_file="t1w2dwi_mask.nii.gz",
            interp="nearestneighbour",
            datatype="int",
        ),
        name="apply_xfm",
    )
    if config.workflow.dwi2t1w_method == "epireg":
        coreg_node = pe.Node(fsl.EpiReg(), name="epireg_node")
        workflow.__desc__ = COREG_EPIREG
        workflow.connect(
            [
                (
                    inputnode,
                    apply_mask,
                    [
                        ("t1w_preproc", "in_file"),
                        ("t1w_mask", "mask_file"),
                    ],
                ),
                (
                    inputnode,
                    coreg_node,
                    [("dwi_reference", "epi"), ("t1w_preproc", "t1_head")],
                ),
                (
                    coreg_node,
                    outputnode,
                    [
                        ("out_file", "dwi_in_t1w"),
                    ],
                ),
                (
                    apply_mask,
                    coreg_node,
                    [
                        ("out_file", "t1_brain"),
                    ],
                ),
                (
                    coreg_node,
                    convert_xfm,
                    [
                        ("epi2str_mat", "in_file"),
                    ],
                ),
                (
                    coreg_node,
                    outputnode,
                    [
                        ("epi2str_mat", "dwi2t1w_aff"),
                    ],
                ),
            ]
        )
    elif config.workflow.dwi2t1w_method == "flirt":
        coreg_node = pe.Node(
            fsl.FLIRT(
                dof=config.workflow.dwi2t1w_dof,
                out_file="dwi2t1w.nii.gz",
                out_matrix_file="dwi2t1w.mat",
                searchr_x=[-90, 90],
                searchr_y=[-90, 90],
                searchr_z=[-90, 90],
                cost="normmi",
                bins=256,
            ),
            name="flirt_node",
        )
        workflow.__desc__ = COREG_FLIRT.format(dof=config.workflow.dwi2t1w_dof)
        workflow.connect(
            [
                (
                    inputnode,
                    apply_mask,
                    [
                        ("t1w_preproc", "in_file"),
                        ("t1w_mask", "mask_file"),
                    ],
                ),
                (
                    inputnode,
                    coreg_node,
                    [
                        ("dwi_reference", "in_file"),
                    ],
                ),
                (
                    coreg_node,
                    outputnode,
                    [
                        ("out_file", "dwi_in_t1w"),
                    ],
                ),
                (
                    apply_mask,
                    coreg_node,
                    [
                        ("out_file", "reference"),
                    ],
                ),
                (
                    coreg_node,
                    convert_xfm,
                    [
                        ("out_matrix_file", "in_file"),
                    ],
                ),
                (
                    coreg_node,
                    outputnode,
                    [
                        ("out_matrix_file", "dwi2t1w_aff"),
                    ],
                ),
            ]
        )

    workflow.connect(
        [
            (
                convert_xfm,
                outputnode,
                [
                    ("out_file", "t1w2dwi_aff"),
                ],
            ),
            (
                apply_mask,
                outputnode,
                [
                    ("out_file", "t1w_preproc_brain"),
                ],
            ),
            (
                inputnode,
                apply_xfm,
                [("t1w_mask", "in_file"), ("dwi_reference", "reference")],
            ),
            (
                convert_xfm,
                apply_xfm,
                [
                    ("out_file", "in_matrix_file"),
                ],
            ),
            (
                apply_xfm,
                outputnode,
                [
                    ("out_file", "dwi_brain_mask"),
                ],
            ),
        ]
    )
    return workflow


def init_5tt_coreg_wf(name="coreg_5tt_wf") -> pe.Workflow:
    """
    Workflow to perform tractography using MRtrix3.
    """
    workflow = pe.Workflow(name=name)

    inputnode = pe.Node(
        niu.IdentityInterface(
            fields=[
                "dwi_reference",
                "t1w_to_dwi_transform",
                "t1w_file",
                "5tt_file",
            ]
        ),
        name="inputnode",
    )

    outputnode = pe.Node(
        niu.IdentityInterface(
            fields=[
                "5tt_coreg",
            ]
        ),
        name="outputnode",
    )
    transform_convert_node = pe.Node(
        mrt.TransformFSLConvert(
            flirt_import=True,
            nthreads=config.nipype.omp_nthreads,
        ),
        name="transform_convert",
    )
    mrtransform_node = pe.Node(
        mrt.MRTransform(
            # inverse=True,
        ),
        name="mrtransform",
    )

    workflow.connect(
        [
            (
                inputnode,
                transform_convert_node,
                [
                    ("t1w_file", "in_file"),
                    ("dwi_reference", "reference"),
                    ("t1w_to_dwi_transform", "in_transform"),
                ],
            ),
            (
                inputnode,
                mrtransform_node,
                [("5tt_file", "in_files")],
            ),
            (
                transform_convert_node,
                mrtransform_node,
                [("out_transform", "linear_transform")],
            ),
            (
                mrtransform_node,
                outputnode,
                [("out_file", "5tt_coreg")],
            ),
        ]
    )
    return workflow
