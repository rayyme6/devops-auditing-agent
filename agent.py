import json

from llm import LLMClient
from tools import RepoTools


class DevOpsAgent:
    """
    Autonomous DevOps repository auditing agent.

    The LLM decides which inspection tools to use.
    Python validates and executes those tool requests.
    """

    MAX_RESULT_CHARS = 12000

    def __init__(
        self,
        repo_path,
        llm=None,
        tools=None,
        max_steps=12
    ):
        self.repo_path = repo_path

        self.llm = llm if llm is not None else LLMClient()

        self.tools = (
            tools if tools is not None
            else RepoTools(repo_path)
        )

        self.max_steps = max_steps

        # Only these functions can be executed by the LLM.
        self.available_tools = {
            "list_files": self.tools.list_files,
            "read_file": self.tools.read_file,
            "search_code": self.tools.search_code,
            "git_log": self.tools.git_log
        }

        self.expected_arguments = {
            "list_files": set(),
            "read_file": {"path"},
            "search_code": {"pattern"},
            "git_log": set()
        }

    def execute_tool(self, tool_name, arguments):
        """
        Validate and execute an LLM-requested tool.
        """

        if tool_name not in self.available_tools:
            return {
                "success": False,
                "error": "Unknown or disallowed tool"
            }

        if not isinstance(arguments, dict):
            return {
                "success": False,
                "error": "Arguments must be a JSON object"
            }

        expected = self.expected_arguments[tool_name]

        if set(arguments) != expected:
            return {
                "success": False,
                "error": (
                    f"Invalid arguments for {tool_name}. "
                    f"Expected: {sorted(expected)}"
                )
            }

        for value in arguments.values():
            if not isinstance(value, str) or not value.strip():
                return {
                    "success": False,
                    "error": "Arguments must be nonempty strings"
                }

        try:
            function = self.available_tools[tool_name]

            result = function(**arguments)

            serialized = json.dumps(
                result,
                ensure_ascii=False
            )

            if len(serialized) > self.MAX_RESULT_CHARS:
                return {
                    "success": True,
                    "result_preview": serialized[
                        :self.MAX_RESULT_CHARS
                    ],
                    "truncated": True
                }

            return {
                "success": True,
                "result": result
            }

        except (OSError, ValueError) as error:
            # Avoid leaking sensitive details into the LLM.
            return {
                "success": False,
                "error": type(error).__name__
            }

    def run(self):
        """
        Run the autonomous investigation.

        Returns a preliminary text summary.
        JSON reporting will be added in Step 8.
        """

        print("\n===================================")
        print("      AI DevOps Auditing Agent")
        print("===================================")

        messages = [
            {
                "role": "user",
                "content": (
                    "Investigate this locally available Git repository "
                    "for genuine DevOps best-practice violations. "

                    "Begin by discovering its structure. "

                    "Choose subsequent inspection tools dynamically "
                    "based on the evidence you observe. "

                    "Investigate relevant security, testing, "
                    "dependencies, CI/CD, configuration, "
                    "repository hygiene, code quality, "
                    "collaboration, and build practices. "

                    "Do not invent missing files or vulnerabilities. "

                    "Do not report optional missing tools as defects "
                    "when acceptable alternatives exist. "

                    "When you have sufficient evidence, finish "
                    "with ONLY the JSON object described "
                    "in your system instructions."
                )
            }
        ]

        for step in range(self.max_steps):

            print(f"\n[Agent] Investigation step {step + 1}")

            response = self.llm.get_next_action(
                messages,
                require_tool=(step == 0)
            )

            assistant_message = response.choices[0].message

            tool_calls = assistant_message.tool_calls or []

            # No tool calls means the LLM has finished.
            if not tool_calls:

                final_response = assistant_message.content

                if not final_response:
                    raise RuntimeError(
                        "LLM returned an empty final response"
                    )

                print("\n[Agent] Investigation completed.")

                return final_response

            # Record the assistant's tool requests.
            messages.append({
                "role": "assistant",
                "content": assistant_message.content or "",
                "tool_calls": [
                    {
                        "id": call.id,
                        "type": "function",
                        "function": {
                            "name": call.function.name,
                            "arguments": call.function.arguments
                        }
                    }
                    for call in tool_calls
                ]
            })

            # Execute every requested tool.
            for call in tool_calls:

                tool_name = call.function.name

                print(f"[Agent] Selected tool: {tool_name}")

                try:
                    arguments = json.loads(
                        call.function.arguments
                    )

                except (json.JSONDecodeError, TypeError):
                    arguments = None

                result = self.execute_tool(
                    tool_name,
                    arguments
                )

                print(
                    "[Agent] Tool execution:",
                    "SUCCESS" if result["success"] else "FAILED"
                )

                # Return the actual result to the LLM.
                messages.append({
                    "role": "tool",
                    "tool_call_id": call.id,
                    "content": json.dumps(result)
                })

        raise RuntimeError(
            "Agent exceeded the maximum investigation steps"
        )