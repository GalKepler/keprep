import os.path as op

from nipype.interfaces.base import File, TraitedSpec, traits
from nipype.interfaces.mrtrix3.base import MRTrix3Base, MRTrix3BaseInputSpec


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
