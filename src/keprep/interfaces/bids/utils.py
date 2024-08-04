import json
import os
from pathlib import Path

from bids import BIDSLayout
from bids.layout import Query, parse_file_entities


def collect_data(
    bids_dir,
    participant_label,
    session_id=Query.OPTIONAL,
    bids_validate=True,
    bids_filters=None,
):
    """
    Use pybids to retrieve the input data for a given participant.

    .. testsetup::

        >>> data_dir_canary()

    Parameters
    ----------
    bids_dir : :obj:`str` or :obj:`bids.layout.BIDSLayout`
        The BIDS directory
    participant_label : :obj:`str`
        The participant identifier
    session_id : :obj:`str`, None, or :obj:`bids.layout.Query`
        The session identifier. By default, all sessions will be used.
    task : :obj:`str` or None
        The task identifier (for BOLD queries)
    echo : :obj:`int` or None
        The echo identifier (for BOLD queries)
    bids_validate : :obj:`bool`
        Whether the `bids_dir` is validated upon initialization
    bids_filters: :obj:`dict` or None
        Custom filters to alter default queries

    Examples
    --------
    >>> bids_root, _ = collect_data(str(datadir / 'ds054'), '100185',
    ...                             bids_validate=False)
    >>> bids_root['fmap']  # doctest: +ELLIPSIS
    ['.../ds054/sub-100185/fmap/sub-100185_magnitude1.nii.gz', \
'.../ds054/sub-100185/fmap/sub-100185_magnitude2.nii.gz', \
'.../ds054/sub-100185/fmap/sub-100185_phasediff.nii.gz']
    >>> bids_root['bold']  # doctest: +ELLIPSIS
    ['.../ds054/sub-100185/func/sub-100185_task-machinegame_run-01_bold.nii.gz', \
'.../ds054/sub-100185/func/sub-100185_task-machinegame_run-02_bold.nii.gz', \
'.../ds054/sub-100185/func/sub-100185_task-machinegame_run-03_bold.nii.gz', \
'.../ds054/sub-100185/func/sub-100185_task-machinegame_run-04_bold.nii.gz', \
'.../ds054/sub-100185/func/sub-100185_task-machinegame_run-05_bold.nii.gz', \
'.../ds054/sub-100185/func/sub-100185_task-machinegame_run-06_bold.nii.gz']
    >>> bids_root['sbref']  # doctest: +ELLIPSIS
    ['.../ds054/sub-100185/func/sub-100185_task-machinegame_run-01_sbref.nii.gz', \
'.../ds054/sub-100185/func/sub-100185_task-machinegame_run-02_sbref.nii.gz', \
'.../ds054/sub-100185/func/sub-100185_task-machinegame_run-03_sbref.nii.gz', \
'.../ds054/sub-100185/func/sub-100185_task-machinegame_run-04_sbref.nii.gz', \
'.../ds054/sub-100185/func/sub-100185_task-machinegame_run-05_sbref.nii.gz', \
'.../ds054/sub-100185/func/sub-100185_task-machinegame_run-06_sbref.nii.gz']
    >>> bids_root['t1w']  # doctest: +ELLIPSIS
    ['.../ds054/sub-100185/anat/sub-100185_T1w.nii.gz']
    >>> bids_root['t2w']  # doctest: +ELLIPSIS
    []
    >>> bids_root, _ = collect_data(str(datadir / 'ds051'), '01',
    ...                             bids_validate=False,
    ...                             bids_filters={'t1w':{'run': 1, 'session': None}})
    >>> bids_root['t1w']  # doctest: +ELLIPSIS
    ['.../ds051/sub-01/anat/sub-01_run-01_T1w.nii.gz']

    """
    if isinstance(bids_dir, BIDSLayout):
        layout = bids_dir
    else:
        layout = BIDSLayout(str(bids_dir), validate=bids_validate)

    layout_get_kwargs = {
        "return_type": "file",
        "subject": participant_label,
        "extension": [".nii", ".nii.gz"],
        "session": session_id,
    }

    queries = {
        "fmap": {"datatype": "dwi", "suffix": "dwi", "direction": "PA"},
        "dwi": {"datatype": "dwi", "suffix": "dwi", "direction": "AP"},
        "sbref": {
            "datatype": "dwi",
            "suffix": "sbref",
        },
        "flair": {
            "datatype": "anat",
            "suffix": "FLAIR",
            "part": ["mag", None],
        },
        "t2w": {"datatype": "anat", "suffix": "T2w", "part": ["mag", None]},
        "t1w": {"datatype": "anat", "suffix": "T1w", "part": ["mag", None]},
        "roi": {"datatype": "anat", "suffix": "roi"},
    }
    bids_filters = bids_filters or {}
    for acq, entities in bids_filters.items():
        queries[acq].update(entities)  # type: ignore[attr-defined]
        for entity in list(layout_get_kwargs.keys()):
            if entity in entities:
                # avoid clobbering layout.get
                del layout_get_kwargs[entity]
    subj_data = {
        dtype: sorted(layout.get(**layout_get_kwargs, **query))
        for dtype, query in queries.items()
    }

    return subj_data, layout


def get_fieldmap(dwi_file: str | Path, subject_data: dict) -> str | None:
    """
    Locate the fieldmap (dir-PA) associated with the dwi file of the session.

    Parameters
    ----------
    dwi_file : Union[str,Path]
        path to DWI file
    subject_data : dict
        subject data

    Returns
    -------
    str
        path to the fieldmap file
    """
    dwi_entities = parse_file_entities(dwi_file)
    dwi_dir = dwi_entities["direction"]
    fmap_dir = dwi_dir[::-1]  # reverse the direction
    avaliable_fmaps = subject_data.get("fmap")
    if not avaliable_fmaps:
        raise FileNotFoundError(f"No fieldmap found for <{dwi_file}>")
    for fmap in avaliable_fmaps:
        fmap_entities = parse_file_entities(fmap)
        if (
            fmap_entities["direction"] == fmap_dir
            and fmap_entities["session"] == dwi_entities["session"]
        ):
            return fmap
    return None


def write_derivative_description(bids_dir, deriv_dir):
    from keprep import __version__

    DOWNLOAD_URL = (
        f"https://github.com/GalKepler/keprep/archive/refs/tags/v{__version__}.tar.gz"
    )

    desc = {
        "Name": "KePrep output",
        "BIDSVersion": "1.9.0",
        "PipelineDescription": {
            "Name": "keprep",
            "Version": __version__,
            "CodeURL": DOWNLOAD_URL,
        },
        "GeneratedBy": [
            {
                "Name": "keprep",
                "Version": __version__,
                "CodeURL": DOWNLOAD_URL,
            }
        ],
        "CodeURL": "https://github.com/GalKepler/keprep",
        "HowToAcknowledge": "Please cite our paper and "
        "include the generated citation boilerplate within the Methods "
        "section of the text.",
    }

    # Keys deriving from source dataset
    fname = os.path.join(bids_dir, "dataset_description.json")
    if os.path.exists(fname):
        with open(fname) as fobj:
            orig_desc = json.load(fobj)
    else:
        orig_desc = {}

    if "DatasetDOI" in orig_desc:
        desc["SourceDatasetsURLs"] = [
            "https://doi.org/{}".format(orig_desc["DatasetDOI"])
        ]
    if "License" in orig_desc:
        desc["License"] = orig_desc["License"]

    with open(os.path.join(deriv_dir, "dataset_description.json"), "w") as fobj:
        json.dump(desc, fobj, indent=4)


def write_bidsignore(deriv_dir):
    bids_ignore = (
        "*.html",
        "logs/",
        "figures/",  # Reports
        "*_xfm.*",  # Unspecified transform files
        "*.surf.gii",  # Unspecified structural outputs
        # Unspecified functional outputs
        "*_boldref.nii.gz",
        "*_bold.func.gii",
        "*_mixing.tsv",
        "*_timeseries.tsv",
    )
    ignore_file = Path(deriv_dir) / ".bidsignore"

    ignore_file.write_text("\n".join(bids_ignore) + "\n")
