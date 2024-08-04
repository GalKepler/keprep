# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

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

LOGGER = logging.getLogger("nipype.interface")

CUSTOM_PATH_PATTERNS = [
    "sub-{subject}[/ses-{session}]/{datatype<dwi>|dwi}/sub-{subject}[_ses-{session}][_acq-{acquisition}][_rec-{reconstruction}][_dir-{direction}][_run-{run}][_space-{space}][_cohort-{cohort}][_res-{resolution}][_desc-{desc}]_{suffix<dwi|dwiref|epiref|lowb|dseg|streamlines>}{extension<.json|.nii.gz|.nii|.tck|.trk>|.nii.gz}",  # pylint: disable=line-too-long
    "sub-{subject}[/ses-{session}]/{datatype<dwi>|dwi}/{desc}",
]


class DerivativesDataSink(_DDSink):
    out_path_base = ""
    _file_patterns = tuple(list(_DDSink._file_patterns) + CUSTOM_PATH_PATTERNS)


__all__ = ("DerivativesDataSink",)


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
