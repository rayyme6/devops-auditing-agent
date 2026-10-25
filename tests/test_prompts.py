from prompts import SYSTEM_PROMPT


def test_required_audit_categories():

    categories = [
        "Repository hygiene",
        "Dependency management",
        "Code quality",
        "Testing",
        "GitHub Actions / CI",
        "Security",
        "Configuration",
        "Collaboration",
        "Build and release"
    ]

    for category in categories:
        assert category in SYSTEM_PROMPT


def test_evidence_requirements():

    assert "evidence" in SYSTEM_PROMPT.lower()
    assert "recommendation" in SYSTEM_PROMPT.lower()
    assert "severity" in SYSTEM_PROMPT.lower()


def test_json_output_instructions():

    assert '"violations"' in SYSTEM_PROMPT
    assert '"rule_id"' in SYSTEM_PROMPT
    assert '"category"' in SYSTEM_PROMPT


def test_false_positive_instructions():

    assert "optional" in SYSTEM_PROMPT.lower()
    assert "Do not invent" in SYSTEM_PROMPT