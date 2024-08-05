# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
#
# Copyright 2021 The NiPreps Developers <nipreps@gmail.com>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# We support and encourage derived works from this project, please read
# about our expectations at
#
#     https://www.nipreps.org/community/licensing/
#
"""Interfaces to generate reportlets."""

import os
import time

from nipype.interfaces import freesurfer as fs
from nipype.interfaces.base import (
    BaseInterfaceInputSpec,
    Directory,
    File,
    InputMultiObject,
    SimpleInterface,
    Str,
    TraitedSpec,
    isdefined,
    traits,
)

SUBJECT_TEMPLATE = """\
\t<ul class="elem-desc">
\t\t<li>Subject ID: {subject_id}</li>
\t\t<li>Structural images: {n_t1s:d} T1-weighted {t2w}</li>
\t\t<li>Diffusion Weighted Images: {n_dwi:d}</li>
\t\t<li>Standard output spaces: {std_spaces}</li>
\t\t<li>Non-standard output spaces: {nstd_spaces}</li>
\t\t<li>FreeSurfer reconstruction: {freesurfer_status}</li>
\t</ul>
"""

DIFFUSION_TEMPLATE = """\t\t<h3 class="elem-title">Summary</h3>
\t\t<ul class="elem-desc">
\t\t\t<li>Phase-encoding (PE) direction: {pedir}</li>
\t\t\t<li>Susceptibility distortion correction: {sdc}</li>
\t\t\t<li>Coregistration Transform: {coregistration}</li>
\t\t\t<li>Denoising Method: {denoise_method}</li>
\t\t\t<li>Denoising Window: {denoise_window}</li>
\t\t\t<li>HMC Model: {hmc_model}</li>
\t\t</ul>
"""
# {validation_reports}

ABOUT_TEMPLATE = """\t<ul>
\t\t<li>KePrep version: {version}</li>
\t\t<li>KePrep command: <code>{command}</code></li>
\t\t<li>Date preprocessed: {date}</li>
\t</ul>
</div>
"""


class SummaryOutputSpec(TraitedSpec):
    out_report = File(exists=True, desc="HTML segment containing summary")


class SummaryInterface(SimpleInterface):
    output_spec = SummaryOutputSpec

    def _run_interface(self, runtime):
        segment = self._generate_segment()
        fname = os.path.join(runtime.cwd, "report.html")
        with open(fname, "w") as fobj:
            fobj.write(segment)
        self._results["out_report"] = fname
        return runtime

    def _generate_segment(self):
        raise NotImplementedError


class SubjectSummaryInputSpec(BaseInterfaceInputSpec):
    t1w = InputMultiObject(File(exists=True), desc="T1w structural images")
    t2w = InputMultiObject(File(exists=True), desc="T2w structural images")
    subjects_dir = Directory(desc="FreeSurfer subjects directory")
    subject_id = Str(desc="Subject ID")
    dwi = InputMultiObject(
        traits.Either(File(exists=True), traits.List(File(exists=True))),
        desc="DWI files",
    )
    std_spaces = traits.List(Str, desc="list of standard spaces")
    nstd_spaces = traits.List(Str, desc="list of non-standard spaces")


class SubjectSummaryOutputSpec(SummaryOutputSpec):
    # This exists to ensure that the summary is run prior to the first ReconAll
    # call, allowing a determination whether there is a pre-existing directory
    subject_id = Str(desc="FreeSurfer subject ID")


class SubjectSummary(SummaryInterface):
    input_spec = SubjectSummaryInputSpec
    output_spec = SubjectSummaryOutputSpec

    def _run_interface(self, runtime):
        if isdefined(self.inputs.subject_id):
            self._results["subject_id"] = self.inputs.subject_id
        return super(SubjectSummary, self)._run_interface(runtime)

    def _generate_segment(self):
        if not isdefined(self.inputs.subjects_dir):
            freesurfer_status = "Not run"
        else:
            recon = fs.ReconAll(
                subjects_dir=self.inputs.subjects_dir,
                subject_id=self.inputs.subject_id,
                T1_files=self.inputs.t1w,
                flags="-noskullstrip",
            )
            if recon.cmdline.startswith("echo"):
                freesurfer_status = "Pre-existing directory"
            else:
                freesurfer_status = "Run by KePrep"

        t2w_seg = ""
        if self.inputs.t2w:
            t2w_seg = "(+ {:d} T2-weighted)".format(len(self.inputs.t2w))

        dwi_files = self.inputs.dwi if isdefined(self.inputs.dwi) else []
        dwi_files = [s[0] if isinstance(s, list) else s for s in dwi_files]

        return SUBJECT_TEMPLATE.format(
            subject_id=self.inputs.subject_id,
            n_t1s=len(self.inputs.t1w),
            t2w=t2w_seg,
            n_dwi=len(dwi_files),
            std_spaces=", ".join(self.inputs.std_spaces),
            nstd_spaces=", ".join(self.inputs.nstd_spaces),
            freesurfer_status=freesurfer_status,
        )


class AboutSummaryInputSpec(BaseInterfaceInputSpec):
    version = Str(desc="KePrep version")
    command = Str(desc="KePrep command")
    # Date not included - update timestamp only if version or command changes


class AboutSummary(SummaryInterface):
    input_spec = AboutSummaryInputSpec

    def _generate_segment(self):
        return ABOUT_TEMPLATE.format(
            version=self.inputs.version,
            command=self.inputs.command,
            date=time.strftime("%Y-%m-%d %H:%M:%S %z"),
        )


class DiffusionSummaryInputSpec(BaseInterfaceInputSpec):
    distortion_correction = traits.Str(
        default_value="TOPUP",
        desc="Susceptibility distortion correction method",
        mandatory=False,
    )
    pe_direction = traits.Enum(
        None,
        "i",
        "i-",
        "j",
        "j-",
        mandatory=True,
        desc="Phase-encoding direction detected",
    )
    impute_slice_threshold = traits.CFloat(desc="threshold for imputing a slice")
    hmc_model = traits.Str(desc="model used for hmc")
    b0_to_t1w_transform = traits.Enum(
        "Rigid", "Affine", desc="Transform type for coregistration"
    )
    denoise_method = traits.Str(desc="method used for image denoising")
    dwi_denoise_window = traits.Either(
        traits.Int(), traits.Str(), desc="window size for dwidenoise"
    )
    output_spaces = traits.List(desc="Target spaces")
    confounds_file = File(exists=True, desc="Confounds file")
    validation_reports = InputMultiObject(File(exists=True))


class DiffusionSummary(SummaryInterface):
    input_spec = DiffusionSummaryInputSpec

    def _generate_segment(self):
        if self.inputs.pe_direction is None:
            pedir = "MISSING - Assuming Anterior-Posterior"
        else:
            pedir = {"i": "Left-Right", "j": "Anterior-Posterior"}[
                self.inputs.pe_direction[0]
            ]

        if isdefined(self.inputs.confounds_file):
            with open(self.inputs.confounds_file) as cfh:
                conflist = cfh.readline().strip("\n").strip()  # noqa: F841
        else:
            conflist = ""  # noqa: F841

        validation_summaries = []  # noqa: F841
        # for summary in self.inputs.validation_reports:
        #     with open(summary, "r") as summary_f:
        #         validation_summaries.extend(summary_f.readlines())
        # validation_summary = "\n".join(validation_summaries)

        return DIFFUSION_TEMPLATE.format(
            pedir=pedir,
            sdc=self.inputs.distortion_correction,
            coregistration=self.inputs.b0_to_t1w_transform,
            hmc_model=self.inputs.hmc_model,
            denoise_method=self.inputs.denoise_method,
            denoise_window=self.inputs.dwi_denoise_window,
            # validation_reports=validation_summary,
        )
