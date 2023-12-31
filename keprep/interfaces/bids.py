# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
from pathlib import Path
from typing import Union

from bids import BIDSLayout
from bids.layout import Query
from nipype import logging
from nipype.interfaces.base import (
    BaseInterfaceInputSpec,
    OutputMultiObject,
    SimpleInterface,
    Str,
    TraitedSpec,
    traits,
)
from niworkflows.interfaces.bids import DerivativesDataSink as _DDSink

from keprep import config

LOGGER = logging.getLogger("nipype.interface")


class DerivativesDataSink(_DDSink):
    out_path_base = ""


__all__ = ("DerivativesDataSink",)


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
        "fmap": {"datatype": "fmap"},
        "dwi": {"datatype": "dwi", "suffix": "dwi"},
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


class _BIDSDataGrabberInputSpec(BaseInterfaceInputSpec):
    subject_data = traits.Dict(Str, traits.Any)
    subject_id = Str()


class _BIDSDataGrabberOutputSpec(TraitedSpec):
    out_dict = traits.Dict(desc="output data structure")
    fmap = OutputMultiObject(desc="output fieldmaps")
    bold = OutputMultiObject(desc="output functional images")
    sbref = OutputMultiObject(desc="output sbrefs")
    t1w = OutputMultiObject(desc="output T1w images")
    roi = OutputMultiObject(desc="output ROI images")
    t2w = OutputMultiObject(desc="output T2w images")
    flair = OutputMultiObject(desc="output FLAIR images")
    dwi = OutputMultiObject(desc="output DWI images")


class BIDSDataGrabber(SimpleInterface):
    """
    Collect files from a BIDS directory structure.

    .. testsetup::

        >>> data_dir_canary()

    >>> bids_src = BIDSDataGrabber(anat_only=False)
    >>> bids_src.inputs.subject_data = bids_collect_data(
    ...     str(datadir / 'ds114'), '01', bids_validate=False)[0]
    >>> bids_src.inputs.subject_id = '01'
    >>> res = bids_src.run()
    >>> res.outputs.t1w  # doctest: +ELLIPSIS +NORMALIZE_WHITESPACE
    ['.../ds114/sub-01/ses-retest/anat/sub-01_ses-retest_T1w.nii.gz',
     '.../ds114/sub-01/ses-test/anat/sub-01_ses-test_T1w.nii.gz']

    """

    input_spec = _BIDSDataGrabberInputSpec
    output_spec = _BIDSDataGrabberOutputSpec
    _require_dwis = True

    def __init__(self, *args, **kwargs):
        anat_only = kwargs.pop("anat_only")
        anat_derivatives = kwargs.pop("anat_derivatives", None)
        super().__init__(*args, **kwargs)
        if anat_only is not None:
            self._require_dwis = not anat_only
        self._require_t1w = anat_derivatives is None

    def _run_interface(self, runtime):
        bids_dict = self.inputs.subject_data

        self._results["out_dict"] = bids_dict
        self._results.update(bids_dict)

        if self._require_t1w and not bids_dict["t1w"]:
            raise FileNotFoundError(
                f"No T1w images found for subject sub-{self.inputs.subject_id}"
            )

        if self._require_dwis and not bids_dict["dwi"]:
            raise FileNotFoundError(
                f"No DWI images found for subject sub-{self.inputs.subject_id}"
            )

        for imtype in ["bold", "t2w", "flair", "fmap", "sbref", "roi", "dwi"]:
            if not bids_dict.get(imtype):
                LOGGER.info(
                    'No "%s" images found for sub-%s',
                    imtype,
                    self.inputs.subject_id,
                )

        return runtime


def get_fieldmap(file: Union[str, Path], layout: BIDSLayout) -> Path:
    """
    Locate a fieldmap file for a given image.

    Parameters
    ----------
    file : Union[str,Path]
        DWI image to find fieldmap for
    layout : BIDSLayout
        BIDSLayout object to search

    Returns
    -------
    Path
        Path to fieldmap file
    """
    file = Path(file)
    fieldmaps = layout.get_fieldmap(file, return_list=True)
    fieldmaps_to_remove = []
    fieldmap_to_keep = None
    for fieldmap in fieldmaps:
        for key, value in fieldmap.items():
            entities = layout.parse_file_entities(value)
            for filter_key, filter_value in config.execution.bids_filters[
                "fmap"
            ].items():
                if not entities.get(filter_key) == filter_value:
                    fieldmaps_to_remove.append(fieldmap)
                    break
            break
    for fieldmap in fieldmaps_to_remove:
        fieldmaps.remove(fieldmap)
    if len(fieldmaps) > 1:
        LOGGER.warning(
            "More than one fieldmap found for %s. Using %s",
            file,
            fieldmaps[0],
        )
    if fieldmaps:
        fieldmap_to_keep = fieldmaps[0].get("epi")

    return fieldmap_to_keep
