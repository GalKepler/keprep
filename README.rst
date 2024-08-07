============================================================================
KePrep: PreProcessing Strauss Neuroplasticity Brain Bank dMRI data
============================================================================



========
Overview
========
.. list-table::
    :stub-columns: 1

    * - docs
      - |docs|
    * - tests, CI & coverage
      - |github-actions| |circleci| |codecov| |codacy|
    * - codeclimate
      - |codeclimate-maintainability| |codeclimate-testcoverage|
    * - version
      - |pypi| |python|
    * - styling
      - |black| |isort| |flake8| |pre-commit|
    * - license
      - |license|

.. |docs| image:: https://readthedocs.org/projects/keprep/badge/?version=latest
    :target: https://keprep.readthedocs.io/en/latest/?version=latest
    :alt: Documentation Status

.. |github-actions| image:: https://github.com/GalKepler/keprep/actions/workflows/github-actions.yml/badge.svg
    :alt: GitHub Actions Build Status
    :target: https://github.com/GalKepler/keprep/actions

.. |circleci| image:: https://dl.circleci.com/status-badge/img/circleci/J6A3JWLZsHZMCMZ1aCKdXb/AVFefVDaX15sp62PZ8MpA9/tree/main.svg?style=svg
    :alt: CircleCI Build Status
    :target: https://dl.circleci.com/status-badge/redirect/circleci/J6A3JWLZsHZMCMZ1aCKdXb/AVFefVDaX15sp62PZ8MpA9/tree/main

.. |codecov| image:: https://codecov.io/github/GalKepler/keprep/graph/badge.svg?token=LO5CH471O4
    :alt: Coverage Status
    :target: https://app.codecov.io/github/GalKepler/keprep

.. |codacy| image:: https://app.codacy.com/project/badge/Grade/7fe5b4cb103d4100bf00603c913b9ac1
    :target: https://app.codacy.com/gh/GalKepler/keprep/dashboard?utm_source=gh&utm_medium=referral&utm_content=&utm_campaign=Badge_grade
    :alt: Code Quality

.. |codeclimate-maintainability| image:: https://api.codeclimate.com/v1/badges/dc78868ecc19deb5fb5b/maintainability
    :target: https://codeclimate.com/github/GalKepler/keprep/maintainability
    :alt: Maintainability

.. |codeclimate-testcoverage| image:: https://api.codeclimate.com/v1/badges/dc78868ecc19deb5fb5b/test_coverage
    :target: https://codeclimate.com/github/GalKepler/keprep/test_coverage
    :alt: Test Coverage

.. |pypi| image:: https://img.shields.io/pypi/v/keprep.svg
        :target: https://pypi.python.org/pypi/keprep

.. |python| image:: https://img.shields.io/pypi/pyversions/keprep
        :target: https://www.python.org

.. |license| image:: https://img.shields.io/github/license/GalKepler/keprep.svg
        :target: https://opensource.org/license/mit
        :alt: License

.. |black| image:: https://img.shields.io/badge/formatter-black-000000.svg
      :target: https://github.com/psf/black

.. |isort| image:: https://img.shields.io/badge/imports-isort-%231674b1.svg
        :target: https://pycqa.github.io/isort/

.. |flake8| image:: https://img.shields.io/badge/style-flake8-000000.svg
        :target: https://flake8.pycqa.org/en/latest/

.. |pre-commit| image:: https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white
        :target: https://github.com/pre-commit/pre-commit



* Free software: MIT license
* Documentation: https://keprep.readthedocs.io.


About
------

KePrep is a diffusion magnetic resonance imaging (dMRI) preprocessing pipeline designed to provide a reproducible, user-friendly, and easily accessible interface for dMRI data associated with the Strauss Neuroplasticity Brain Bank (SNBB).

.. note::

  The *KePrep* pipeline uses much of the code from fMRIPrep_ (Esteban et al., 2019) and QSIPrep_ (Cieslak et al., 2021) and is built on top of Nipype_ (Gorgolewski et al., 2011).
  It is crucial to note that the similarities in the code **do not imply that the authors of fMRIPrep, QSIPrep, or Nipype endorse KePrep or its pipeline**.
  These similarities are aimed at providing a consistent format and code for contributing to the pipeline.

dMRI data requires a series of preprocessing steps to be performed before it can be used in further analysis.
Although researchers often apply different preprocessing steps using various tools, there is a general consensus on the most common steps.
Therefore, *KePrep* aims to provide a standardized pipeline, allowing researchers to access the dMRI data at different stages of preprocessing.

This pipeline includes the following steps:

1. Denoising
2. Motion and Eddy Current Correction
3. Brain Extraction
4. Bias Field Correction
5. Tractography
6. Coregistration to subject's anatomical image

While being tailored to the SNBB, *KePrep* is designed to be easily adaptable to other dMRI datasets.

More information and documentation can be found at https://keprep.readthedocs.io.

Credits
-------

This package was created with Cookiecutter_ and the `audreyr/cookiecutter-pypackage`_ project template.

.. _Cookiecutter: https://github.com/audreyr/cookiecutter
.. _`audreyr/cookiecutter-pypackage`: https://github.com/audreyr/cookiecutter-pypackage
.. _Nipype: https://nipype.readthedocs.io/en/latest/
.. _fMRIprep: https://fmriprep.org/en/stable/
.. _qsiprep: https://qsiprep.readthedocs.io/en/latest/
