"""Write a small synthetic report: python examples/report.py artifacts/example-report.html."""

import argparse
from pathlib import Path

from gramlab.reports import Finding, Report, write_report

parser = argparse.ArgumentParser(description="Write an original, synthetic GramLab report example.")
parser.add_argument("output", type=Path)
arguments = parser.parse_args()
report = Report(
    run_id="documentation-example",
    title="A report from your own scenario",
    mode="simulation-only",
    outcome="incomplete",
    seed=7,
    profile={"Source": "Original documentation fixture"},
    summary="Replace these original sample records with your scenario's actual evidence.",
    evidence={"Example message": {"chat_id": 1, "text": "سلام hello"}},
    findings=[
        Finding(
            stage="proposed",
            title="Attach real assertions and observations",
            detail="This example writes a report; it does not execute or validate a scenario.",
        )
    ],
    limitations=["Documentation example only; no bot or Android client ran."],
)
print(write_report(arguments.output, report))
