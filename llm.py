import os

from dotenv import load_dotenv
from groq import Groq
from prompts import SYSTEM_PROMPT

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
            max_retries=1
        )

        self.model = os.getenv(
            "GROQ_MODEL",
            "openai/gpt-oss-20b"
        )

    def get_next_action(self, messages, require_tool=False):

        response = self.client.chat.completions.create(
            model=self.model,

            messages=[
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT
                },
                *messages
            ],

            tools=TOOL_DEFINITIONS,

            tool_choice=(
                "required" if require_tool else "auto"
            )
        )

        return response