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


def plot_eddy_qc(
    eddy_qc: str,
    out_file: str,
    dpi: int = 300,
):
    """
    Plot the eddy QC.

    Parameters
    ----------
    eddy_qc : str
        path to the eddy qc file
    out_file : str
        path to the output file
    title : str, optional
        title of the plot (default: "Eddy QC")
    dpi : int, optional
        dpi of the plot (default: 300)
    """
    import os
    from pathlib import Path

    import matplotlib.pyplot as plt
    import numpy as np
    import pandas as pd
    import seaborn as sns

    sns.set_style("whitegrid")
    sns.set_context("paper", font_scale=1.5)
    sns.set_palette("bright")

    eddy_qc = Path(eddy_qc)  # type: ignore[assignment]
    params = np.genfromtxt(eddy_qc / "eddy_parameters", dtype=float)  # type: ignore[type-var, operator] # noqa: E501
    motion = np.genfromtxt(eddy_qc / "eddy_movement_rms", dtype=float)  # type: ignore[type-var, operator] # noqa: E501

    df_params = pd.DataFrame(
        {
            "x": params[:, 0],
            "y": params[:, 1],
            "z": params[:, 2],
        }
    )
    df_params["type"] = "absolute"
    df_params["volume"] = np.arange(df_params.shape[0])
    # add relative motion from columns 3 to 5 as new lines
    df_params = pd.concat(
        [
            df_params,
            pd.DataFrame(
                {
                    "x": params[:, 3],
                    "y": params[:, 4],
                    "z": params[:, 5],
                    "type": "relative",
                    "volume": np.arange(df_params.shape[0]),
                }
            ),
        ]
    )
    df_params = df_params.melt(
        id_vars=["volume", "type"],
        value_vars=["x", "y", "z"],
        var_name="direction",
        value_name="displacement",
    )

    fig_props = {
        "absolute": {
            "title": "Eddy estimated translations (mm)",
            "ylabel": "Translation [mm]",
        },
        "relative": {
            "title": "Eddy estimated rotations (deg)",
            "ylabel": "Rotation [deg]",
        },
    }

    fig, axes = plt.subplots(3, 1, figsize=(10, 15))
    for i, movement_type in enumerate(["absolute", "relative"]):
        _ = sns.lineplot(
            data=df_params[df_params["type"] == movement_type],
            x="volume",
            y="displacement",
            hue="direction",
            ax=axes[i],  # type: ignore[index]
            palette={"x": "r", "y": "g", "z": "b"},
            linewidth=2,
        )
        axes[i].set_xlabel("Volume")  # type: ignore[index]
        axes[i].set_ylabel(fig_props[movement_type]["ylabel"])  # type: ignore[index]
        axes[i].set_title(  # type: ignore[index]
            fig_props[movement_type]["title"], fontweight="bold", fontsize=20
        )

    df_motion = pd.DataFrame(motion, columns=["Absolute", "Relative"])
    df_motion["Volume"] = np.arange(df_motion.shape[0])
    df_motion = df_motion.melt(
        id_vars=["Volume"], var_name="Type", value_name="Displacement"
    )
    _ = sns.lineplot(
        data=df_motion,
        x="Volume",
        y="Displacement",
        hue="Type",
        ax=axes[2],  # type: ignore[index]
        linewidth=2,
        palette={"Absolute": "r", "Relative": "b"},
    )
    axes[2].set_xlabel("Volume")  # type: ignore[index]
    axes[2].set_ylabel("Displacement [mm]")  # type: ignore[index]
    axes[2].set_title("Estimated mean displacement", fontweight="bold", fontsize=20)  # type: ignore[index] # noqa: E501
    axes[2].legend(loc="best", frameon=True, framealpha=0.5)  # type: ignore[index]
    axes[2].set_ylim(0, 0.5 + np.max(df_motion["Displacement"]))  # type: ignore[index]
    plt.tight_layout()

    # save the plot with transparent background
    out_file = os.getcwd() + "/" + out_file
    plt.savefig(out_file, dpi=dpi, bbox_inches="tight", transparent=True)
    plt.close()

    return out_file
