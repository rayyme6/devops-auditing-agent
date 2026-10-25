import json

from llm import LLMClient


def main():

    print("Initializing Groq LLM...")

    llm = LLMClient()

    messages = [
        {
            "role": "user",
            "content": (
                "You are beginning a DevOps audit of "
                "an unfamiliar GitHub repository. "
                "You have not inspected any files. "
                "Choose the best first tool to "
                "investigate the repository structure."
            )
        }
    ]

    print("Asking LLM to select a tool...")

    response = llm.get_next_action(
        messages,
        require_tool=True
    )

    tool_calls = (
        response.choices[0].message.tool_calls or []
    )

    if not tool_calls:
        raise RuntimeError(
            "The LLM did not request a tool."
        )

    for call in tool_calls:

        tool_name = call.function.name
        arguments = json.loads(call.function.arguments)

        print("\nLLM selected tool:")
        print(tool_name)

        print("\nTool arguments:")
        print(json.dumps(arguments, indent=2))

        expected_parameters = {
            "list_files": set(),
            "read_file": {"path"},
            "search_code": {"pattern"},
            "git_log": set()
        }

        if tool_name not in expected_parameters:
            raise ValueError(f"Unknown tool: {tool_name}")

        if not isinstance(arguments, dict):
            raise ValueError("Tool arguments must be an object")

        expected = expected_parameters[tool_name]

        if set(arguments.keys()) != expected:
            raise ValueError(
                f"Invalid arguments for {tool_name}: "
                f"expected {expected}, got {set(arguments.keys())}"
            )

        for value in arguments.values():
            if not isinstance(value, str) or not value.strip():
                raise ValueError("Tool arguments must be nonempty strings")

        print("\nTool request validated successfully!")


if __name__ == "__main__":
    main()