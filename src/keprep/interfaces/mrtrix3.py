import os.path as op
import shlex
from pathlib import Path

from nipype.interfaces.base import Directory, File, TraitedSpec, traits
from nipype.interfaces.mrtrix3.base import MRTrix3Base, MRTrix3BaseInputSpec
from nipype.utils.filemanip import get_dependencies, which
from nipype.utils.subprocess import run_command


class MRConvertInputSpec(MRTrix3BaseInputSpec):
    in_file = File(
        exists=True,
        argstr="%s",
        mandatory=True,
        position=-2,
        desc="input image",
    )
    out_file = File(
        "dwi.mif",
        argstr="%s",
        mandatory=True,
        position=-1,
        usedefault=True,
        desc="output image",
    )
    coord = traits.List(
        traits.Int,
        sep=" ",
        argstr="-coord %s",
        desc="extract data at the specified coordinates",
    )
    vox = traits.List(
        traits.Float,
        sep=",",
        argstr="-vox %s",
        desc="change the voxel dimensions",
    )
    axes = traits.List(
        traits.Int,
        sep=",",
        argstr="-axes %s",
        desc="specify the axes that will be used",
    )
    scaling = traits.List(
        traits.Float,
        sep=",",
        argstr="-scaling %s",
        desc="specify the data scaling parameter",
    )
    json_import = File(
        exists=True,
        argstr="-json_import %s",
        mandatory=False,
        desc="import data from a JSON file into header key-value pairs",
    )
    json_export = File(
        exists=False,
        argstr="-json_export %s",
        mandatory=False,
        desc="export data from an image header key-value pairs into a JSON file",
    )
    out_mrtrix_grad = File(
        exists=False,
        argstr="-export_grad_mrtrix %s",
        mandatory=False,
        desc="export the gradient table in MRtrix format",
    )


class MRConvertOutputSpec(TraitedSpec):
    out_file = File(exists=True, desc="output image")
    json_export = File(
        exists=True,
        desc="exported data from an image header key-value pairs in a JSON file",
    )
    out_bvec = File(exists=True, desc="export bvec file in FSL format")
    out_bval = File(exists=True, desc="export bvec file in FSL format")
    out_mrtrix_grad = File(
        exists=True, desc="export the gradient table in MRtrix format"
    )


class MRConvert(MRTrix3Base):  # pylint: disable=abstract-method
    """
    Perform conversion between different file types and optionally extract a subset of the input image.

    Example
    -------

    >>> import nipype.interfaces.mrtrix3 as mrt
    >>> mrconvert = mrt.MRConvert()
    >>> mrconvert.inputs.in_file = 'dwi.nii.gz'
    >>> mrconvert.inputs.grad_fsl = ('bvecs', 'bvals')
    >>> mrconvert.cmdline                             # doctest: +ELLIPSIS
    'mrconvert -fslgrad bvecs bvals dwi.nii.gz dwi.mif'
    >>> mrconvert.run()                               # doctest: +SKIP
    """

    _cmd = "mrconvert"
    input_spec = MRConvertInputSpec
    output_spec = MRConvertOutputSpec

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["out_file"] = op.abspath(self.inputs.out_file)
        if self.inputs.json_export:
            outputs["json_export"] = op.abspath(self.inputs.json_export)
        if self.inputs.out_bvec:
            outputs["out_bvec"] = op.abspath(self.inputs.out_bvec)
        if self.inputs.out_bval:
            outputs["out_bval"] = op.abspath(self.inputs.out_bval)
        if self.inputs.out_mrtrix_grad:
            outputs["out_mrtrix_grad"] = op.abspath(self.inputs.out_mrtrix_grad)
        return outputs


class Generate5ttInputSpec(MRTrix3BaseInputSpec):
    algorithm = traits.Enum(
        "fsl",
        "gif",
        "freesurfer",
        "hsvs",
        argstr="%s",
        position=-3,
        mandatory=True,
        desc="tissue segmentation algorithm",
    )
    in_file = traits.Either(
        File(exists=True),
        traits.Directory(exists=True),
        argstr="%s",
        mandatory=True,
        position=-2,
        desc="input image",
    )

    out_file = File(argstr="%s", mandatory=True, position=-1, desc="output image")


class Generate5ttOutputSpec(TraitedSpec):
    out_file = File(exists=True, desc="output image")


class Generate5tt(MRTrix3Base):
    """
    Generate a 5TT image suitable for ACT using the selected algorithm


    Example
    -------

    >>> import nipype.interfaces.mrtrix3 as mrt
    >>> gen5tt = mrt.Generate5tt()
    >>> gen5tt.inputs.in_file = 'T1.nii.gz'
    >>> gen5tt.inputs.algorithm = 'fsl'
    >>> gen5tt.inputs.out_file = '5tt.mif'
    >>> gen5tt.cmdline                             # doctest: +ELLIPSIS
    '5ttgen fsl T1.nii.gz 5tt.mif'
    >>> gen5tt.run()                               # doctest: +SKIP
    """

    _cmd = "5ttgen"
    input_spec = Generate5ttInputSpec
    output_spec = Generate5ttOutputSpec

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["out_file"] = op.abspath(self.inputs.out_file)
        return outputs


class TckSiftInputSpec(MRTrix3BaseInputSpec):
    in_file = File(
        exists=True,
        argstr="%s",
        mandatory=True,
        position=-3,
        desc="input tractogram",
    )
    in_fod = File(
        exists=True,
        argstr="%s",
        mandatory=True,
        position=-2,
        desc="input FOD image",
    )
    out_file = File(
        "sift.tck",
        argstr="%s",
        mandatory=True,
        position=-1,
        usedefault=True,
        desc="output sift tractogram",
    )
    act_file = File(
        exists=True,
        argstr="-act %s",
        desc="ACT five-tissue-type segmentation image",
    )
    fd_scale_gm = traits.Bool(
        default_value=True,
        argstr="-fd_scale_gm",
        desc="heuristically downsize the fibre density estimates based on the presence of GM in the voxel.",  # pylint: disable=line-too-long
    )
    no_dilate_lut = traits.Bool(
        default_value=False,
        argstr="-no_dilate_lut",
        desc="do NOT dilate FOD lobe lookup tables.",
    )
    remove_untracked = traits.Bool(
        default_value=False,
        argstr="-remove_untracked",
        desc="emove FOD lobes that do not have any streamline density attributed to them.",  # pylint: disable=line-too-long
    )
    fd_thresh = traits.Float(
        argstr="-fd_thresh %f",
        desc="fibre density threshold.",
    )
    out_csv = File(
        exists=False,
        argstr="-csv %s",
        desc="output statistics of execution per iteration to a .csv file",
    )
    out_mu = File(
        exists=False,
        argstr="-out_mu %s",
        desc="output the final value of SIFT proportionality coefficient mu to a text file",  # pylint: disable=line-too-long
    )
    output_debug = traits.Directory(
        exists=False,
        argstr="-output_debug %s",
        desc="output debugging information to a directory",
    )
    out_selection = File(
        exists=False,
        argstr="-out_selection %s",
        desc="output a text file containing the binary selection of streamlines",
    )
    term_number = traits.Int(
        argstr="-term_number %d",
        desc="continue filtering until this number of streamlines remain",
    )
    term_ratio = traits.Float(
        argstr="-term_ratio %f",
        desc="termination ratio; defined as the ratio between reduction in cost function, and reduction in density of streamlines",  # pylint: disable=line-too-long
    )
    term_mu = traits.Float(
        argstr="-term_mu %f",
        desc="terminate filtering once the SIFT proportionality coefficient reaches a given value",  # pylint: disable=line-too-long
    )


class TckSiftOutputSpec(TraitedSpec):
    out_file = File(exists=True, desc="output sift tractogram")
    out_csv = File(exists=True, desc="output statistics of execution per iteration")
    out_mu = File(
        exists=True,
        desc="output the final value of SIFT proportionality coefficient mu to a text file",  # pylint: disable=line-too-long
    )
    out_selection = File(
        exists=True,
        desc="output a text file containing the binary selection of streamlines",
    )


class TckSift(MRTrix3Base):  # pylint: disable=abstract-method
    """
    Select the streamlines from a tractogram that are most consistent with the
    underlying FOD image.

    Example
    -------
    >>> import nipype.interfaces.mrtrix3 as mrt
    >>> sift = mrt.TCKSift()
    >>> sift.inputs.in_file = 'tracks.tck'
    >>> sift.inputs.in_fod = 'fod.mif'
    >>> sift.cmdline
    'tcksift tracks.tck fod.mif sift.tck'
    >>> sift.run()  # doctest: +SKIP
    """

    _cmd = "tcksift"
    input_spec = TckSiftInputSpec
    output_spec = TckSiftOutputSpec

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["out_file"] = op.abspath(self.inputs.out_file)
        if self.inputs.out_csv:
            outputs["out_csv"] = op.abspath(self.inputs.out_csv)
        if self.inputs.out_mu:
            outputs["out_mu"] = op.abspath(self.inputs.out_mu)
        if self.inputs.out_selection:
            outputs["out_selection"] = op.abspath(self.inputs.out_selection)
        return outputs


class DWIPreprocInputSpec(MRTrix3BaseInputSpec):
    in_file = File(
        exists=True,
        argstr="%s",
        position=0,
        mandatory=True,
        desc="input DWI image",
    )
    out_file = File(
        "preproc.mif",
        argstr="%s",
        mandatory=True,
        position=1,
        usedefault=True,
        desc="output file after preprocessing",
    )
    rpe_options = traits.Enum(
        "none",
        "pair",
        "all",
        "header",
        argstr="-rpe_%s",
        position=2,
        mandatory=True,
        desc='Specify acquisition phase-encoding design. "none" for no reversed phase-encoding image, "all" for all DWIs have opposing phase-encoding acquisition, "pair" for using a pair of b0 volumes for inhomogeneity field estimation only, and "header" for phase-encoding information can be found in the image header(s)',
    )
    pe_dir = traits.Str(
        argstr="-pe_dir %s",
        desc="Specify the phase encoding direction of the input series, can be a signed axis number (e.g. -0, 1, +2), an axis designator (e.g. RL, PA, IS), or NIfTI axis codes (e.g. i-, j, k)",
    )
    ro_time = traits.Float(
        argstr="-readout_time %f",
        desc="Total readout time of input series (in seconds)",
    )
    in_epi = File(
        exists=True,
        argstr="-se_epi %s",
        desc="Provide an additional image series consisting of spin-echo EPI images, which is to be used exclusively by topup for estimating the inhomogeneity field (i.e. it will not form part of the output image series)",
    )
    align_seepi = traits.Bool(
        argstr="-align_seepi",
        desc="Achieve alignment between the SE-EPI images used for inhomogeneity field estimation, and the DWIs",
    )
    json_import = File(
        exists=True,
        argstr="-json_import %s",
        desc="Import image header information from an associated JSON file (may be necessary to determine phase encoding information)",
    )
    topup_options = traits.Str(
        argstr='-topup_options "%s"',
        desc="Manually provide additional command-line options to the topup command",
    )
    eddy_options = traits.Str(
        argstr='-eddy_options "%s"',
        desc="Manually provide additional command-line options to the eddy command",
    )
    eddy_mask = File(
        exists=True,
        argstr="-eddy_mask %s",
        desc="Provide a processing mask to use for eddy, instead of having dwifslpreproc generate one internally using dwi2mask",
    )
    eddy_slspec = File(
        exists=True,
        argstr="-eddy_slspec %s",
        desc="Provide a file containing slice groupings for eddy's slice-to-volume registration",
    )
    eddyqc_text = Directory(
        exists=False,
        argstr="-eddyqc_text %s",
        desc="Copy the various text-based statistical outputs generated by eddy, and the output of eddy_qc (if installed), into an output directory",
    )
    eddyqc_all = Directory(
        exists=False,
        argstr="-eddyqc_all %s",
        desc="Copy ALL outputs generated by eddy (including images), and the output of eddy_qc (if installed), into an output directory",
    )
    out_grad_mrtrix = File(
        "grad.b",
        argstr="-export_grad_mrtrix %s",
        desc="export new gradient files in mrtrix format",
    )
    out_grad_fsl = traits.Tuple(
        File("grad.bvecs", desc="bvecs"),
        File("grad.bvals", desc="bvals"),
        argstr="-export_grad_fsl %s, %s",
        desc="export gradient files in FSL format",
    )


class DWIPreprocOutputSpec(TraitedSpec):
    out_file = File(argstr="%s", desc="output preprocessed image series")
    out_grad_mrtrix = File(
        "grad.b",
        argstr="%s",
        usedefault=True,
        desc="preprocessed gradient file in mrtrix3 format",
    )
    out_fsl_bvec = File(
        "grad.bvecs",
        argstr="%s",
        usedefault=True,
        desc="exported fsl gradient bvec file",
    )
    out_fsl_bval = File(
        "grad.bvals",
        argstr="%s",
        usedefault=True,
        desc="exported fsl gradient bval file",
    )
    eddyqc_text = File(
        "eddyqc.txt",
        argstr="%s",
        desc="Various text-based statistical outputs generated by eddy, and the output of eddy_qc (if installed), into an output directory",
    )
    eddyqc_all = Directory(
        "eddyqc_all",
        argstr="%s",
        desc="All outputs generated by eddy (including images), and the output of eddy_qc (if installed), into an output directory",
    )


class DWIPreproc(MRTrix3Base):
    """
    Perform diffusion image pre-processing using FSL's eddy tool; including inhomogeneity distortion correction using FSL's topup tool if possible

    For more information, see
    <https://mrtrix.readthedocs.io/en/latest/reference/commands/dwifslpreproc.html>

    Example
    -------

    >>> import nipype.interfaces.mrtrix3 as mrt
    >>> preproc = mrt.DWIPreproc()
    >>> preproc.inputs.in_file = 'dwi.mif'
    >>> preproc.inputs.rpe_options = 'none'
    >>> preproc.inputs.out_file = "preproc.mif"
    >>> preproc.inputs.eddy_options = '--slm=linear --repol'     # linear second level model and replace outliers
    >>> preproc.inputs.out_grad_mrtrix = "grad.b"    # export final gradient table in MRtrix format
    >>> preproc.inputs.ro_time = 0.165240   # 'TotalReadoutTime' in BIDS JSON metadata files
    >>> preproc.inputs.pe_dir = 'j'     # 'PhaseEncodingDirection' in BIDS JSON metadata files
    >>> preproc.cmdline
    'dwifslpreproc dwi.mif preproc.mif -rpe_none -eddy_options "--slm=linear --repol" -export_grad_mrtrix grad.b -pe_dir j -readout_time 0.165240'
    >>> preproc.run()                             # doctest: +SKIP
    """

    _cmd = "dwifslpreproc"
    input_spec = DWIPreprocInputSpec
    output_spec = DWIPreprocOutputSpec

    def _run_interface(self, runtime, correct_return_codes=(0,)):
        """Execute command via subprocess

        Parameters
        ----------
        runtime : passed by the run function

        Returns
        -------
        runtime :
            updated runtime information
            adds stdout, stderr, merged, cmdline, dependencies, command_path

        """
        out_environ = self._get_environ()
        # Initialize runtime Bunch

        try:
            runtime.cmdline = self.cmdline
        except Exception as exc:
            raise RuntimeError(
                "Error raised when interpolating the command line"
            ) from exc

        runtime.stdout = None
        runtime.stderr = None
        runtime.cmdline = self.cmdline
        runtime.environ.update(out_environ)
        runtime.success_codes = correct_return_codes

        # which $cmd
        executable_name = shlex.split(self._cmd_prefix + self.cmd)[0]
        cmd_path = which(executable_name, env=runtime.environ)

        if cmd_path is None:
            raise IOError(
                'No command "%s" found on host %s. Please check that the '
                "corresponding package is installed."
                % (executable_name, runtime.hostname)
            )

        runtime.command_path = cmd_path
        runtime.dependencies = (
            get_dependencies(executable_name, runtime.environ)
            if self._ldd
            else "<skipped>"
        )
        runtime = run_command(
            runtime,
            output=self.terminal_output,
            write_cmdline=self.write_cmdline,
        )
        # manually copy the eddyqc outputs
        if self.inputs.eddyqc_text:
            eddyqc_dir = Path(self.inputs.eddyqc_all)
            eddy_target_dir = Path(self.inputs.out_file).parent
            eddyqc_dir.rename(eddy_target_dir / eddyqc_dir.name)
        return runtime

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["out_file"] = op.abspath(self.inputs.out_file)
        if self.inputs.out_grad_mrtrix:
            outputs["out_grad_mrtrix"] = op.abspath(self.inputs.out_grad_mrtrix)
        if self.inputs.out_grad_fsl:
            outputs["out_fsl_bvec"] = op.abspath(self.inputs.out_grad_fsl[0])
            outputs["out_fsl_bval"] = op.abspath(self.inputs.out_grad_fsl[1])
        if self.inputs.eddyqc_text:
            outputs["eddyqc_text"] = op.abspath(self.inputs.eddyqc_text)
        if self.inputs.eddyqc_all:
            outputs["eddyqc_all"] = op.abspath(self.inputs.eddyqc_all)

        return outputs
