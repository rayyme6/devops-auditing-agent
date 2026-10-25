import subprocess

import pytest

from tools import RepoTools


@pytest.fixture
def sample_repo(tmp_path):
    """
    Create a temporary local Git repository for testing.
    """

    repo = tmp_path / "sample-repo"
    repo.mkdir()

    subprocess.run(
        ["git", "init", "-q", str(repo)],
        check=True
    )

    (repo / "README.md").write_text(
        "# Sample Repository\n",
        encoding="utf-8"
    )

    (repo / "app.py").write_text(
        'print("hello")\n# TODO: add tests\n',
        encoding="utf-8"
    )

    subprocess.run(
        ["git", "-C", str(repo), "add", "."],
        check=True
    )

    subprocess.run(
        [
            "git",
            "-C",
            str(repo),
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

    return repo


def test_list_files(sample_repo):

    tools = RepoTools(sample_repo)

    files = tools.list_files()

    assert "README.md" in files
    assert "app.py" in files


def test_read_file(sample_repo):

    tools = RepoTools(sample_repo)

    content = tools.read_file("app.py")

    assert '1: print("hello")' in content


def test_search_code(sample_repo):

    tools = RepoTools(sample_repo)

    results = tools.search_code("TODO")

    assert len(results) == 1
    assert results[0]["file"] == "app.py"
    assert results[0]["line"] == 2


def test_git_log(sample_repo):

    tools = RepoTools(sample_repo)

    history = tools.git_log()

    assert "Initial commit" in history


def test_path_traversal_blocked(sample_repo):

    tools = RepoTools(sample_repo)

    with pytest.raises(ValueError):
        tools.read_file("../outside.txt")

def test_valid_yaml(sample_repo):

    tools = RepoTools(sample_repo)

    workflow = sample_repo / "ci.yml"

    workflow.write_text(
        "name: CI\n"
        "on:\n"
        "  push:\n",
        encoding="utf-8"
    )

    result = tools.validate_yaml("ci.yml")

    assert result["valid"] is True


def test_invalid_yaml(sample_repo):

    tools = RepoTools(sample_repo)

    workflow = sample_repo / "bad.yml"

    workflow.write_text(
        "name: [invalid\n",
        encoding="utf-8"
    )

    result = tools.validate_yaml("bad.yml")

    assert result["valid"] is False