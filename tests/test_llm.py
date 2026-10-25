from llm import TOOL_DEFINITIONS


def test_required_tools():

    names = {
        tool["function"]["name"]
        for tool in TOOL_DEFINITIONS
    }

    expected = {
        "list_files",
        "read_file",
        "search_code",
        "git_log"
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