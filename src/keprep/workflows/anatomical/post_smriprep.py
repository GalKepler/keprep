import nipype.pipeline.engine as pe
from nipype.interfaces import utility as niu

from keprep import config
from keprep.interfaces import mrtrix3 as mrt


def locate_fs_subject_dir(subject_id: str, fs_subjects_dir: str) -> str:
    """
    Locate the freesurfer subject directory

    Parameters
    ----------
    subject_id : str
        subject id
    fs_subjects_dir : str
        freesurfer subjects directory

    Returns
    -------
    str
        path to the freesurfer subject directory
    """
    from pathlib import Path

    return str(Path(fs_subjects_dir) / subject_id)


def init_post_anatomical_wf(name: str = "post_anatomical_wf") -> pe.Workflow:
    """
    Initialize the post-anatomical processing

    Parameters
    ----------
    name : str, optional
        name of the workflow (default: "post_anatomical_wf

    Returns
    -------
    pe.Workflow
        the workflow
    """
    wf = pe.Workflow(name=name)

    inputnode = pe.Node(
        niu.IdentityInterface(
            fields=[
                "t1w_preproc",
                "t2w_preproc",
                "t1w_mask",
                "fs_subjects_dir",
                "subject_id",
            ]
        ),
        name="inputnode",
    )
    outputnode = pe.Node(
        niu.IdentityInterface(fields=["five_tissue_type"]), name="outputnode"
    )

    algo_5tt = config.workflow.five_tissue_type_algorithm

    five_tissue_type = pe.Node(
        mrt.Generate5tt(
            algorithm=algo_5tt,
            out_file="5tt.mif",
            nthreads=config.nipype.omp_nthreads,
        ),
        name="five_tissue_type",
    )
    if algo_5tt == "fsl":
        wf.connect(
            [
                (
                    inputnode,
                    five_tissue_type,
                    [
                        ("t1w_preproc", "in_file"),
                    ],
                ),
            ]
        )
    elif algo_5tt == "hsvs":
        fs_subject_dir = pe.Node(
            niu.Function(
                input_names=["subject_id", "fs_subjects_dir"],
                output_names=["fs_subject_dir"],
                function=locate_fs_subject_dir,
            ),
            name="fs_subject_dir",
        )
        wf.connect(
            [
                (
                    inputnode,
                    fs_subject_dir,
                    [
                        ("subject_id", "subject_id"),
                        ("fs_subjects_dir", "fs_subjects_dir"),
                    ],
                ),
                (fs_subject_dir, five_tissue_type, [("fs_subject_dir", "in_file")]),
            ]
        )

    wf.connect([(five_tissue_type, outputnode, [("out_file", "five_tissue_type")])])
    return wf
