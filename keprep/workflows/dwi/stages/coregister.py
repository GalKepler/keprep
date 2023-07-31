import nipype.pipeline.engine as pe
from nipype.interfaces import fsl
from nipype.interfaces import utility as niu

from keprep import config


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
    workflow = pe.Workflow(name=name)
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

    filrt_node = pe.Node(
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
        name="filrt_node",
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
                filrt_node,
                [
                    ("dwi_reference", "in_file"),
                ],
            ),
            (
                filrt_node,
                outputnode,
                [
                    ("out_file", "dwi_in_t1w"),
                ],
            ),
            (
                apply_mask,
                filrt_node,
                [
                    ("out_file", "reference"),
                ],
            ),
            (
                filrt_node,
                convert_xfm,
                [
                    ("out_matrix_file", "in_file"),
                ],
            ),
            (
                convert_xfm,
                outputnode,
                [
                    ("out_file", "t1w2dwi_aff"),
                ],
            ),
            (
                filrt_node,
                outputnode,
                [
                    ("out_matrix_file", "dwi2t1w_aff"),
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
