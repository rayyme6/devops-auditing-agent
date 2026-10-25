import subprocess
import re
from pathlib import Path
from urllib.parse import urlparse


def clone_repository(repo_url, destination):
    """
    Clone a public GitHub repository into a local folder.
    """

    print(f"Cloning repository: {repo_url}")

    # Validate GitHub repository URL
    parsed = urlparse(repo_url)

    if (
        parsed.scheme != "https"
        or parsed.netloc != "github.com"
        or parsed.query
        or parsed.fragment
        or parsed.username
        or parsed.password
    ):
        raise ValueError("Invalid GitHub repository URL")

    parts = parsed.path.strip("/").split("/")

    if len(parts) != 2:
        raise ValueError("Expected a GitHub owner and repository name")

    owner, repo = parts
    repo = repo.removesuffix(".git")

    if not re.fullmatch(r"[A-Za-z0-9-]+", owner):
        raise ValueError("Invalid repository owner")

    if not re.fullmatch(r"[A-Za-z0-9._-]+", repo) or repo in (".", ".."):
        raise ValueError("Invalid repository name")

    destination = Path(destination).resolve()

    if destination.exists():
        raise ValueError("Destination already exists")

    validated_url = f"https://github.com/{owner}/{repo}.git"

    try:
        subprocess.run(
            [
                "git",
                "clone",
                "--depth",
                "50",
                "--single-branch",
                validated_url,
                str(destination)
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=120
        )

        print("Repository cloned successfully!")

        return destination

    except subprocess.TimeoutExpired:
        raise RuntimeError("Repository cloning timed out")

    except subprocess.CalledProcessError:
        raise RuntimeError("Failed to clone repository")