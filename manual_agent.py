import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory

from agent import DevOpsAgent


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

        print("\n========== PRELIMINARY SUMMARY ==========")
        print(result)


if __name__ == "__main__":
    main()