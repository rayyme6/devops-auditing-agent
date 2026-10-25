from llm import TOOL_DEFINITIONS

from types import SimpleNamespace

import httpx
import llm

from groq import RateLimitError
from groq import BadRequestError

from llm import LLMClient


def test_required_tools():

    names = {
        tool["function"]["name"]
        for tool in TOOL_DEFINITIONS
    }

    expected = {
        "list_files",
        "read_file",
        "search_code",
        "git_log",
        "validate_yaml"
    }

    assert names == expected


def test_tool_schemas():

    for tool in TOOL_DEFINITIONS:

        parameters = tool["function"]["parameters"]

        assert parameters["type"] == "object"
        assert parameters["additionalProperties"] is False


def test_list_files_no_arguments():

    tool = next(
        tool for tool in TOOL_DEFINITIONS
        if tool["function"]["name"] == "list_files"
    )

    parameters = tool["function"]["parameters"]

    assert parameters["properties"] == {}
    assert parameters["required"] == []

def test_validate_yaml_schema():

    tool = next(
        tool for tool in TOOL_DEFINITIONS
        if tool["function"]["name"] == "validate_yaml"
    )

    parameters = tool["function"]["parameters"]

    assert parameters["type"] == "object"

    assert "path" in parameters["properties"]

    assert parameters["required"] == ["path"]

    assert parameters["additionalProperties"] is False

def test_rate_limit_retry(monkeypatch):

    class FakeCompletions:

        def __init__(self):
            self.calls = 0

        def create(self, **kwargs):

            self.calls += 1

            if self.calls == 1:

                response = httpx.Response(
                    429,
                    headers={"retry-after": "1"},
                    request=httpx.Request(
                        "POST",
                        "https://api.groq.com/openai/v1/chat/completions"
                    )
                )

                raise RateLimitError(
                    "Rate limit exceeded",
                    response=response,
                    body={}
                )

            return "successful_response"

    fake_api = FakeCompletions()

    client = LLMClient.__new__(LLMClient)

    client.model = "openai/gpt-oss-20b"

    client.client = SimpleNamespace(
        chat=SimpleNamespace(
            completions=fake_api
        )
    )

    delays = []

    monkeypatch.setattr(
        llm.time,
        "sleep",
        lambda seconds: delays.append(seconds)
    )

    result = client.get_next_action(
        [{"role": "user", "content": "Inspect repository"}]
    )

    assert result == "successful_response"
    assert fake_api.calls == 2
    assert delays == [1.0]

def test_invalid_tool_call_retry():

    class FakeCompletions:

        def __init__(self):
            self.calls = 0
            self.temperatures = []

        def create(self, **kwargs):

            self.calls += 1

            self.temperatures.append(
                kwargs["temperature"]
            )

            if self.calls == 1:

                response = httpx.Response(
                    400,
                    request=httpx.Request(
                        "POST",
                        "https://api.groq.com/openai/v1/chat/completions"
                    )
                )

                raise BadRequestError(
                    "Parsing failed",
                    response=response,
                    body={
                        "error": {
                            "code": "output_parse_failed",
                            "message": "Parsing failed"
                        }
                    }
                )

            return "successful_response"

    fake_api = FakeCompletions()

    client = LLMClient.__new__(LLMClient)

    client.model = "openai/gpt-oss-20b"

    client.client = SimpleNamespace(
        chat=SimpleNamespace(
            completions=fake_api
        )
    )

    result = client.get_next_action(
        [
            {
                "role": "user",
                "content": "Inspect the repository."
            }
        ]
    )

    assert result == "successful_response"

    assert fake_api.calls == 2

    assert fake_api.temperatures == [0.2, 0.0]