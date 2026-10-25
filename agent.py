import json

from llm import LLMClient
from tools import RepoTools

import argparse
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

from tools import clone_repository
from report import build_report, save_report

from groq import RateLimitError


class DevOpsAgent:
    """
    Autonomous DevOps repository auditing agent.

    The LLM decides which inspection tools to use.
    Python validates and executes those tool requests.
    """

    MAX_RESULT_CHARS = 4000

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

def main(argv=None):
    """
    Command-line entry point for the DevOps auditing agent.
    """

    parser = argparse.ArgumentParser(
        description="AI-powered DevOps Repository Auditing Agent"
    )

    parser.add_argument(
        "--repo",
        required=True,
        help="Public GitHub repository URL"
    )

    parser.add_argument(
        "--output",
        required=True,
        help="Path to the JSON report"
    )

    args = parser.parse_args(argv)

    print("\n===================================")
    print("      DevOps Repository Audit")
    print("===================================")

    try:
        # Inspect the repository in a temporary directory.
        with TemporaryDirectory(
            prefix="devops-audit-"
        ) as temp_dir:

            destination = Path(temp_dir) / "repository"

            # Step 1: Clone repository
            print("\n[1] Cloning repository...")

            repo_path = clone_repository(
                args.repo,
                destination
            )

            # Step 2: Initialize AI agent
            print("\n[2] Initializing AI agent...")

            auditing_agent = DevOpsAgent(
                repo_path=repo_path,
                max_steps=20
            )

            # Step 3: Execute autonomous investigation
            print("\n[3] Starting repository investigation...")

            llm_output = auditing_agent.run()

            # Step 4: Validate findings
            print("\n[4] Validating audit findings...")

            report = build_report(
                repo_url=args.repo,
                llm_output=llm_output,
                repo_path=repo_path
            )

            # Step 5: Save JSON report
            print("\n[5] Saving JSON report...")

            output_path = save_report(
                report=report,
                output_path=args.output,
                repo_path=repo_path
            )

            print("\n===================================")
            print("        AUDIT COMPLETED")
            print("===================================")

            print(
                f"\nViolations found: "
                f"{len(report['violations'])}"
            )

            print(f"Report saved to: {output_path}")

            return 0

    except RateLimitError as error:

        response = getattr(error, "response", None)

        headers = (
            response.headers
            if response is not None
            else {}
        )

        print(
            "\nERROR: Groq API rate limit exceeded.",
            file=sys.stderr
        )

        retry_after = headers.get("retry-after")

        if retry_after:
            print(
                f"Suggested retry delay: {retry_after} seconds",
                file=sys.stderr
            )

        print(
            "Check your GroqCloud rate limits and quota.",
            file=sys.stderr
        )

        return 1

    except (ValueError, RuntimeError, OSError) as error:

        print(
            f"\nERROR: {error}",
            file=sys.stderr
        )

        return 1

    except Exception as error:

        print(
            f"\nERROR ({type(error).__name__}): "
            "Audit could not be completed. "
            "Check the repository URL, API configuration, "
            "network connection, and available API quota.",
            file=sys.stderr
        )

        return 1


if __name__ == "__main__":
    sys.exit(main())