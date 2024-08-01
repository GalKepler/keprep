=====
Usage
=====

The KePrep preprocessing workflow takes as input a BIDS_-appropriate dataset.
Other than the BIDS dataset, the user can specify a variety of options to customize the preprocessing workflow.

Being primarily a python package, the way to use the pipeline is to populate the `keprep.config` module with the desired options before running the pipeline itself.

There are two main ways to customize the configuration of the pipeline:

1. By modifying the `keprep.config` module directly.::

    from keprep import config
    config.execution.bids_dir = '/path/to/bids/dataset' # path to the BIDS dataset
    config.execution.output_dir = '/path/to/output/directory' # path to the output directory
    config.execution.participant_label = ['01', '02', '03'] # list of participant labels to process

2. By passing a dictionary of options to the `from_dict` method.::

    from keprep import config

    inputs = {
        "bids_dir": "/path/to/bids/dataset", # path to the BIDS dataset
        "output_dir": "/path/to/output/directory", # path to the output directory
        "participant_label": ["01", "02", "03"] # list of participant labels to process
    }

    config.from_dict(inputs)

Configuration Options
----------------------

Execution Settings
------------------

(accessible through `config.execution`)

* **bids_dir**: Path to the BIDS dataset.
* **output_dir**: Path to the output directory.
* **participant_label**: List of participant identifiers to be preprocessed.
* **anat_derivatives**: Path where anatomical derivatives are found.
* **bids_database_dir**: Directory containing SQLite database indices for the input BIDS dataset.
* **reset_database**: Reset the SQLite database (default: True).
* **fs_license_file**: Path to the FreeSurfer license file.
* **fs_subjects_dir**: FreeSurfer's subjects directory.
* **log_dir**: Path to the directory containing execution logs.
* **log_level**: Output verbosity (default: 25).
* **work_dir**: Path to the working directory where intermediate results will be available.

Nipype Settings
----------------

(accessible through `config.nipype`)

* **nprocs**: Number of processes (compute tasks) that can be run in parallel (multiprocessing only).
* **omp_nthreads**: Number of CPUs a single process can access for multithreaded execution.
* **stop_on_first_crash**: Whether the workflow should stop or continue after the first error (default: True).

Workflow Settings
-----------------

(accessible through `config.workflow`)

* **anat_only**: Execute the anatomical preprocessing only (default: False).
* **dwi2t1w_dof**: Degrees of freedom of the DWI-to-T1w registration steps (default: 6).
* **dwi2t1w_init**: Initialization method for DWI-to-T1w coregistration (default: register).
* **cifti_output**: Generate HCP Grayordinates (accepts 91k or 170k).
* **do_reconall**: Whether to perform FreeSurfer's recon-all (default: False).
* **longitudinal**: Run FreeSurfer recon-all with the -logitudinal flag (default: False).
* **skull_strip_fixed_seed**: Fix a seed for skull-stripping (default: False).
* **skull_strip_template**: Change default brain extraction template (default: OASIS30ANTs).
* **hires**: Run FreeSurfer recon-all with the -hires flag.
* **skull_strip_t1w**: Skip brain extraction of the T1w image (default: force).


.. _BIDS: https://bids.neuroimaging.io
