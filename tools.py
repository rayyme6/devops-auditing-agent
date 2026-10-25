import subprocess
import re
from pathlib import Path
from urllib.parse import urlparse
import yaml


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

SECRET_LIKE_VALUES = re.compile(
    r"\b(?:"
    r"gh[pousr]_[A-Za-z0-9_]{16,}"
    r"|github_pat_[A-Za-z0-9_]{16,}"
    r"|sk-[A-Za-z0-9_-]{16,}"
    r"|AKIA[0-9A-Z]{16}"
    r")\b"
)

class RepoTools:
    """
    Tools used by the AI agent to inspect Git repositories.
    """

    MAX_FILE_SIZE = 200_000

    def __init__(self, repo_path):
        self.repo_path = Path(repo_path).resolve()

        if not (self.repo_path / ".git").exists():
            raise ValueError("Not a valid Git repository")

    def list_files(self):
        """
        List tracked files in the repository.
        """

        result = subprocess.run(
            [
                "git",
                "-C",
                str(self.repo_path),
                "ls-files",
                "-z"
            ],
            capture_output=True,
            text=True,
            check=True,
            timeout=30
        )

        files = [
            f for f in result.stdout.split("\0") if f
        ]

        return files[:3000]

    def _safe_file(self, path):
        """
        Ensure the requested file is inside the repository.
        """

        if not isinstance(path, str) or not path:
            raise ValueError("Invalid file path")

        requested = Path(path)

        if requested.is_absolute() or ".." in requested.parts:
            raise ValueError("Unsafe file path")

        file_path = self.repo_path / requested

        if file_path.is_symlink():
            raise ValueError("Symbolic links are not supported")

        resolved = file_path.resolve()

        if not resolved.is_relative_to(self.repo_path):
            raise ValueError("Path outside repository")

        if not resolved.is_file():
            raise FileNotFoundError(path)

        if resolved.stat().st_size > self.MAX_FILE_SIZE:
            raise ValueError("File exceeds inspection size limit")

        return resolved

    def _read_text(self, path):
        """
        Read a small text file safely.
        """

        file_path = self._safe_file(path)

        data = file_path.read_bytes()

        if b"\x00" in data:
            raise ValueError("Binary file not supported")

        return data.decode("utf-8", errors="replace")

    @staticmethod
    def _redact(line):
        """
        Prevent common credentials from being returned
        to the LLM through repository inspection tools.
        """

        sensitive_terms = [
            "password",
            "secret",
            "api_key",
            "apikey",
            "token",
            "authorization",
            "private_key"
        ]

        lower_line = line.lower()

        contains_sensitive_keyword = any(
            term in lower_line
            for term in sensitive_terms
        )

        contains_credential_pattern = bool(
            SECRET_LIKE_VALUES.search(line)
        )

        if (
            contains_sensitive_keyword
            or contains_credential_pattern
        ):
            return "[REDACTED: potentially sensitive content]"

        return line[:500]

    def read_file(self, path):
        """
        Read a repository file and include line numbers.
        """

        content = self._read_text(path)

        lines = content.splitlines()

        numbered_lines = []

        for number, line in enumerate(lines, start=1):
            numbered_lines.append(
                f"{number}: {self._redact(line)}"
            )

        return "\n".join(numbered_lines)

    def search_code(self, pattern):
        """
        Search tracked repository files for a literal pattern.
        """

        if not isinstance(pattern, str) or not pattern:
            raise ValueError("Invalid search pattern")

        if len(pattern) > 100:
            raise ValueError("Search pattern too long")

        matches = []

        for path in self.list_files():

            try:
                content = self._read_text(path)
            except (OSError, ValueError):
                continue

            for number, line in enumerate(
                content.splitlines(), start=1
            ):

                if pattern.lower() in line.lower():

                    matches.append({
                        "file": path,
                        "line": number,
                        "snippet": self._redact(line)
                    })

                    if len(matches) >= 100:
                        return matches

        return matches

    def git_log(self):
        """
        Retrieve the latest 20 Git commits.
        """

        result = subprocess.run(
            [
                "git",
                "-C",
                str(self.repo_path),
                "log",
                "-n",
                "20",
                "--format=%h %s"
            ],
            capture_output=True,
            text=True,
            check=True,
            timeout=30
        )

        return "\n".join(
            self._redact(line)
            for line in result.stdout.splitlines()
        )

    def validate_yaml(self, path):
        """
        Check whether a YAML file has valid syntax.

        This checks syntax, not GitHub Actions semantics.
        """

        if not path.endswith((".yml", ".yaml")):
            return {
                "valid": False,
                "error": "Not a YAML file"
            }

        content = self._read_text(path)

        try:
            yaml.safe_load(content)

            return {
                "valid": True,
                "file": path,
                "message": "YAML syntax is valid"
            }

        except yaml.YAMLError as error:

            mark = getattr(error, "problem_mark", None)

            return {
                "valid": False,
                "file": path,
                "line": (
                    mark.line + 1
                    if mark is not None
                    else None
                ),
                "error": "YAML syntax error detected"
            }