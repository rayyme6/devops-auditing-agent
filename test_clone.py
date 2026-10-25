from tools import clone_repository
from tempfile import TemporaryDirectory
from pathlib import Path

repo_url = "https://github.com/psf/requests"

with TemporaryDirectory() as temp_dir:

    destination = Path(temp_dir) / "demo-repo"

    repo_path = clone_repository(repo_url, destination)

    print("\nRepository cloned successfully!")
    print("Repository location:", repo_path)

    print("\nFiles in repository:")

    for file in repo_path.iterdir():
        print(file.name)