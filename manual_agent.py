import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory

from agent import DevOpsAgent
import json
from report import build_report, save_report


def main():

    with TemporaryDirectory() as temp_dir:

        repo_path = Path(temp_dir) / "sample-repo"

        repo_path.mkdir()

        # Create harmless sample files.
        (repo_path / "README.md").write_text(
            "# Sample Project\n\n"
            "A small Python application.\n",
            encoding="utf-8"
        )

        (repo_path / "app.py").write_text(
            'print("Hello DevOps!")\n',
            encoding="utf-8"
        )

        # Create a GitHub Actions workflow with excessive permissions.

        workflow_dir = repo_path / ".github" / "workflows"

        workflow_dir.mkdir(parents=True, exist_ok=True)

        workflow_file = workflow_dir / "ci.yml"

        workflow_file.write_text(
            """name: CI

        on:
        push:

        permissions: write-all

        jobs:
        check:
            runs-on: ubuntu-latest

            steps:
            - uses: actions/checkout@v4
            - name: Run check
                run: echo "Checking project"
        """,
            encoding="utf-8"
        )

        # Initialize a local Git repository.
        subprocess.run(
            ["git", "init", "-q", str(repo_path)],
            check=True
        )

        subprocess.run(
            ["git", "-C", str(repo_path), "add", "."],
            check=True
        )

        subprocess.run(
            [
                "git",
                "-C",
                str(repo_path),
                "-c",
                "user.name=Test User",
                "-c",
                "user.email=test@example.com",
                "commit",
                "-q",
                "-m",
                "Initial commit"
            ],
            check=True
        )

        print("Starting autonomous repository inspection...")

        agent = DevOpsAgent(
            repo_path=repo_path,
            max_steps=12
        )

        result = agent.run()

        print("\n========== VALIDATING FINDINGS ==========")

        report = build_report(
            repo_url="https://github.com/example/manual-test",
            llm_output=result,
            repo_path=repo_path
        )

        print(json.dumps(report, indent=2))

        output_file = "manual_report.json"

        save_report(
            report=report,
            output_path=output_file,
            repo_path=repo_path
        )

        print(f"\nReport saved to: {output_file}")


if __name__ == "__main__":
    main()