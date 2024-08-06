COREG_EPIREG = """
Once previously described confounds were removed,
a reference mean b=0 image was estimated from the preprocessed DWI series
to use for co-registration purposes:
EPI-to-T1w co-registration was performed using Boundary-Based Registration technique,
as implemented in FSL’s `epi_reg` [@flirt].
While the resulting transformation matrix was not applied to the DWI series (which was kept in its original space),
it was inversed and the two matrices are provided for further applications.
"""

COREG_FLIRT = """
Once previously described confounds were removed,
a reference mean b=0 image was estimated from the preprocessed DWI series
to use for co-registration purposes:
EPI-to-T1w co-registration was performed using FSL`s `FLIRT` [@flirt], configured with
{dof} Degrees of Freedom (DOF).
While the resulting transformation matrix was not applied to the DWI series (which was kept in its original space),
it was inversed and the two matrices are provided for further applications.
"""
