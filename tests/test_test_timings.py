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


def test_rejects_utf16_dtd_before_expanding_its_entity(tmp_path: Path) -> None:
    report = tmp_path / "utf16-dtd.xml"
    report.write_bytes(
        """<!DOCTYPE testsuite [<!ENTITY label "expanded">]>
        <testsuite><testcase classname="tests.x" name="&label;" time="1" /></testsuite>""".encode(
            "utf-16"
        )
    )

    result = run_tool(report)

    assert result.returncode == 2
    assert result.stdout == ""
    assert "unsupported DTD" in result.stderr
    assert "expanded" not in result.stderr


def test_selects_only_observed_passes_from_an_ordered_complete_collection(tmp_path: Path) -> None:
    report = tmp_path / "partial.xml"
    report.write_text(
        """<testsuite name="pytest" tests="5" time="12">
        <testcase classname="tests.test_gate" name="test_pass[param::one]" time="1" />
        <testcase classname="tests.test_gate.TestGroup"
          name="test_class[value.with.dot]literal]" time="2" />
        <testcase classname="tests.test_gate" name="test_failed" time="3"><failure /></testcase>
        <testcase classname="tests.test_gate" name="test_error" time="4"><error /></testcase>
        <testcase classname="tests.test_gate" name="test_skipped" time="2"><skipped /></testcase>
        </testsuite>"""
    )
    collection = [
        "tests/test_gate.py::test_pass[param::one]",
        "tests/test_gate.py::test_failed",
        "tests/test_gate.py::TestGroup::test_class[value.with.dot]literal]",
        "tests/test_gate.py::test_error",
        "tests/test_gate.py::test_skipped",
        "tests/test_gate.py::test_absent",
    ]
    collected = tmp_path / "collected.json"
    collected.write_text(json.dumps(collection))

    result = run_tool(report, "--collected-nodeids", collected, "--limit", "1")

    assert result.returncode == 0, result.stderr
    observed = json.loads(result.stdout)
    assert len(observed["current"]["slowest"]) == 1
    assert observed["selection"] == {
        "collected_nodeids": collection,
        "retained_passing_nodeids": [collection[0], collection[2]],
        "remaining_nodeids": [collection[1], *collection[3:]],
        "collected_count": 6,
        "retained_passing_count": 2,
        "remaining_count": 4,
    }


def test_old_invocation_output_is_unchanged_without_a_collection(tmp_path: Path) -> None:
    report = tmp_path / "report.xml"
    report.write_text(
        '<testsuite><testcase classname="tests.x" name="test_one" time="1" /></testsuite>'
    )

    result = run_tool(report)

    assert result.returncode == 0, result.stderr
    assert set(json.loads(result.stdout)) == {"schema", "current"}


def test_zero_observed_cases_retain_no_passes(tmp_path: Path) -> None:
    report = tmp_path / "empty.xml"
    report.write_text('<testsuite name="stopped" tests="0" time="0" />')
    collection = ["tests/test_gate.py::test_one", "tests/test_gate.py::TestGroup::test_two[x]"]
    collected = tmp_path / "collected.json"
    collected.write_text(json.dumps(collection))

    result = run_tool(report, "--collected-nodeids", collected)

    assert result.returncode == 0, result.stderr
    selection = json.loads(result.stdout)["selection"]
    assert selection["retained_passing_nodeids"] == []
    assert selection["remaining_nodeids"] == collection
    assert selection["retained_passing_count"] == 0


@pytest.mark.parametrize(
    ("collection", "message"),
    [
        ([], "nonempty JSON array"),
        (["tests/test_x.py::test_one", "tests/test_x.py::test_one"], "duplicates"),
        (["tests/test_x.py::test_one", 3], "only nonempty strings"),
        (["tests/test_x.py"], "supported Python test node"),
        (["tests/test_x.py::test_one[param::broken"], "malformed parameter name"),
        (["tests/test_x.py::Helper::test_one"], "unsupported class or selection shape"),
        (
            [
                "tests/test_x.py::TestGroup::test_one",
                "tests/test_x/TestGroup.py::test_one",
            ],
            "ambiguous JUnit identity",
        ),
    ],
)
def test_rejects_invalid_duplicate_and_ambiguous_collections(
    tmp_path: Path, collection: object, message: str
) -> None:
    report = tmp_path / "empty.xml"
    report.write_text("<testsuite />")
    collected = tmp_path / "collected.json"
    collected.write_text(json.dumps(collection))

    result = run_tool(report, "--collected-nodeids", collected)

    assert result.returncode == 2
    assert result.stdout == ""
    assert message in result.stderr


@pytest.mark.parametrize("contents", ["{", '"not an array"', '"\\ud800"'])
def test_rejects_malformed_or_nonarray_collection_json(tmp_path: Path, contents: str) -> None:
    report = tmp_path / "empty.xml"
    report.write_text("<testsuite />")
    collected = tmp_path / "collected.json"
    collected.write_text(contents)

    result = run_tool(report, "--collected-nodeids", collected)

    assert result.returncode == 2
    assert result.stdout == ""


@pytest.mark.parametrize(
    "collected_name",
    ["test_other", "test_value[raw::value]"],
)
def test_rejects_junit_cases_absent_from_the_collection(
    tmp_path: Path, collected_name: str
) -> None:
    report = tmp_path / "report.xml"
    report.write_text(
        '<testsuite><testcase classname="tests.test_x" name="test_value[sanitized]" '
        'time="1" /></testsuite>'
    )
    collected = tmp_path / "collected.json"
    collected.write_text(json.dumps([f"tests/test_x.py::{collected_name}"]))

    result = run_tool(report, "--collected-nodeids", collected)

    assert result.returncode == 2
    assert result.stdout == ""
    assert "absent from the collected node IDs" in result.stderr
