=====
Usage
=====

The KePrep preprocessing workflow takes as input a BIDS_-appropriate dataset.
Other than the BIDS dataset, the user can specify a variety of options to customize the preprocessing workflow.

Being primarily a python package, the way to use the pipeline is to populate the `keprep.config` module with the desired options before running the pipeline itself.

There are two main ways to customize the configuration of the pipeline:

1. By modifying the `keprep.config` module directly.::

    from keprep import config
    from keprep.workflows


.. _BIDS: https://bids.neuroimaging.io
