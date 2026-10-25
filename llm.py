import os

from dotenv import load_dotenv
from groq import Groq
from prompts import SYSTEM_PROMPT

import time
import math

from groq import Groq, RateLimitError, BadRequestError

load_dotenv()


def make_tool(name, description, properties=None, required=None):
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": properties or {},
                "required": required or [],
                "additionalProperties": False
            }
        }
    }


TOOL_DEFINITIONS = [
    make_tool(
        "list_files",
        "List tracked repository files. This function takes no arguments. Use an empty object {}."
    ),

    make_tool(
        "read_file",
        "Read a repository file to inspect code or configuration.",
        {
            "path": {
                "type": "string",
                "description": "Repository-relative file path"
            }
        },
        ["path"]
    ),

    make_tool(
        "search_code",
        "Search tracked repository files for a literal text pattern.",
        {
            "pattern": {
                "type": "string",
                "description": "Pattern to search for"
            }
        },
        ["pattern"]
    ),

    make_tool(
        "git_log",
        "Inspect recent Git commit history."
    ), 

    make_tool(
        "validate_yaml",
        (
            "Validate the YAML syntax of a repository file. "
            "Use this before reporting YAML syntax or "
            "indentation errors. This tool checks YAML syntax, "
            "not GitHub Actions workflow semantics."
        ),
        {
            "path": {
                "type": "string",
                "description": (
                    "Repository-relative path to a YAML file"
                )
            }
        },
        ["path"]
    )
]


class LLMClient:

    def __init__(self):

        api_key = os.getenv("GROQ_API_KEY")

        if not api_key:
            raise ValueError(
                "GROQ_API_KEY is missing from .env"
            )

        self.client = Groq(
            api_key=api_key,
            timeout=30.0,
            max_retries=0
        )

        self.model = os.getenv(
            "GROQ_MODEL",
            "openai/gpt-oss-20b"
        )

    def _request_with_parsing_retry(
    self,
    request_messages,
    require_tool=False
):
        """
        Retry Groq requests when the model generates
        an invalid tool call.

        Retry at most once with a lower temperature.
        """

        temperatures = [0.2, 0.0]

        for attempt, temperature in enumerate(temperatures):

            try:
                return self.client.chat.completions.create(
                    model=self.model,

                    messages=request_messages,

                    tools=TOOL_DEFINITIONS,

                    tool_choice=(
                        "required" if require_tool else "auto"
                    ),

                    temperature=temperature,

                    reasoning_effort="low",

                    parallel_tool_calls=False
                )

            except BadRequestError as error:

                body = getattr(error, "body", None)

                if not isinstance(body, dict):
                    raise

                details = body.get("error", body)

                if not isinstance(details, dict):
                    raise

                error_code = details.get("code")

                recoverable_errors = {
                    "output_parse_failed",
                    "tool_use_failed"
                }

                # Do not retry unrelated HTTP 400 errors.
                if error_code not in recoverable_errors:
                    raise

                if attempt == len(temperatures) - 1:
                    raise RuntimeError(
                        "Groq could not generate a valid tool "
                        "call after two attempts."
                    ) from None

                print(
                    "[LLM] Invalid tool-call response. "
                    "Retrying with lower temperature..."
                )

    def get_next_action(self, messages, require_tool=False):
        """
        Request the next LLM action.

        Retry temporary rate limits without retrying forever.
        """

        request_messages = [
            {
                "role": "system",
                "content": SYSTEM_PROMPT
            },
            *messages
        ]

        max_attempts = 4
        max_retry_delay = 60

        for attempt in range(max_attempts):

            try:
                return self._request_with_parsing_retry(
                    request_messages=request_messages,
                    require_tool=require_tool
                )

            except RateLimitError as error:

                if attempt == max_attempts - 1:
                    raise RuntimeError(
                        "Groq rate limit exceeded after "
                        "multiple attempts."
                    ) from error

                response = getattr(error, "response", None)

                retry_after = (
                    response.headers.get("retry-after")
                    if response is not None
                    else None
                )

                if retry_after is not None:
                    try:
                        delay = float(retry_after)
                    except ValueError:
                        delay = 2 ** attempt
                else:
                    delay = 2 ** attempt

                if not math.isfinite(delay) or delay < 0:
                    raise RuntimeError(
                        "Invalid API retry delay."
                    ) from error

                if delay > max_retry_delay:
                    raise RuntimeError(
                        "Groq rate limit requires a longer wait. "
                        "Retry the audit after your quota resets."
                    ) from error

                print(
                    "[LLM] Temporary rate limit detected. "
                    "Retrying the request."
                )

                time.sleep(delay)