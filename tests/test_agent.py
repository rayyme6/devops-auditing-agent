import json
from types import SimpleNamespace

from agent import DevOpsAgent


def make_response(tool_name=None, arguments=None, text=None, call_id="call_1"):

    if tool_name:
        tool_calls = [
            SimpleNamespace(
                id=call_id,
                function=SimpleNamespace(
                    name=tool_name,
                    arguments=json.dumps(
                        arguments if arguments is not None else {}
                    )
                )
            )
        ]
    else:
        tool_calls = None

    message = SimpleNamespace(
        content=text,
        tool_calls=tool_calls
    )

    return SimpleNamespace(
        choices=[
            SimpleNamespace(message=message)
        ]
    )


class FakeTools:

    def __init__(self):
        self.executed = []

    def list_files(self):
        self.executed.append("list_files")
        return ["README.md", "app.py"]

    def read_file(self, path):
        self.executed.append("read_file")
        return "1: # Sample Repository"

    def search_code(self, pattern):
        self.executed.append("search_code")
        return []

    def git_log(self):
        self.executed.append("git_log")
        return "abc123 Initial commit"


class FakeLLM:

    def __init__(self):
        self.call_count = 0
        self.messages_seen = []

    def get_next_action(self, messages, require_tool=False):

        self.call_count += 1

        self.messages_seen.append(
            list(messages)
        )

        if self.call_count == 1:
            assert require_tool is True

            return make_response(
                tool_name="list_files",
                arguments={},
                call_id="call_1"
            )

        if self.call_count == 2:
            assert require_tool is False

            return make_response(
                tool_name="read_file",
                arguments={"path": "README.md"},
                call_id="call_2"
            )

        return make_response(
            text="Repository inspection completed."
        )


def test_autonomous_agent_loop():

    fake_tools = FakeTools()
    fake_llm = FakeLLM()

    agent = DevOpsAgent(
        repo_path="unused",
        llm=fake_llm,
        tools=fake_tools,
        max_steps=5
    )

    result = agent.run()

    assert result == "Repository inspection completed."

    assert fake_tools.executed == [
        "list_files",
        "read_file"
    ]

    assert fake_llm.call_count == 3

    # Verify that the second LLM request received
    # the first tool's result.
    second_request = fake_llm.messages_seen[1]

    assert any(
        message["role"] == "tool"
        and message["tool_call_id"] == "call_1"
        for message in second_request
    )


def test_unknown_tool_is_blocked():

    agent = DevOpsAgent(
        repo_path="unused",
        llm=FakeLLM(),
        tools=FakeTools()
    )

    result = agent.execute_tool(
        "delete_repository",
        {}
    )

    assert result["success"] is False


def test_invalid_tool_arguments():

    agent = DevOpsAgent(
        repo_path="unused",
        llm=FakeLLM(),
        tools=FakeTools()
    )

    result = agent.execute_tool(
        "list_files",
        {"path": ""}
    )

    assert result["success"] is False