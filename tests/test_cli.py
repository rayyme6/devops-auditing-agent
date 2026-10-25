import json

import agent as agent_module


def test_cli_success(monkeypatch, tmp_path):

    repo_url = "https://github.com/example/demo"

    output_file = tmp_path / "report.json"

    def fake_clone(url, destination):

        assert url == repo_url

        destination.mkdir(parents=True)

        (destination / "README.md").write_text(
            "# Sample Project\n",
            encoding="utf-8"
        )

        return destination

    class FakeAgent:

        def __init__(self, repo_path, max_steps=20):
            self.repo_path = repo_path

        def run(self):
            return '{"violations": []}'

    monkeypatch.setattr(
        agent_module,
        "clone_repository",
        fake_clone
    )

    monkeypatch.setattr(
        agent_module,
        "DevOpsAgent",
        FakeAgent
    )

    exit_code = agent_module.main([
        "--repo",
        repo_url,
        "--output",
        str(output_file)
    ])

    assert exit_code == 0

    assert output_file.exists()

    report = json.loads(
        output_file.read_text(encoding="utf-8")
    )

    assert report["repository"] == repo_url
    assert report["violations"] == []


def test_cli_clone_failure(monkeypatch, tmp_path):

    def fake_clone(url, destination):
        raise RuntimeError("Repository cloning failed")

    monkeypatch.setattr(
        agent_module,
        "clone_repository",
        fake_clone
    )

    output_file = tmp_path / "report.json"

    exit_code = agent_module.main([
        "--repo",
        "https://github.com/example/demo",
        "--output",
        str(output_file)
    ])

    assert exit_code != 0
    assert not output_file.exists()


def test_cli_invalid_llm_json(monkeypatch, tmp_path):

    def fake_clone(url, destination):

        destination.mkdir(parents=True)

        return destination

    class FakeAgent:

        def __init__(self, repo_path, max_steps=20):
            pass

        def run(self):
            return "This is not valid JSON"

    monkeypatch.setattr(
        agent_module,
        "clone_repository",
        fake_clone
    )

    monkeypatch.setattr(
        agent_module,
        "DevOpsAgent",
        FakeAgent
    )

    output_file = tmp_path / "report.json"

    exit_code = agent_module.main([
        "--repo",
        "https://github.com/example/demo",
        "--output",
        str(output_file)
    ])

    assert exit_code != 0
    assert not output_file.exists()