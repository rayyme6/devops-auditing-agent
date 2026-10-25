import json

import pytest

from report import build_report, save_report


@pytest.fixture
def sample_repo(tmp_path):

    repo = tmp_path / "sample-repo"

    workflow_dir = repo / ".github" / "workflows"
    workflow_dir.mkdir(parents=True)

    workflow = workflow_dir / "ci.yml"

    workflow.write_text(
        "name: CI\n"
        "on:\n"
        "  push:\n"
        "\n"
        "permissions: write-all\n",
        encoding="utf-8"
    )

    return repo


@pytest.fixture
def valid_finding():

    return {
        "rule_id": "SEC-001",
        "category": "security",
        "severity": "high",
        "file": ".github/workflows/ci.yml",
        "line": 5,
        "description": "Excessive workflow permissions",
        "evidence": "Workflow requests write-all permissions",
        "recommendation": "Apply least-privilege permissions"
    }


def test_valid_report(sample_repo, valid_finding, tmp_path):

    llm_output = json.dumps({
        "violations": [valid_finding]
    })

    report = build_report(
        "https://github.com/example/demo",
        llm_output,
        sample_repo
    )

    output = tmp_path / "report.json"

    save_report(report, output, sample_repo)

    saved = json.loads(output.read_text())

    assert saved["repository"] == (
        "https://github.com/example/demo"
    )

    assert len(saved["violations"]) == 1

    assert saved["violations"][0]["severity"] == "high"


def test_empty_violations(sample_repo):

    report = build_report(
        "https://github.com/example/demo",
        '{"violations": []}',
        sample_repo
    )

    assert report["violations"] == []


def test_invalid_severity(sample_repo, valid_finding):

    valid_finding["severity"] = "extreme"

    with pytest.raises(ValueError):
        build_report(
            "https://github.com/example/demo",
            json.dumps({"violations": [valid_finding]}),
            sample_repo
        )


def test_duplicate_findings(sample_repo, valid_finding):

    report = build_report(
        "https://github.com/example/demo",
        json.dumps({
            "violations": [
                valid_finding,
                valid_finding.copy()
            ]
        }),
        sample_repo
    )

    assert len(report["violations"]) == 1


def test_invalid_line(sample_repo, valid_finding):

    valid_finding["line"] = 999

    with pytest.raises(ValueError):
        build_report(
            "https://github.com/example/demo",
            json.dumps({"violations": [valid_finding]}),
            sample_repo
        )


def test_invalid_json(sample_repo):

    with pytest.raises(ValueError):
        build_report(
            "https://github.com/example/demo",
            "This is not JSON",
            sample_repo
        )


def test_path_traversal(sample_repo, valid_finding):

    valid_finding["file"] = "../outside.txt"

    with pytest.raises(ValueError):
        build_report(
            "https://github.com/example/demo",
            json.dumps({"violations": [valid_finding]}),
            sample_repo
        )


def test_secret_redaction(sample_repo, valid_finding):

    valid_finding["evidence"] = (
        "Found api_key=abcdef123456 in source"
    )

    report = build_report(
        "https://github.com/example/demo",
        json.dumps({"violations": [valid_finding]}),
        sample_repo
    )

    evidence = report["violations"][0]["evidence"]

    assert "abcdef123456" not in evidence
    assert "[REDACTED]" in evidence


def test_cannot_write_inside_repository(
    sample_repo,
    tmp_path
):

    report = {
        "repository": "https://github.com/example/demo",
        "violations": []
    }

    with pytest.raises(ValueError):
        save_report(
            report,
            sample_repo / "report.json",
            sample_repo
        )

def test_reject_false_yaml_syntax_finding(
    sample_repo,
    valid_finding
):

    valid_finding["rule_id"] = "CI-001"

    valid_finding["description"] = (
        "YAML syntax error in workflow configuration"
    )

    valid_finding["line"] = 2

    llm_output = json.dumps({
        "violations": [valid_finding]
    })

    report = build_report(
        "https://github.com/example/demo",
        llm_output,
        sample_repo
    )

    assert report["violations"] == []

def test_accept_real_yaml_syntax_finding(
    sample_repo,
    valid_finding
):

    workflow = (
        sample_repo
        / ".github"
        / "workflows"
        / "ci.yml"
    )

    workflow.write_text(
        "name: [invalid\n",
        encoding="utf-8"
    )

    valid_finding["rule_id"] = "CI-001"

    valid_finding["description"] = (
        "YAML syntax error in workflow configuration"
    )

    valid_finding["line"] = 1

    llm_output = json.dumps({
        "violations": [valid_finding]
    })

    report = build_report(
        "https://github.com/example/demo",
        llm_output,
        sample_repo
    )

    assert len(report["violations"]) == 1

    assert report["violations"][0]["rule_id"] == "CI-001"