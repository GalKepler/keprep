ANAT_DERIVATIVES_FAILED = """
Attempted to access pre-existing anatomical derivatives at \
<{anat_derivatives}>, however not all expectations of KePrep \
were met (for participant <{subject_id}>, spaces <{spaces}>, \
reconall <{run_reconall}>).
"""

BASE_WORKFLOW_DESCRIPTION = """
Results included in this manuscript come from preprocessing
performed using *KePrep* {keprep_ver}
which is based on *Nipype* {nipype_ver}
(@nipype1; @nipype2; RRID:SCR_002502).
"""

BASE_POSTDESC = """
Many internal operations of *fMRIPrep* use
*Nilearn* {nilearn_ver} [@nilearn, RRID:SCR_001362],
mostly within the functional processing workflow.
For more details of the pipeline, see [the section corresponding
to workflows in *fMRIPrep*'s documentation]\
(https://fmriprep.readthedocs.io/en/latest/workflows.html \
"FMRIPrep's documentation").


### Copyright Waiver

The above boilerplate text was automatically generated by fMRIPrep
with the express intention that users should copy and paste this
text into their manuscripts *unchanged*.
It is released under the [CC0]\
(https://creativecommons.org/publicdomain/zero/1.0/) license.

### References

"""

DIFFUSION_WORKFLOW_DESCRIPTION = """
Diffusion data preprocessing

: For each of the {n_dwi} DWI scans found per subject
 (across all sessions), the following preprocessing was
    performed.
"""  # TODO: add more details
