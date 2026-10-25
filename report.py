import json
import os
import re
import tempfile
from pathlib import Path


REQUIRED_FIELDS = {
    "rule_id",
    "category",
    "severity",
    "file",
    "line",
    "description",
    "evidence",
    "recommendation",
}

ALLOWED_SEVERITIES = {
    "critical",
    "high",
    "medium",
    "low",
}


# Basic protection against common credential formats.
SECRET_PATTERNS = [
    re.compile(
        r"\b(?:sk-[A-Za-z0-9_-]{12,}|"
        r"gh[pousr]_[A-Za-z0-9_]{12,}|"
        r"github_pat_[A-Za-z0-9_]{12,})\b"
    ),
]

ASSIGNMENT_PATTERN = re.compile(
    r"(?i)(\b(?:password|api[_-]?key|secret(?:_key)?|"
    r"(?:access_)?token)\s*[:=]\s*['\"]?)"
    r"([A-Za-z0-9_./+=-]{6,})"
)


def redact_secrets(text):
    """Redact common credential patterns."""

    for pattern in SECRET_PATTERNS:
        text = pattern.sub("[REDACTED]", text)

    text = ASSIGNMENT_PATTERN.sub(
        lambda match: match.group(1) + "[REDACTED]",
        text
    )

    return text


def validate_file_location(repo_path, file, line):
    """
    Check that cited files and lines exist in the repository.

    This verifies locations, not whether the alleged
    DevOps violation is semantically correct.
    """

    if file is None:
        if line is not None:
            raise ValueError(
                "A line number cannot exist without a file"
            )
        return

    if not isinstance(file, str) or not file.strip():
        raise ValueError("Invalid file path")

    relative = Path(file)

    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError("Unsafe file path")

    root = Path(repo_path).resolve()
    target = (root / relative).resolve()

    if not target.is_relative_to(root):
        raise ValueError("File is outside repository")

    # Reject symbolic links in any path component.
    current = root

    for part in relative.parts:
        current = current / part

        if current.is_symlink():
            raise ValueError("Symbolic links are not supported")

    if not target.is_file():
        raise ValueError(f"Evidence file does not exist: {file}")

    if line is not None:

        if type(line) is not int or line < 1:
            raise ValueError("Line must be a positive integer")

        with target.open(
            "r",
            encoding="utf-8",
            errors="replace"
        ) as source:
            line_count = sum(1 for _ in source)

        if line > line_count:
            raise ValueError(
                f"Line {line} does not exist in {file}"
            )


def validate_violation(violation, repo_path):
    """Validate one LLM-generated finding."""

    if not isinstance(violation, dict):
        raise ValueError("Violation must be an object")

    if set(violation) != REQUIRED_FIELDS:
        raise ValueError(
            "Violation does not match the required schema"
        )

    for field in [
        "rule_id",
        "category",
        "severity",
        "description",
        "evidence",
        "recommendation"
    ]:
        value = violation[field]

        if not isinstance(value, str) or not value.strip():
            raise ValueError(
                f"Invalid or missing value for {field}"
            )

    if violation["severity"] not in ALLOWED_SEVERITIES:
        raise ValueError("Invalid severity value")

    validate_file_location(
        repo_path,
        violation["file"],
        violation["line"]
    )

    cleaned = dict(violation)

    for field in [
        "description",
        "evidence",
        "recommendation"
    ]:
        cleaned[field] = redact_secrets(cleaned[field])

    return cleaned


def build_report(repo_url, llm_output, repo_path):
    """
    Convert LLM-generated JSON into a validated report.
    """

    if not isinstance(repo_url, str) or not repo_url.strip():
        raise ValueError("Invalid repository URL")

    try:
        data = json.loads(llm_output)

    except (json.JSONDecodeError, TypeError) as error:
        raise ValueError(
            "LLM returned invalid JSON"
        ) from error

    if not isinstance(data, dict):
        raise ValueError("LLM output must be a JSON object")

    if set(data) != {"violations"}:
        raise ValueError(
            "LLM output must contain a violations array"
        )

    if not isinstance(data["violations"], list):
        raise ValueError("Violations must be a list")

    validated = []
    seen = set()

    for violation in data["violations"]:

        finding = validate_violation(
            violation,
            repo_path
        )

        # Avoid reporting the same rule at the same location
        # more than once.
        identity = (
            finding["rule_id"],
            finding["file"],
            finding["line"]
        )

        if identity in seen:
            continue

        seen.add(identity)
        validated.append(finding)

    return {
        "repository": repo_url,
        "violations": validated
    }


def save_report(report, output_path, repo_path):
    """
    Atomically write the JSON report.

    Never write inside the inspected repository.
    """

    root = Path(repo_path).resolve()
    output = Path(output_path).resolve()

    if output.is_relative_to(root):
        raise ValueError(
            "Report cannot be written inside the inspected repository"
        )

    output.parent.mkdir(parents=True, exist_ok=True)

    temporary_path = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=output.parent,
            prefix=".audit-",
            suffix=".tmp",
            delete=False
        ) as handle:

            temporary_path = Path(handle.name)

            json.dump(
                report,
                handle,
                indent=2,
                ensure_ascii=False
            )

            handle.write("\n")

        os.replace(temporary_path, output)

    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)

    return output