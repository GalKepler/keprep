import os
import warnings
from copy import deepcopy
from pathlib import Path

from nipype.interfaces import utility as niu
from nipype.pipeline import engine as pe
from packaging.version import Version

from keprep import config
from keprep.workflows.base.messages import (
    ANAT_DERIVATIVES_FAILED,
    BASE_POSTDESC,
    BASE_WORKFLOW_DESCRIPTION,
)
from keprep.workflows.dwi.workflow import init_dwi_preproc_wf


def init_keprep_wf():
    """
    Build *fMRIPrep*'s pipeline.

    This workflow organizes the execution of FMRIPREP, with a sub-workflow for
    each subject.

    If FreeSurfer's ``recon-all`` is to be run, a corresponding folder is created
    and populated with any needed template subjects under the derivatives folder.

    Workflow Graph
        .. workflow::
            :graph2use: orig
            :simple_form: yes

            from fmriprep.workflows.tests import mock_config
            from fmriprep.workflows.base import init_keprep_wf
            with mock_config():
                wf = init_keprep_wf()

    """
    # pylint: disable=import-outside-toplevel
    from niworkflows.engine.workflows import LiterateWorkflow as Workflow
    from niworkflows.interfaces.bids import BIDSFreeSurferDir

    # pylint: enable=import-outside-toplevel

    ver = Version(config.environment.version)

    keprep_wf = Workflow(name=f"keprep_{ver.major}_{ver.minor}_{ver.micro}_wf")
    keprep_wf.base_dir = config.execution.work_dir

    freesurfer = config.workflow.do_reconall
    if freesurfer:
        fsdir = pe.Node(
            BIDSFreeSurferDir(
                derivatives=config.execution.output_dir,
                freesurfer_home=os.getenv("FREESURFER_HOME"),
                spaces=config.workflow.spaces.get_fs_spaces(),  # type: ignore[attr-defined]
                minimum_fs_version="7.0.0",
            ),
            name=f"fsdir_run_{config.execution.run_uuid.replace('-', '_')}",
            run_without_submitting=True,
        )
        if config.execution.fs_subjects_dir is not None:
            fsdir.inputs.subjects_dir = str(config.execution.fs_subjects_dir.absolute())  # type: ignore[unreachable]

    participants: list = config.execution.participant_label  # type: ignore[assignment]  # pylint: disable=not-an-iterable
    for subject_id in list(participants):
        single_subject_wf = init_single_subject_wf(subject_id)  # type: ignore[operator]

        single_subject_wf.config["execution"]["crashdump_dir"] = str(
            Path(config.execution.keprep_dir)  # type: ignore[operator, attr-defined]
            / f"sub-{subject_id}"
            / "log"
            / config.execution.run_uuid
        )
        for node in single_subject_wf._get_all_nodes():
            node.config = deepcopy(single_subject_wf.config)
        if freesurfer:
            keprep_wf.connect(
                fsdir,
                "subjects_dir",
                single_subject_wf,
                "inputnode.subjects_dir",
            )
        else:
            keprep_wf.add_nodes([single_subject_wf])

        # Dump a copy of the config file into the log directory
        log_dir = (
            Path(config.execution.keprep_dir)  # type: ignore[operator, attr-defined]
            / f"sub-{subject_id}"
            / "log"
            / config.execution.run_uuid
        )
        log_dir.mkdir(exist_ok=True, parents=True)
        config.to_filename(log_dir / "keprep.toml")

    return keprep_wf


def init_single_subject_wf(subject_id: str):
    """
    Organize the preprocessing pipeline for a single subject.

    It collects and reports information about the subject, and prepares
    sub-workflows to perform anatomical and functional preprocessing.
    Anatomical preprocessing is performed in a single workflow, regardless of
    the number of sessions.
    Functional preprocessing is performed using a separate workflow for each
    individual BOLD series.

    Workflow Graph
        .. workflow::
            :graph2use: orig
            :simple_form: yes

            from fmriprep.workflows.tests import mock_config
            from fmriprep.workflows.base import init_single_subject_wf
            with mock_config():
                wf = init_single_subject_wf('01')

    Parameters
    ----------
    subject_id : :obj:`str`
        Subject label for this single-subject workflow.

    Inputs
    ------
    subjects_dir : :obj:`str`
        FreeSurfer's ``$SUBJECTS_DIR``.

    """
    # pylint: disable=import-outside-toplevel,import-error
    from niworkflows.engine.workflows import LiterateWorkflow as Workflow
    from niworkflows.interfaces.bids import BIDSInfo
    from niworkflows.interfaces.nilearn import NILEARN_VERSION
    from niworkflows.utils.misc import fix_multi_T1w_source_name
    from niworkflows.utils.spaces import Reference
    from smriprep.workflows.anatomical import init_anat_preproc_wf

    # pylint: enable=import-outside-toplevel,import-error
    from keprep.interfaces.bids import BIDSDataGrabber, collect_data
    from keprep.workflows.anatomical.post_smriprep import init_post_anatomical_wf

    name = f"single_subject_{subject_id}_wf"
    subject_data = collect_data(
        config.execution.layout,
        subject_id,
        bids_filters=config.execution.bids_filters,
    )[0]

    anat_only = config.workflow.anat_only
    anat_derivatives = config.execution.anat_derivatives
    spaces = config.workflow.spaces
    # Make sure we always go through these two checks
    if not anat_only and not subject_data["dwi"]:
        raise RuntimeError(
            f"No DWI images found for participant {subject_id}."
            "All workflows require DWI images."
        )

    if anat_derivatives:
        from smriprep.utils.bids import (  # type: ignore[unreachable] # pylint: disable=import-outside-toplevel,import-error
            collect_derivatives,
        )

        std_spaces = spaces.get_spaces(nonstandard=False, dim=(3,))  # noqa
        anat_derivatives = collect_derivatives(
            anat_derivatives.absolute(),
            subject_id,
            std_spaces,
            config.workflow.do_reconall,
        )
        if anat_derivatives is None:
            warning_message = ANAT_DERIVATIVES_FAILED.format(
                anat_derivatives=config.execution.anat_derivatives,
                subject_id=subject_id,
                spaces=", ".join(std_spaces),
                run_reconall=config.workflow.do_reconall,
            )
            config.loggers.workflow.warning(warning_message)

    if not anat_derivatives and not subject_data["t1w"]:
        raise FileNotFoundError(
            f"No T1w images found for participant {subject_id}. All workflows require T1w images."  # noqa
        )

    if subject_data["roi"]:
        warnings.warn(
            f"Lesion mask {subject_data['roi']} found. "
            "Future versions of fMRIPrep will use alternative conventions. "
            "Please refer to the documentation before upgrading.",
            FutureWarning,
        )

    workflow = Workflow(name=name)
    workflow.__desc__ = BASE_WORKFLOW_DESCRIPTION.format(
        keprep_ver=config.environment.version,
        nipype_ver=config.environment.nipype_version,
    )
    workflow.__postdesc__ = BASE_POSTDESC.format(nilearn_ver=NILEARN_VERSION)

    keprep_dir = str(config.execution.keprep_dir)  # type: ignore[attr-defined]

    inputnode = pe.Node(
        niu.IdentityInterface(fields=["subjects_dir"]), name="inputnode"
    )

    bidssrc = pe.Node(
        BIDSDataGrabber(
            subject_data=subject_data,
            anat_only=anat_only,
            anat_derivatives=anat_derivatives,
            subject_id=subject_id,
        ),
        name="bidssrc",
    )

    bids_info = pe.Node(
        BIDSInfo(bids_dir=config.execution.bids_dir, bids_validate=False),
        name="bids_info",
    )

    # Preprocessing of T1w (includes registration to MNI)
    anat_preproc_wf = init_anat_preproc_wf(
        bids_root=str(config.execution.bids_dir),
        debug=config.execution.debug,
        existing_derivatives=anat_derivatives,
        freesurfer=config.workflow.do_reconall,
        longitudinal=config.workflow.longitudinal,
        omp_nthreads=config.nipype.omp_nthreads,
        output_dir=keprep_dir,
        hires=config.workflow.hires,
        skull_strip_fixed_seed=config.workflow.skull_strip_fixed_seed,
        skull_strip_mode=config.workflow.skull_strip_t1w,
        skull_strip_template=Reference.from_string(
            config.workflow.skull_strip_template
        )[0],
        spaces=spaces,
        t1w=subject_data["t1w"],
        t2w=subject_data["t2w"],
        cifti_output=config.workflow.cifti_output,
    )
    # fmt:off
    workflow.connect([
        (inputnode, anat_preproc_wf, [('subjects_dir', 'inputnode.subjects_dir')]),
        (bids_info, anat_preproc_wf, [(('subject', _prefix), 'inputnode.subject_id')]),
        (bidssrc, anat_preproc_wf, [('t1w', 'inputnode.t1w'),
                                    ('t2w', 'inputnode.t2w'),
                                    ('roi', 'inputnode.roi'),
                                    ('flair', 'inputnode.flair')]),
    ])

    if not anat_derivatives:
        workflow.connect([
            (bidssrc, bids_info, [(('t1w', fix_multi_T1w_source_name), 'in_file')]),
        ])
    else:
        workflow.connect([ # type: ignore[unreachable]
            (bidssrc, bids_info, [(('dwi', fix_multi_T1w_source_name), 'in_file')]),
        ])
    # fmt:on

    post_smriprep_wf = init_post_anatomical_wf()
    workflow.connect(
        [
            (
                anat_preproc_wf,
                post_smriprep_wf,
                [
                    ("outputnode.t1w_preproc", "inputnode.t1w_preproc"),
                    ("outputnode.t2w_preproc", "inputnode.t2w_preproc"),
                    ("outputnode.t1w_mask", "inputnode.t1w_mask"),
                    ("outputnode.subjects_dir", "inputnode.fs_subjects_dir"),
                    ("outputnode.subject_id", "inputnode.subject_id"),
                ],
            )
        ]
    )

    # Overwrite ``out_path_base`` of smriprep's DataSinks
    for node in workflow.list_node_names():
        if node.split(".")[-1].startswith("ds_"):
            workflow.get_node(node).interface.out_path_base = ""

    if anat_only:
        return workflow

    for dwi_file in subject_data["dwi"]:
        dwi_preproc_wf = init_dwi_preproc_wf(dwi_file, subject_data)
        workflow.connect(
            [
                (
                    anat_preproc_wf,
                    dwi_preproc_wf,
                    [
                        ("outputnode.t1w_preproc", "inputnode.t1w_preproc"),
                        ("outputnode.t1w_mask", "inputnode.t1w_mask"),
                    ],
                ),
                (
                    post_smriprep_wf,
                    dwi_preproc_wf,
                    [("outputnode.five_tissue_type", "inputnode.five_tissue_type")],
                ),
            ]
        )
    return workflow


def _prefix(subid):
    return subid if subid.startswith("sub-") else f"sub-{subid}"
