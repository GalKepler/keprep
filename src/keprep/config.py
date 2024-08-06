r"""
A Python module to maintain unique, run-wide *KePrep* settings.

This module implements the memory structures to keep a consistent, singleton config.
Settings are passed across processes via filesystem, and a copy of the settings for
each run and subject is left under
``<output_dir>/sub-<participant_id>/log/<run_unique_id>/keprep.toml``.
Settings are stored using :abbr:`ToML (Tom's Markup Language)`.
The module has a :py:func:`~keprep.config.to_filename` function to allow writing out
the settings to hard disk in *ToML* format, which looks like:
.. literalinclude:: ../keprep/data/tests/config.toml
   :language: toml
   :name: keprep.toml
   :caption: **Example file representation of KePrep settings**.
This config file is used to pass the settings across processes,
using the :py:func:`~keprep.config.load` function.
Configuration sections
----------------------
.. autoclass:: environment
   :members:
.. autoclass:: execution
   :members:
.. autoclass:: workflow
   :members:
.. autoclass:: nipype
   :members:
Usage
-----
A config file is used to pass settings and collect information as the execution
graph is built across processes.
.. code-block:: Python
    from keprep import config
    config_file = config.execution.work_dir / '.keprep.toml'
    config.to_filename(config_file)
    # Call build_workflow(config_file, retval) in a subprocess
    with Manager() as mgr:
        from .workflow import build_workflow
        retval = mgr.dict()
        p = Process(target=build_workflow, args=(str(config_file), retval))
        p.start()
        p.join()
    config.load(config_file)
    # Access configs from any code section as:
    value = config.section.setting
Logging
-------
.. autoclass:: loggers
   :members:
Other responsibilities
----------------------
The :py:mod:`config` is responsible for other conveniency actions.
  * Switching Python's :obj:`multiprocessing` to *forkserver* mode.
  * Set up a filter for warnings as early as possible.
  * Automated I/O magic operations. Some conversions need to happen in the
    store/load processes (e.g., from/to :obj:`~pathlib.Path` \<-\> :obj:`str`,
    :py:class:`~bids.layout.BIDSLayout`, etc.)
"""

# mypy: ignore-errors
import os
from multiprocessing import set_start_method

# Disable NiPype etelemetry always
_disable_et = bool(
    os.getenv("NO_ET") is not None or os.getenv("NIPYPE_NO_ET") is not None
)
os.environ["NIPYPE_NO_ET"] = "1"
os.environ["NO_ET"] = "1"

CONFIG_FILENAME = "keprep.toml"

try:
    set_start_method("forkserver")
except RuntimeError:
    pass  # context has been already set
finally:
    # Defer all custom import for after initializing the forkserver and
    # ignoring the most annoying warnings
    import json
    import logging
    import random
    import sys
    from pathlib import Path
    from time import strftime
    from uuid import uuid4

    from nipype import __version__ as _nipype_ver
    from templateflow import __version__ as _tf_ver

    from keprep import __version__

# Trick to avoid sklearn's FutureWarnings
if not hasattr(sys, "_is_pytest_session"):
    sys._is_pytest_session = False  # type: ignore[attr-defined]
# Disable all warnings in main and children processes only on production versions

logging.addLevelName(25, "IMPORTANT")  # Add a new level between INFO and WARNING
logging.addLevelName(15, "VERBOSE")  # Add a new level between INFO and DEBUG

DEFAULT_MEMORY_MIN_GB = 0.01

# Execution environment
_exec_env = os.name
_docker_ver = None
# special variable set in the container
if os.getenv("IS_DOCKER_8395080871"):
    _exec_env = "singularity"
    _cgroup = Path("/proc/1/cgroup")
    if _cgroup.exists() and "docker" in _cgroup.read_text():
        _docker_ver = os.getenv("DOCKER_VERSION_8395080871")
        _exec_env = "keprep-docker" if _docker_ver else "docker"
    del _cgroup

_fs_license = os.getenv("FS_LICENSE")
if not _fs_license and os.getenv("FREESURFER_HOME"):
    _fs_home = os.getenv("FREESURFER_HOME")
    if _fs_home and (Path(_fs_home) / "license.txt").is_file():
        _fs_license = str(Path(_fs_home) / "license.txt")
    del _fs_home

_templateflow_home = Path(
    os.getenv(
        "TEMPLATEFLOW_HOME",
        os.path.join(
            os.getenv("HOME"), ".cache", "templateflow"  # type: ignore[arg-type]
        ),  # noqa: C0301
    )
)

try:
    from psutil import virtual_memory

    _free_mem_at_start = round(virtual_memory().available / 1024**3, 1)
except Exception:
    _free_mem_at_start = None

_oc_limit = "n/a"
_oc_policy = "n/a"
try:
    # Memory policy may have a large effect on types of errors experienced
    _proc_oc_path = Path("/proc/sys/vm/overcommit_memory")
    if _proc_oc_path.exists():
        _oc_policy = {"0": "heuristic", "1": "always", "2": "never"}.get(
            _proc_oc_path.read_text().strip(), "unknown"
        )
        if _oc_policy != "never":
            _proc_oc_kbytes = Path("/proc/sys/vm/overcommit_kbytes")
            if _proc_oc_kbytes.exists():
                _oc_limit = _proc_oc_kbytes.read_text().strip()
            if (
                _oc_limit in ("0", "n/a")
                and Path("/proc/sys/vm/overcommit_ratio").exists()
            ):
                _oc_limit = "{}%".format(
                    Path("/proc/sys/vm/overcommit_ratio").read_text().strip()
                )
except Exception:
    pass


# Debug modes are names that influence the exposure of internal details to
# the user, either through additional derivatives or increased verbosity
DEBUG_MODES = ""


class _Config:
    """An abstract class forbidding instantiation."""

    _paths: tuple = tuple()

    def __init__(self):
        """Avert instantiation."""
        raise RuntimeError("Configuration type is not instantiable.")

    @classmethod
    def load(cls, settings, init=True, ignore=None):
        """Store settings from a dictionary."""
        ignore = ignore or {}
        for k, v in settings.items():
            if k in ignore or v is None:
                continue
            if k in cls._paths:
                setattr(cls, k, Path(v).absolute())
            elif hasattr(cls, k):
                setattr(cls, k, v)

        if init:
            try:
                cls.init()  # type: ignore[attr-defined]
            except AttributeError:
                pass

    @classmethod
    def get(cls):
        """Return defined settings."""
        from niworkflows.utils.spaces import Reference, SpatialReferences

        out = {}
        for k, v in cls.__dict__.items():
            if k.startswith("_") or v is None:
                continue
            if callable(getattr(cls, k)):
                continue
            if k in cls._paths:
                v = str(v)
            if isinstance(v, SpatialReferences):
                v = " ".join([str(s) for s in v.references]) or None
            if isinstance(v, Reference):
                v = str(v) or None
            out[k] = v
        return out


class environment(_Config):
    """
    Read-only options regarding the platform and environment.

    Crawls runtime descriptive settings (e.g., default FreeSurfer license,
    execution environment, nipype and *KePrep* versions, etc.).
    The ``environment`` section is not loaded in from file,
    only written out when settings are exported.
    This config section is useful when reporting issues,
    and these variables are tracked whenever the user does not
    opt-out using the ``--notrack`` argument.
    """

    cpu_count = os.cpu_count()
    """Number of available CPUs."""
    exec_docker_version = _docker_ver
    """Version of Docker Engine."""
    exec_env = _exec_env
    """A string representing the execution platform."""
    free_mem = _free_mem_at_start
    """Free memory at start."""
    overcommit_policy = _oc_policy
    """Linux's kernel virtual memory overcommit policy."""
    overcommit_limit = _oc_limit
    """Linux's kernel virtual memory overcommit limits."""
    nipype_version = _nipype_ver
    """Nipype's current version."""
    templateflow_version = _tf_ver
    """The TemplateFlow client version installed."""
    version = __version__
    """*KePrep*'s version."""


class nipype(_Config):
    """Nipype settings."""

    crashfile_format = "txt"
    """The file format for crashfiles, either text or pickle."""
    get_linked_libs = False
    """Run NiPype's tool to enlist linked libraries for every interface."""
    memory_gb = None
    """Estimation in GB of the RAM this workflow can allocate at any given time."""
    nprocs = os.cpu_count()
    """Number of processes (compute tasks) that can be run in parallel (multiprocessing only)."""  # noqa: E501
    omp_nthreads = None
    """Number of CPUs a single process can access for multithreaded execution."""
    plugin = "MultiProc"
    """NiPype's execution plugin."""
    plugin_args = {
        "maxtasksperchild": 1,
        "raise_insufficient": False,
    }
    """Settings for NiPype's execution plugin."""
    resource_monitor = False
    """Enable resource monitor."""
    stop_on_first_crash = True
    """Whether the workflow should stop or continue after the first error."""

    @classmethod
    def get_plugin(cls):
        """Format a dictionary for Nipype consumption."""
        out = {
            "plugin": cls.plugin,
            "plugin_args": cls.plugin_args,
        }
        if cls.plugin in ("MultiProc", "LegacyMultiProc"):
            out["plugin_args"]["n_procs"] = int(cls.nprocs)  # type: ignore[index, arg-type]
            if cls.memory_gb:
                out["plugin_args"]["memory_gb"] = float(cls.memory_gb)  # type: ignore[unreachable]
        return out

    @classmethod
    def init(cls):
        """Set NiPype configurations."""
        from nipype import config as ncfg

        # Configure resource_monitor
        if cls.resource_monitor:
            ncfg.update_config(
                {
                    "monitoring": {
                        "enabled": cls.resource_monitor,
                        "sample_frequency": "0.5",
                        "summary_append": True,
                    }
                }
            )
            ncfg.enable_resource_monitor()

        # Nipype config (logs and execution)
        ncfg.update_config(
            {
                "execution": {
                    "crashdump_dir": str(execution.log_dir),
                    "crashfile_format": cls.crashfile_format,
                    "get_linked_libs": cls.get_linked_libs,
                    "stop_on_first_crash": cls.stop_on_first_crash,
                    "check_version": False,  # disable future telemetry
                }
            }
        )

        if cls.omp_nthreads is None:
            cls.omp_nthreads = min(
                cls.nprocs - 1 if cls.nprocs > 1 else os.cpu_count(), 8  # type: ignore[type-var, assignment, operator]
            )


class execution(_Config):
    """Configure run-level settings."""

    anat_derivatives = None
    """A path where anatomical derivatives are found to fast-track *sMRIPrep*."""
    bids_dir = None
    """An existing path to the dataset, which must be BIDS-compliant."""
    bids_database_dir = None
    """Path to the directory containing SQLite database indices for the input BIDS dataset."""
    bids_description_hash = None
    """Checksum (SHA256) of the ``dataset_description.json`` of the BIDS dataset."""
    bids_filters = None
    """A dictionary of BIDS selection filters."""
    reset_database = True
    """Reset the SQLite database."""
    debug: str | list = []
    """Debug mode(s)."""
    fs_license_file = _fs_license
    """An existing file containing a FreeSurfer license."""
    fs_subjects_dir = None
    """FreeSurfer's subjects directory."""
    layout = None
    """A :py:class:`~keprep.bids.layout.QSIPrepLayout` object, see :py:func:`init`."""
    reportlets_dir = None
    """Path to a directory where reportlets will be stored."""
    log_dir = None
    """The path to a directory that contains execution logs."""
    log_level = 25
    """Output verbosity."""
    low_mem = None
    """Utilize uncompressed NIfTIs and other tricks to minimize memory allocation."""
    output_dir = None
    """Folder where derivatives will be stored."""
    run_uuid = f"{strftime('%Y%m%d-%H%M%S')}_{uuid4()}"
    """Unique identifier of this particular run."""
    participant_label: list | None = None
    """List of participant identifiers that are to be preprocessed."""
    work_dir = Path("work").absolute()
    """Path to a working directory where intermediate results will be available."""
    write_graph = False
    """Write out the computational graph corresponding to the planned preprocessing."""
    output_spaces = None
    """List of (non)standard spaces designated (with the ``--output-spaces`` flag of
    the command line) as spatial references for outputs."""
    _layout = None

    _paths = (
        "anat_derivatives",
        "bids_dir",
        "bids_database_dir",
        "fs_license_file",
        "fs_subjects_dir",
        "layout",
        "log_dir",
        "output_dir",
        "work_dir",
    )

    @classmethod
    def init(cls):
        """Create a new BIDS Layout accessible with :attr:`~execution.layout`."""
        if cls.fs_license_file and Path(cls.fs_license_file).is_file():
            os.environ["FS_LICENSE"] = str(cls.fs_license_file)

        if cls._layout is None:
            from bids import BIDSLayout

            _db_path = cls.bids_database_dir or (
                cls.work_dir / cls.run_uuid / "bids_db"
            )
            _db_path.mkdir(exist_ok=True, parents=True)

            # Recommended after PyBIDS 12.1
            cls._layout = BIDSLayout(
                str(cls.bids_dir),
                database_path=_db_path,
                reset_database=cls.reset_database or (cls.bids_database_dir is None),
            )
            cls.bids_database_dir = _db_path
        cls.layout = cls._layout
        if cls.bids_filters:
            if isinstance(cls.bids_filters, str) or isinstance(cls.bids_filters, Path):  # type: ignore[unreachable]
                cls.bids_filters = json.loads(Path(cls.bids_filters).read_text())
            from bids.layout import Query

            # unserialize pybids Query enum values
            for acq, filters in cls.bids_filters.items():
                cls.bids_filters[acq] = {
                    k: (
                        getattr(Query, v[7:-4])
                        if not isinstance(v, Query) and "Query" in v
                        else v
                    )
                    for k, v in filters.items()
                }
        if "all" in cls.debug:
            cls.debug = list(DEBUG_MODES)

        if Path(cls.output_dir).name != "keprep":  # type: ignore[arg-type]
            cls.output_dir = Path(cls.output_dir) / "keprep"  # type: ignore[arg-type]
        cls.output_dir.mkdir(exist_ok=True, parents=True)  # type: ignore[union-attr]
        cls.keprep_dir = Path(cls.output_dir)  # type: ignore[arg-type, attr-defined]
        cls.output_dir = Path(cls.output_dir).parent  # type: ignore[arg-type]
        if cls.participant_label is None:
            cls.participant_label = cls.layout.get_subjects()
        else:
            cls.participant_label = list(cls.participant_label)
        if cls.reportlets_dir is None:
            cls.reportlets_dir = Path(cls.work_dir) / "reportlets"
        cls.reportlets_dir.mkdir(exist_ok=True, parents=True)  # type: ignore[union-attr]


# These variables are not necessary anymore
del _fs_license
del _exec_env
del _nipype_ver
del _templateflow_home
del _tf_ver
del _free_mem_at_start
del _oc_limit
del _oc_policy


class workflow(_Config):
    """Configure the particular execution graph of this workflow."""

    anat_only = False
    """Execute the anatomical preprocessing only."""
    dwi2t1w_method = "epireg"
    """
    Method to use for DWI-to-T1w coregistration. Either "epireg" (default) or "flirt"
    """
    dwi2t1w_dof = 6
    """Degrees of freedom of the DWI-to-T1w registration steps."""
    dwi2t1w_init = "register"
    """Whether to use standard coregistration ('register') or to initialize coregistration from the
    BOLD image-header ('header')."""
    cifti_output = None
    """Generate HCP Grayordinates, accepts either ``'91k'`` (default) or ``'170k'``."""
    do_reconall = False
    """Whether to perform FreeSurfer's recon-all."""
    longitudinal = False
    """Run FreeSurfer ``recon-all`` with the ``-logitudinal`` flag."""
    skull_strip_fixed_seed = False
    """Fix a seed for skull-stripping."""
    skull_strip_template = "OASIS30ANTs"
    """Change default brain extraction template."""
    spaces = None
    """Keeps the :py:class:`~niworkflows.utils.spaces.SpatialReferences`
    instance keeping standard and nonstandard spaces."""
    hires = None
    """Run FreeSurfer ``recon-all`` with the ``-hires`` flag."""
    skull_strip_t1w = "force"
    """Skip brain extraction of the T1w image (default is ``force``, meaning that
    *KePrep* will run brain extraction of the T1w)."""
    denoise_method = "dwidenoise"
    """Image-based denoising method. Either "dwidenoise" (MRtrix), "patch2self" (DIPY)
    or "none"."""
    dwi_denoise_window = "auto"
    """Window size in voxels for image-based denoising, integer or "auto"."""
    dwi_no_biascorr = False
    """DEPRECATED: see --b1-biascorrect-stage."""
    eddy_config = "--fwhm=0 --flm='quadratic' --repol"
    """Configuration for running Eddy."""
    hmc_model = "eddy"
    """Model used to generate target images for hmc."""
    b0_threshold = 100
    """any value in the .bval file less than this will be considered a b=0 image."""


class loggers:
    """Keep loggers easily accessible (see :py:func:`init`)."""

    _fmt = "%(asctime)s,%(msecs)d %(name)-2s " "%(levelname)-2s:\n\t %(message)s"
    _datefmt = "%y%m%d-%H:%M:%S"

    default = logging.getLogger()
    """The root logger."""
    cli = logging.getLogger("cli")
    """Command-line interface logging."""
    workflow = logging.getLogger("nipype.workflow")
    """NiPype's workflow logger."""
    interface = logging.getLogger("nipype.interface")
    """NiPype's interface logger."""
    utils = logging.getLogger("nipype.utils")
    """NiPype's utils logger."""

    @classmethod
    def init(cls):
        """
        Set the log level, initialize all loggers into :py:class:`loggers`.

            * Add new logger levels (25: IMPORTANT, and 15: VERBOSE).
            * Add a new sub-logger (``cli``).
            * Logger configuration.
        """
        from nipype import config as ncfg

        _handler = logging.StreamHandler(stream=sys.stdout)
        _handler.setFormatter(logging.Formatter(fmt=cls._fmt, datefmt=cls._datefmt))
        cls.cli.addHandler(_handler)
        cls.default.setLevel(execution.log_level)
        cls.cli.setLevel(execution.log_level)
        cls.interface.setLevel(execution.log_level)
        cls.workflow.setLevel(execution.log_level)
        cls.utils.setLevel(execution.log_level)
        ncfg.update_config(
            {
                "logging": {
                    "log_directory": str(execution.log_dir),
                    "log_to_file": True,
                }
            }
        )


class seeds(_Config):
    """Initialize the PRNG and track random seed assignments."""

    _random_seed = None
    master = None
    """Master random seed to initialize the Pseudorandom Number Generator (PRNG)"""
    ants = None
    """Seed used for antsRegistration, antsAI, antsMotionCorr"""
    numpy = None
    """Seed used by NumPy"""

    @classmethod
    def init(cls):
        if cls._random_seed is not None:
            cls.master = cls._random_seed
        if cls.master is None:
            cls.master = random.randint(1, 65536)
        random.seed(cls.master)  # initialize the PRNG
        # functions to set program specific seeds
        cls.ants = _set_ants_seed()
        cls.numpy = _set_numpy_seed()


def _set_ants_seed():
    """Fix random seed for antsRegistration, antsAI, antsMotionCorr."""
    val = random.randint(1, 65536)
    os.environ["ANTS_RANDOM_SEED"] = str(val)
    return val


def _set_numpy_seed():
    """Numpy's random seed is independent from Python's `random` module."""
    import numpy as np

    val = random.randint(1, 65536)
    np.random.seed(val)
    return val


def from_dict(settings, init=True, ignore=None):
    """
    Read settings from a flat dictionary.

    Arguments
    ---------
    setting : dict
        Settings to apply to any configuration
    init : `bool` or :py:class:`~collections.abc.Container`
        Initialize all, none, or a subset of configurations.
    ignore : :py:class:`~collections.abc.Container`
        Collection of keys in ``setting`` to ignore
    """

    # Accept global True/False or container of configs to initialize
    def initialize(x):
        return init if init in (True, False) else x in init

    nipype.load(settings, init=initialize("nipype"), ignore=ignore)
    execution.load(settings, init=initialize("execution"), ignore=ignore)
    workflow.load(settings, init=initialize("workflow"), ignore=ignore)
    seeds.load(settings, init=initialize("seeds"), ignore=ignore)

    loggers.init()
    init_spaces()


def load(filename, skip=None, init=True):
    """
    Load settings from file.

    Arguments
    ---------
    filename : :py:class:`os.PathLike`
        TOML file containing fMRIPrep configuration.
    skip : dict or None
        Sets of values to ignore during load, keyed by section name
    init : `bool` or :py:class:`~collections.abc.Container`
        Initialize all, none, or a subset of configurations.
    """
    from toml import loads  # type: ignore

    skip = skip or {}

    # Accept global True/False or container of configs to initialize
    def initialize(x):
        return init if init in (True, False) else x in init

    filename = Path(filename)
    settings = loads(filename.read_text())
    for sectionname, configs in settings.items():
        if sectionname != "environment":
            section = getattr(sys.modules[__name__], sectionname)
            ignore = skip.get(sectionname)
            section.load(configs, ignore=ignore, init=initialize(sectionname))
    init_spaces()


def get(flat=False):
    """Get config as a dict."""
    settings = {
        "environment": environment.get(),
        "execution": execution.get(),
        "workflow": workflow.get(),
        "nipype": nipype.get(),
        "seeds": seeds.get(),
    }
    if not flat:
        return settings

    return {
        ".".join((section, k)): v
        for section, configs in settings.items()
        for k, v in configs.items()
    }


def dumps():
    """Format config into toml."""
    from toml import dumps

    return dumps(get())


def to_filename(filename):
    """Write settings to file."""
    filename = Path(filename)
    filename.write_text(dumps())


def init_spaces(checkpoint=True):
    """Initialize the :attr:`~workflow.spaces` setting."""
    from niworkflows.utils.spaces import Reference, SpatialReferences

    spaces = execution.output_spaces or SpatialReferences()
    if not isinstance(spaces, SpatialReferences):
        spaces = SpatialReferences(
            [ref for s in spaces.split(" ") for ref in Reference.from_string(s)]
        )

    if checkpoint and not spaces.is_cached():
        spaces.checkpoint()

    # Add the default standard space if not already present (required by several sub-workflows)
    if "MNI152NLin2009cAsym" not in spaces.get_spaces(nonstandard=False, dim=(3,)):
        spaces.add(Reference("MNI152NLin2009cAsym", {}))

    # Ensure user-defined spatial references for outputs are correctly parsed.
    # Certain options require normalization to a space not explicitly defined by users.
    # These spaces will not be included in the final outputs.
    cifti_output = workflow.cifti_output
    if cifti_output:
        # CIFTI grayordinates to corresponding FSL-MNI resolutions.
        vol_res = "2" if cifti_output == "91k" else "1"
        spaces.add(Reference("MNI152NLin6Asym", {"res": vol_res}))

    # Make the SpatialReferences object available
    workflow.spaces = spaces
