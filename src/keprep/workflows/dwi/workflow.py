from pathlib import Path

from bids import BIDSLayout
from nipype.interfaces import utility as niu
from nipype.pipeline import engine as pe
from niworkflows.engine.workflows import LiterateWorkflow as Workflow

from keprep import config
from keprep.interfaces.bids import get_fieldmap
from keprep.interfaces.bids.bids import DerivativesDataSink
from keprep.interfaces.reports.reports import DiffusionSummary
from keprep.workflows.dwi.descriptions.base import (
    DENOISING,
    DIFFUSION_WORKFLOW_DESCRIPTION_MULTI_SESSIONS,
    DIFFUSION_WORKFLOW_DESCRIPTION_SINGLE_SESSION,
)
from keprep.workflows.dwi.stages.coregister import init_dwi_coregister_wf
from keprep.workflows.dwi.stages.derivatives import init_derivatives_wf
from keprep.workflows.dwi.stages.eddy import init_eddy_wf
from keprep.workflows.dwi.stages.post_eddy import init_post_eddy_wf
from keprep.workflows.dwi.utils import calculate_denoise_window, read_field_from_json


def fieldmap_is_4d(fieldmap_file: str | Path) -> bool:
    """
    Check if the fieldmap is 4D.

    Parameters
    ----------
    fieldmap_file : Union[str,Path]
        path to fieldmap file

    Returns
    -------
    bool
        True if the fieldmap is 4D
    """
    from nibabel import load

    fieldmap_img = load(str(fieldmap_file))
    return fieldmap_img.ndim == 4  # type: ignore[attr-defined]


def init_dwi_preproc_wf(dwi_file: str | Path, subject_data: dict):
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

    layout: BIDSLayout = config.execution.layout
    config.loggers.workflow.debug(
        "Creating DWI preprocessing workflow for <%s>" % dwi_file
    )
    fieldmap = get_fieldmap(dwi_file=dwi_file, subject_data=subject_data)
    if not fieldmap:  # currently, fieldmap in necessary
        raise FileNotFoundError(f"No fieldmap found for <{dwi_file}>")

    # Build workflow
    workflow = Workflow(name=_get_wf_name(dwi_file))

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
                "fmap_bvec",
                "fmap_bval",
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
    fmap_is_dwi = True
    try:
        inputnode.inputs.fmap_bvec = Path(layout.get_bvec(fieldmap))
        inputnode.inputs.fmap_bval = Path(layout.get_bval(fieldmap))
    except IndexError:
        fmap_is_dwi = False
        pass

    # check if fieldmap is 4D
    fmap_is_4d = fieldmap_is_4d(fieldmap)

    outputnode = pe.Node(  # noqa: F841
        niu.IdentityInterface(
            fields=["dwi_preproc", "dwi_reference", "dwi_mask"],
        ),
        name="outputnode",
    )

    if (
        config.workflow.denoise_method == "dwidenoise"
        and config.workflow.dwi_denoise_window == "auto"
    ):
        dwi_denoise_window = calculate_denoise_window(dwi_file)  # type: ignore[arg-type] # noqa: E501
    n_dwis = len(subject_data["dwi"])
    desc = (
        DIFFUSION_WORKFLOW_DESCRIPTION_MULTI_SESSIONS
        if n_dwis > 1
        else DIFFUSION_WORKFLOW_DESCRIPTION_SINGLE_SESSION
    )
    workflow.__desc__ = desc.format(n_dwi=n_dwis) + DENOISING.format(
        b0_threshold=config.workflow.b0_threshold, denoise_window=dwi_denoise_window
    )

    bo_to_t1w = "Rigid" if config.workflow.dwi2t1w_dof == 6 else "Affine"
    summary = pe.Node(
        DiffusionSummary(
            distortion_correction="TOPUP",
            hmc_model=config.workflow.hmc_model,
            b0_to_t1w_transform=bo_to_t1w,
            denoise_method=config.workflow.denoise_method,
            dwi_denoise_window=dwi_denoise_window,
        ),
        name="summary",
    )

    read_pe_direction = pe.Node(
        niu.Function(
            input_names=["json_file", "field"],
            output_names=["pe_dir"],
            function=read_field_from_json,
        ),
        name="read_pe_direction",
    )
    read_pe_direction.inputs.field = "PhaseEncodingDirection"

    # Reporting
    ds_report_summary = pe.Node(
        DerivativesDataSink(
            base_directory=str(config.execution.keprep_dir),  # type: ignore[attr-defined] # noqa: E501
            datatype="figures",
            suffix="dwi",
            desc="summary",
            source_file=dwi_file,
            dismiss_entities=["direction"],
            copy=True,
        ),
        name="ds_report_summary",
    )
    workflow.connect(
        [
            (
                inputnode,
                read_pe_direction,
                [("dwi_json", "json_file")],
            ),
            (
                read_pe_direction,
                summary,
                [("pe_dir", "pe_direction")],
            ),
            (
                summary,
                ds_report_summary,
                [("out_report", "in_file")],
            ),
        ]
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
    if fmap_is_dwi:
        workflow.connect(
            [
                (
                    inputnode,
                    fmap_conversion_to_mif_node,
                    [
                        ("fmap_bvec", "in_bvec"),
                        ("fmap_bval", "in_bval"),
                    ],
                ),
            ]
        )

    # Denoise DWI using MP-PCA
    dwi_denoise_node = pe.Node(
        interface=mrt.DWIDenoise(
            out_file="dwi_denoised.mif",
            extent=(dwi_denoise_window, dwi_denoise_window, dwi_denoise_window),
            noise="noise.nii.gz",
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

    eddy_wf = init_eddy_wf(fieldmap_is_4d=fmap_is_4d, fmap_is_dwi=fmap_is_dwi)
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
                    ("outputnode.eddy_qc", "inputnode.eddy_qc"),
                ],
            ),
        ]
    )

    sdc_report = pe.Node(
        SimpleBeforeAfter(
            before_label="Distorted",
            after_label="Corrected",
            dismiss_affine=True,
        ),
        name="sdc_report",
        mem_gb=0.1,
    )

    coreg_wf = init_dwi_coregister_wf()

    workflow.connect(
        [
            (
                eddy_wf,
                sdc_report,
                [
                    ("outputnode.dwi_reference_distorted", "before"),
                ],
            ),
            (
                post_eddy,
                sdc_report,
                [
                    ("outputnode.dwi_reference", "after"),
                ],
            ),
            (
                post_eddy,
                coreg_wf,
                [
                    ("outputnode.dwi_reference", "inputnode.dwi_reference"),
                ],
            ),
            (
                inputnode,
                coreg_wf,
                [
                    ("t1w_preproc", "inputnode.t1w_preproc"),
                    ("t1w_mask", "inputnode.t1w_mask"),
                ],
            ),
        ]
    )

    coreg_report = pe.Node(
        SimpleBeforeAfter(
            before_label="T1w",
            after_label="Dwi",
            dismiss_affine=True,
        ),
        name="coreg_report",
        mem_gb=0.1,
    )
    workflow.connect(
        [
            (
                inputnode,
                coreg_report,
                [
                    ("t1w_preproc", "before"),
                ],
            ),
            (
                coreg_wf,
                coreg_report,
                [
                    ("outputnode.dwi_in_t1w", "after"),
                ],
            ),
        ]
    )
    ds_workflow = init_derivatives_wf()

    workflow.connect(
        [
            (
                inputnode,
                ds_workflow,
                [
                    ("dwi_file", "inputnode.source_file"),
                ],
            ),
            (
                eddy_wf,
                ds_workflow,
                [
                    ("outputnode.eddy_qc", "inputnode.eddy_qc"),
                ],
            ),
            (
                post_eddy,
                ds_workflow,
                [
                    ("outputnode.dwi_preproc", "inputnode.dwi_preproc"),
                    ("outputnode.dwi_grad", "inputnode.dwi_grad"),
                    ("outputnode.dwi_bvec", "inputnode.dwi_bvec"),
                    ("outputnode.dwi_bval", "inputnode.dwi_bval"),
                    ("outputnode.dwi_json", "inputnode.dwi_json"),
                    ("outputnode.dwi_reference", "inputnode.dwi_reference"),
                    (
                        "outputnode.dwi_reference_json",
                        "inputnode.dwi_reference_json",
                    ),
                    ("outputnode.eddy_qc_plot", "inputnode.eddy_qc_plot"),
                ],
            ),
            (
                coreg_wf,
                ds_workflow,
                [
                    ("outputnode.dwi_brain_mask", "inputnode.dwi_brain_mask"),
                    ("outputnode.dwi2t1w_aff", "inputnode.dwi2t1w_aff"),
                    ("outputnode.t1w2dwi_aff", "inputnode.t1w2dwi_aff"),
                ],
            ),
            (
                sdc_report,
                ds_workflow,
                [("out_report", "inputnode.sdc_report")],
            ),
            (
                coreg_report,
                ds_workflow,
                [("out_report", "inputnode.coreg_report")],
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
    return f"dwi_preproc_{fname_nosub.replace('.', '_').replace(' ', '').replace('-', '_')}"  # noqa: E501
