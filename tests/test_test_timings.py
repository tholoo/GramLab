"""Behavioral checks for the retained pytest timing command."""

import json
import subprocess
from pathlib import Path

import pytest

TOOL = Path(__file__).resolve().parents[1] / "tools/test-timings"


def run_tool(*arguments: Path | str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603
        [str(TOOL), *(str(argument) for argument in arguments)],
        text=True,
        capture_output=True,
    )


def test_compares_independently_specified_cases_and_preserves_suite_timing(
    tmp_path: Path,
) -> None:
    baseline = tmp_path / "baseline.xml"
    baseline.write_text(
        """<testsuites name="pytest tests"><testsuite name="pytest" tests="3" time="6.5">
        <testcase classname="tests.test_sample" name="alpha" time="2" />
        <testcase classname="tests.test_sample" name="beta" time="3" />
        <testcase classname="tests.test_sample" name="removed" time="1"><skipped /></testcase>
        </testsuite></testsuites>"""
    )
    current = tmp_path / "current.xml"
    current.write_text(
        """<testsuites name="pytest tests"><testsuite name="pytest" tests="3" time="20">
        <testcase classname="tests.test_sample" name="alpha" time="5"><failure /></testcase>
        <testcase classname="tests.test_sample" name="beta" time="1" />
        <testcase classname="tests.test_sample" name="added" time="7"><skipped /></testcase>
        </testsuite></testsuites>"""
    )

    result = run_tool(current, "--baseline", baseline, "--limit", "3")

    assert result.returncode == 0, result.stderr
    observed = json.loads(result.stdout)
    assert observed["current"]["suites"] == [
        {
            "attributes": {"name": "pytest", "tests": "3", "time": "20"},
            "case_count": 3,
            "time_seconds": 20.0,
        }
    ]
    assert observed["current"]["case_duration_sum_seconds"] == 13.0
    assert [(case["id"], case["outcome"]) for case in observed["current"]["slowest"]] == [
        ("tests.test_sample::added", "skipped"),
        ("tests.test_sample::alpha", "failure"),
        ("tests.test_sample::beta", "passed"),
    ]
    comparison = observed["comparison"]
    counts = (
        comparison["matched_count"],
        comparison["added_count"],
        comparison["removed_count"],
    )
    assert counts == (2, 1, 1)
    changes = [(change["id"], change["delta_seconds"]) for change in comparison["duration_changes"]]
    assert changes == [
        ("tests.test_sample::alpha", 3.0),
        ("tests.test_sample::beta", -2.0),
    ]
    assert comparison["added"][0]["id"] == "tests.test_sample::added"
    assert comparison["removed"][0]["id"] == "tests.test_sample::removed"


def test_accepts_a_testsuite_root_and_bounds_case_lists(tmp_path: Path) -> None:
    report = tmp_path / "report.xml"
    report.write_text(
        """<testsuite name="pytest">
        <testcase classname="tests.test_sample" name="quick" time="0.25" />
        <testcase classname="tests.test_sample" name="slow" time="1.25"><error /></testcase>
        </testsuite>"""
    )

    result = run_tool(report, "--limit", "1")

    assert result.returncode == 0, result.stderr
    observed = json.loads(result.stdout)
    assert observed["current"]["case_count"] == 2
    assert observed["current"]["suites"][0]["time_seconds"] is None
    assert [(case["name"], case["outcome"]) for case in observed["current"]["slowest"]] == [
        ("slow", "error")
    ]


@pytest.mark.parametrize(
    ("xml", "message"),
    [
        ("<testsuite>", "cannot parse"),
        ("<report />", "unsupported root element"),
        (
            '<testsuite><testcase classname="tests.x" name="missing" /></testsuite>',
            "missing required time attribute",
        ),
        (
            '<testsuite><testcase classname="tests.x" name="negative" time="-1" /></testsuite>',
            "negative or nonfinite duration",
        ),
        (
            '<testsuite><testcase classname="tests.x" name="infinite" time="nan" /></testsuite>',
            "negative or nonfinite duration",
        ),
        (
            """<testsuite>
            <testcase classname="tests.x" name="same" time="1" />
            <testcase classname="tests.x" name="same" time="2" />
            </testsuite>""",
            "duplicate testcase identity",
        ),
        (
            """<testsuite><testcase classname="tests.x" name="ambiguous" time="1">
            <failure /><skipped />
            </testcase></testsuite>""",
            "ambiguous outcomes",
        ),
        ("<testsuites><testsuite><testsuite /></testsuite></testsuites>", "unsupported child"),
    ],
)
def test_rejects_malformed_durations_duplicates_and_unsupported_shapes(
    tmp_path: Path, xml: str, message: str
) -> None:
    report = tmp_path / "invalid.xml"
    report.write_text(xml)

    result = run_tool(report)

    assert result.returncode == 2
    assert result.stdout == ""
    assert message in result.stderr


def test_rejects_nonpositive_limit_before_reading_input(tmp_path: Path) -> None:
    result = run_tool(tmp_path / "absent.xml", "--limit", "0")

    assert result.returncode == 2
    assert "must be a positive integer" in result.stderr
