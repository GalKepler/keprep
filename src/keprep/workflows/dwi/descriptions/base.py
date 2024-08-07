DIFFUSION_WORKFLOW_DESCRIPTION_MULTI_SESSIONS = """
**Diffusion data preprocessing**

: For each of the {n_dwi} DWI scans found (across all sessions),
the following preprocessing was performed.

"""


DIFFUSION_WORKFLOW_DESCRIPTION_SINGLE_SESSION = """
**Diffusion data preprocessing**

The following preprocessing procedures were applied to the DWI scan.
"""

DENOISING = """Any images with a b-value less than {b0_threshold} s/mm^2 were treated as a b=0 image.

MP-PCA denoising as implemented in MRtrix3's `dwidenoise` [@dwidenoise1] was applied with a {denoise_window}-voxel window.
"""
