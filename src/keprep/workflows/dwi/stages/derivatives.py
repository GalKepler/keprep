import nipype.pipeline.engine as pe
from nipype.interfaces import utility as niu

from keprep import config
from keprep.interfaces.bids import DerivativesDataSink

DWI_PREPROC_BASE_ENTITIES = dict(desc="preproc", space="dwi", datatype="dwi")


def _eddy_qc_dds(eddy_qc, source_file):
    import shutil
    from pathlib import Path

    destination = Path(source_file).parent / "eddy_qc"
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(eddy_qc, destination)


def init_derivatives_wf(name: str = "derivatives_wf") -> pe.Workflow:
    """
    Build the workflow that saves derivatives.

    Parameters
    ----------
    name : str, optional
        name of the workflow (default: "derivatives_wf")

    Returns
    -------
    pe.Workflow
        the workflow
    """
    output_dir = str(config.execution.keprep_dir)  # type: ignore[attr-defined]

    workflow = pe.Workflow(name=name)

    inputnode = pe.Node(
        niu.IdentityInterface(
            fields=[
                "source_file",
                "dwi_preproc",
                "dwi_grad",
                "dwi_bvec",
                "dwi_bval",
                "dwi_json",
                "dwi_reference",
                "dwi_reference_json",
                "dwi2t1w_aff",
                "t1w2dwi_aff",
                "dwi_brain_mask",
                "eddy_qc",
                "sdc_report",
                "coreg_report",
                "unsifted_tck",
                "sifted_tck",
                "eddy_qc_plot",
            ]
        ),
        name="inputnode",
    )

    ds_eddy_qc = pe.Node(
        niu.Function(
            input_names=["eddy_qc", "source_file"],
            output_names=[],
            function=_eddy_qc_dds,
        ),
        name="ds_eddy_qc",
    )

    ds_eddy_qc_plot = pe.Node(
        DerivativesDataSink(
            base_directory=output_dir,
            desc="eddyqc",
            suffix="dwi",
            datatype="figures",
            dismiss_entities=["direction"],
            copy=True,
        ),
        name="ds_eddy_qc_plot",
    )

    ds_sdc_report = pe.Node(
        DerivativesDataSink(
            base_directory=output_dir,
            desc="sdc",
            suffix="dwi",
            datatype="figures",
            dismiss_entities=["direction"],
            copy=True,
        ),
        name="ds_report_sdc",
    )
    ds_coreg_report = pe.Node(
        DerivativesDataSink(
            base_directory=output_dir,
            desc="coreg",
            suffix="dwi",
            datatype="figures",
            dismiss_entities=["direction"],
            copy=True,
        ),
        name="ds_coreg_report",
    )

    ds_dwi_preproc = pe.Node(
        DerivativesDataSink(
            base_directory=output_dir,
            suffix="dwi",
            compress=True,
            **DWI_PREPROC_BASE_ENTITIES,
            dismiss_entities=["direction"],
            copy=True,
        ),
        name="ds_dwi_preproc",
    )

    listify_gradients = pe.Node(
        niu.Merge(4),
        name="listify_associated_to_dwi",
    )

    ds_dwi_supp = pe.MapNode(
        DerivativesDataSink(
            base_directory=output_dir,
            suffix="dwi",
            **DWI_PREPROC_BASE_ENTITIES,
            dismiss_entities=["direction"],
            copy=True,
        ),
        iterfield=["in_file"],
        name="ds_dwi_gradients",
    )

    ds_dwiref = pe.Node(
        DerivativesDataSink(
            base_directory=output_dir,
            suffix="dwiref",
            compress=True,
            **DWI_PREPROC_BASE_ENTITIES,
            dismiss_entities=["direction"],
            copy=True,
        ),
        name="ds_dwiref",
    )

    ds_dwiref_json = pe.Node(
        DerivativesDataSink(
            base_directory=output_dir,
            suffix="dwiref",
            **DWI_PREPROC_BASE_ENTITIES,
            dismiss_entities=["direction"],
            copy=True,
        ),
        name="ds_dwiref_json",
    )

    ds_dwi_mask = pe.Node(
        DerivativesDataSink(
            base_directory=output_dir,
            suffix="mask",
            desc="brain",
            space="dwi",
            compress=True,
            dismiss_entities=["direction"],
            copy=True,
        ),
        name="ds_dwi_mask",
    )

    ds_dwi2t1w_aff = pe.Node(
        DerivativesDataSink(
            base_directory=output_dir,
            **{
                "from": "dwi",
                "to": "T1w",
                "mode": "image",
                "suffix": "xfm",
                "extension": "txt",
            },
            dismiss_entities=["direction"],
            copy=True,
        ),
        name="ds_dwi2t1w_aff",
    )

    ds_t1w2dwi_aff = pe.Node(
        DerivativesDataSink(
            base_directory=output_dir,
            **{
                "from": "T1w",
                "to": "dwi",
                "mode": "image",
                "suffix": "xfm",
                "extension": "txt",
            },
            dismiss_entities=["direction"],
            copy=True,
        ),
        name="ds_t1w2dwi_aff",
    )

    workflow.connect(
        [
            (
                inputnode,
                ds_eddy_qc,
                [("eddy_qc", "eddy_qc")],
            ),
            (
                ds_dwi_preproc,
                ds_eddy_qc,
                [("out_file", "source_file")],
            ),
            (
                inputnode,
                ds_eddy_qc_plot,
                [("eddy_qc_plot", "in_file"), ("source_file", "source_file")],
            ),
            (
                inputnode,
                ds_sdc_report,
                [("sdc_report", "in_file"), ("source_file", "source_file")],
            ),
            (
                inputnode,
                ds_coreg_report,
                [("coreg_report", "in_file"), ("source_file", "source_file")],
            ),
            (
                inputnode,
                ds_dwi_preproc,
                [("dwi_preproc", "in_file"), ("source_file", "source_file")],
            ),
            (
                inputnode,
                listify_gradients,
                [
                    ("dwi_grad", "in1"),
                    ("dwi_bvec", "in2"),
                    ("dwi_bval", "in3"),
                    ("dwi_json", "in4"),
                ],
            ),
            (
                listify_gradients,
                ds_dwi_supp,
                [("out", "in_file")],
            ),
            (
                inputnode,
                ds_dwi_supp,
                [("source_file", "source_file")],
            ),
            (
                inputnode,
                ds_dwiref,
                [("dwi_reference", "in_file"), ("source_file", "source_file")],
            ),
            (
                inputnode,
                ds_dwiref_json,
                [
                    ("dwi_reference_json", "in_file"),
                    ("source_file", "source_file"),
                ],
            ),
            (
                inputnode,
                ds_dwi_mask,
                [
                    ("dwi_brain_mask", "in_file"),
                    ("source_file", "source_file"),
                ],
            ),
            (
                inputnode,
                ds_dwi2t1w_aff,
                [("dwi2t1w_aff", "in_file"), ("source_file", "source_file")],
            ),
            (
                inputnode,
                ds_t1w2dwi_aff,
                [("t1w2dwi_aff", "in_file"), ("source_file", "source_file")],
            ),
        ]
    )

    return workflow
