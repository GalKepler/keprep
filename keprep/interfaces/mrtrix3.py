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


class MRConvert(MRTrix3Base):
    """
    Perform conversion between different file types and optionally extract a
    subset of the input image

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
