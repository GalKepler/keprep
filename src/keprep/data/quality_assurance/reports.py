# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
#
# Copyright The NiPreps Developers <nipreps@gmail.com>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# We support and encourage derived works from this project, please read
# about our expectations at
#
#     https://www.nipreps.org/community/licensing/
#
from pathlib import Path

from nipype.pipeline import engine as pe
from nireports.assembler.report import Report

from keprep import config, data


def build_boilerplate(config_file: dict | str | Path, workflow: pe.Workflow):
    """Write boilerplate in an isolated process."""
    from keprep import config

    if isinstance(config_file, str) or isinstance(config_file, Path):
        config.load(config_file)
    elif isinstance(config_file, dict):
        config.from_dict(config_file)
    logs_path = config.execution.keprep_dir / "logs"  # type: ignore[attr-defined]
    logs_path.mkdir(parents=True, exist_ok=True)
    boilerplate = workflow.visit_desc()
    citation_files = {
        ext: logs_path / f"CITATION.{ext}" for ext in ("bib", "tex", "md", "html")
    }

    if boilerplate:
        # To please git-annex users and also to guarantee consistency
        # among different renderings of the same file, first remove any
        # existing one
        for citation_file in citation_files.values():
            try:
                citation_file.unlink()
            except FileNotFoundError:
                pass

    citation_files["md"].write_text(boilerplate)

    if citation_files["md"].exists():
        from subprocess import CalledProcessError, TimeoutExpired, check_call

        from keprep import data

        bib_text = data.load.readable("boilerplate.bib").read_text()
        citation_files["bib"].write_text(
            bib_text.replace("KePrep <version>", f"KePrep {config.environment.version}")
        )

        # Generate HTML file resolving citations
        cmd = [
            "pandoc",
            "-s",
            "--bibliography",
            str(citation_files["bib"]),
            "--citeproc",
            "--metadata",
            'pagetitle="fMRIPrep citation boilerplate"',
            str(citation_files["md"]),
            "-o",
            str(citation_files["html"]),
        ]

        config.loggers.cli.info(
            "Generating an HTML version of the citation boilerplate..."
        )
        try:
            check_call(cmd, timeout=10)
        except (FileNotFoundError, CalledProcessError, TimeoutExpired):
            config.loggers.cli.warning(
                "Could not generate CITATION.html file:\n%s", " ".join(cmd)
            )

        # Generate LaTex file resolving citations
        cmd = [
            "pandoc",
            "-s",
            "--bibliography",
            str(citation_files["bib"]),
            "--natbib",
            str(citation_files["md"]),
            "-o",
            str(citation_files["tex"]),
        ]
        config.loggers.cli.info(
            "Generating a LaTeX version of the citation boilerplate..."
        )
        try:
            check_call(cmd, timeout=10)
        except (FileNotFoundError, CalledProcessError, TimeoutExpired):
            config.loggers.cli.warning(
                "Could not generate CITATION.tex file:\n%s", " ".join(cmd)
            )


def run_reports(
    output_dir,
    subject_label,
    run_uuid,
    bootstrap_file=None,
    out_filename="report.html",
    reportlets_dir=None,
    errorname="report.err",
    **entities,
):
    """
    Run the reports.
    """
    robj = Report(
        output_dir,
        run_uuid,
        bootstrap_file=bootstrap_file,
        out_filename=out_filename,
        reportlets_dir=reportlets_dir,
        plugins=None,
        plugin_meta=None,
        metadata=None,
        **entities,
    )

    # Count nbr of subject for which report generation failed
    try:
        robj.generate_report()
    except:  # noqa: E722
        import sys
        import traceback

        # Store the list of subjects for which report generation failed
        traceback.print_exception(
            *sys.exc_info(), file=str(Path(output_dir) / "logs" / errorname)
        )
        return subject_label

    return None


def generate_reports(
    subject_list,
    output_dir,
    run_uuid,
    session_list=None,
    bootstrap_file=None,
    work_dir=None,
):
    """Generate reports for a list of subjects."""
    reportlets_dir = None
    if work_dir is not None:
        reportlets_dir = Path(work_dir) / "reportlets"

    if isinstance(subject_list, str):
        subject_list = [subject_list]

    errors = []
    for subject_label in subject_list:
        # The number of sessions is intentionally not based on session_list but
        # on the total number of sessions, because I want the final derivatives
        # folder to be the same whether sessions were run one at a time or all-together.
        n_ses = len(config.execution.layout.get_sessions(subject=subject_label))
        html_report = "report.html"

        bootstrap_file = data.load("quality_assurance/templates/reports-spec.yml")
        html_report = "report.html"

        report_error = run_reports(
            output_dir,
            subject_label,
            run_uuid,
            bootstrap_file=bootstrap_file,
            out_filename=html_report,
            reportlets_dir=reportlets_dir,
            errorname=f"report-{run_uuid}-{subject_label}.err",
            subject=subject_label,
        )
        # If the report generation failed, append the subject label for which it failed
        if report_error is not None:
            errors.append(report_error)

        if n_ses > config.execution.aggr_ses_reports:
            # Beyond a certain number of sessions per subject,
            # we separate the functional reports per session
            if session_list is None:
                all_filters = config.execution.bids_filters or {}
                filters = all_filters.get("bold", {})
                session_list = config.execution.layout.get_sessions(
                    subject=subject_label, **filters
                )

            # Drop ses- prefixes
            session_list = [
                ses[4:] if ses.startswith("ses-") else ses for ses in session_list
            ]

            for session_label in session_list:
                bootstrap_file = data.load("reports-spec-func.yml")
                html_report = (
                    f'sub-{subject_label.lstrip("sub-")}_ses-{session_label}_func.html'
                )

                report_error = run_reports(
                    output_dir,
                    subject_label,
                    run_uuid,
                    bootstrap_file=bootstrap_file,
                    out_filename=html_report,
                    reportlets_dir=reportlets_dir,
                    errorname=f"report-{run_uuid}-{subject_label}-func.err",
                    subject=subject_label,
                    session=session_label,
                )
                # If the report generation failed,
                # append the subject label for which it failed
                if report_error is not None:
                    errors.append(report_error)

    return errors
