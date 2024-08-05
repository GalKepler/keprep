def read_field_from_json(json_file, field):
    """Read a field from a JSON file."""
    import json

    with open(json_file, "r") as f:
        data = json.load(f)
    return data[field]


def calculate_denoise_window(dwi_file: str) -> int:
    """
    select the smallest isotropic patch size that exceeds the number of
    DW images in the input data, e.g., 5x5x5 for data with <= 125 DWI volumes,
    7x7x7 for data with <= 343 DWI volumes, etc. Must be an odd number.

    Parameters
    ----------
    dwi_file : str
        path to dwi file

    Returns
    -------
    int
        window size for dwidenoise
    """
    import nibabel as nib
    import numpy as np

    img = nib.load(dwi_file)
    n_volumes = img.shape[-1]  # type: ignore[attr-defined]
    window_size = int(np.ceil(n_volumes ** (1 / 3)))
    if window_size % 2 == 0:
        window_size += 1
    return window_size
