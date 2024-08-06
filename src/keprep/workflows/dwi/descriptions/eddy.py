RPE_DESCRIPTION = """
Data was collected with reversed phase-encoded directions,
resulting in pairs of images with distortions going in opposite directions.
"""

RPE_DWIFSLPREPROC = """Here, the mean b=0 reference image with reversed phase encoding directions was
used along with a corresponding mean b=0 image extracted from the DWI scans.
The susceptibility-induced off-resonance field was estimated based on this pair
using a method similar to that described in [@topup], as implemented in FSL’s [@fsl, RRID:SCR_002823] `topup` [@topup].
The fieldmaps were ultimately incorporated into the Eddy current and head motion correction conducted using FSL’s `eddy` [@anderssoneddy],
configured with a no q-space smoothing factor (FWHM = 0), a total of 5 iterations, and 1000 voxels used to estimate hyperparameters.
A quadratic first level model was used to characterize Eddy current-related spatial distortion.
Outlier slices were defined as such whose average intensity is at least 4 standard deviations lower than expected intensity,
where the expectation is given by a Gaussian Process prediction.
Slices that were deemed as outliers were replaced with predictions made by the Gaussian Process [@eddyrepol].
Quality control metrices were estimated for this process using eddy QC tools as implemented in `eddy_quad` [@eddyqc].
"""
