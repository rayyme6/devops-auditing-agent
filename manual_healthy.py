import json
import subprocess

from pathlib import Path
from tempfile import TemporaryDirectory

from agent import DevOpsAgent
from report import build_report


def main():

    with TemporaryDirectory() as temp_dir:

        repo = Path(temp_dir) / "healthy-repo"
        repo.mkdir()

        # Create README
        (repo / "README.md").write_text(
            "# Healthy Python Project\n\n"
            "A small application with automated tests "
            "and a CI workflow.\n",
            encoding="utf-8"
        )

        # Create .gitignore
        (repo / ".gitignore").write_text(
            "__pycache__/\n"
            ".pytest_cache/\n"
            ".venv/\n"
            ".env\n",
            encoding="utf-8"
        )

        # Create application
        (repo / "app.py").write_text(
            "def add(a, b):\n"
            "    return a + b\n",
            encoding="utf-8"
        )

        # Create tests
        tests_dir = repo / "tests"
        tests_dir.mkdir()

        (tests_dir / "test_app.py").write_text(
            "from app import add\n\n"
            "def test_add():\n"
            "    assert add(2, 3) == 5\n",
            encoding="utf-8"
        )

        # Create GitHub Actions workflow
        workflow_dir = repo / ".github" / "workflows"
        workflow_dir.mkdir(parents=True)

        (workflow_dir / "ci.yml").write_text(
            "name: CI\n"
            "on: [push, pull_request]\n"
            "permissions:\n"
            "  contents: read\n"
            "jobs:\n"
            "  test:\n"
            "    runs-on: ubuntu-latest\n"
            "    steps:\n"
            "      - uses: actions/checkout@v4\n"
            "      - uses: actions/setup-python@v5\n"
            "        with:\n"
            "          python-version: '3.11'\n"
            "      - run: python -m pip install pytest\n"
            "      - run: python -m pytest -q\n",
            encoding="utf-8"
        )

        # Initialize Git repository
        subprocess.run(
            ["git", "init", "-q", str(repo)],
            check=True
        )

        subprocess.run(
            ["git", "-C", str(repo), "add", "."],
            check=True
        )

        subprocess.run(
            [
                "git", "-C", str(repo),
                "-c", "user.name=Test User",
                "-c", "user.email=test@example.com",
                "commit", "-q",
                "-m", "Initial healthy project"
            ],
            check=True
        )

        print("\n========== HEALTHY REPOSITORY AUDIT ==========")

        agent = DevOpsAgent(
            repo_path=repo,
            max_steps=15
        )

        result = agent.run()

        report = build_report(
            repo_url="https://github.com/example/healthy-local-fixture",
            llm_output=result,
            repo_path=repo
        )

        print("\n========== AUDIT RESULTS ==========")

        print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()