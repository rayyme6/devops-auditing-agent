
# AI-Powered DevOps Repository Auditing Agent

An autonomous AI-powered DevOps auditing agent that investigates public GitHub repositories, identifies potential DevOps best-practice violations, and generates structured JSON reports containing evidence, severity levels, and actionable recommendations.

The system uses **GroqCloud with the `openai/gpt-oss-20b` model** for LLM-directed repository investigation.

## 1. Project Overview

The DevOps Auditing Agent is a Python application designed to evaluate repositories for potential issues involving security, CI/CD configuration, testing, dependency management, repository hygiene, and other DevOps practices.

Unlike a traditional scanner that follows only predefined rules, this system allows a large language model to dynamically select inspection tools based on information discovered during the investigation.

The agent performs read-only repository inspection and generates an evidence-based JSON report.

### Key Features

- Autonomous LLM-directed repository investigation
- Public GitHub repository cloning
- Five repository inspection tools
- DevOps best-practice analysis
- YAML syntax validation
- GitHub Actions permissions verification
- Basic credential redaction
- Structured JSON reporting
- Severity classification and recommendations
- Rate-limit handling and malformed-response recovery
- Automated testing using pytest

## 2. Technology Stack

| Technology    | Purpose                                   |
| ------------- | ----------------------------------------- |
| Python 3.10+  | Application development                   |
| GroqCloud API | LLM inference                             |
| GPT-OSS 20B   | Autonomous investigation and reasoning    |
| Git           | Repository cloning and history inspection |
| PyYAML        | YAML syntax verification                  |
| python-dotenv | Environment configuration                 |
| pytest        | Automated testing                         |
| JSON          | Structured audit reports                  |

## 3. System Architecture

The application follows an autonomous tool-calling architecture.

```text
GitHub Repository URL
         |
         v
Repository Cloning
         |
         v
Temporary Local Repository
         |
         v
Autonomous DevOps Agent
         |
         v
       Groq LLM
         |
         v
Dynamic Tool Selection
         |
         +---- list_files()
         |
         +---- read_file()
         |
         +---- search_code()
         |
         +---- git_log()
         |
         +---- validate_yaml()
         |
         v
Python Tool Execution
         |
         v
Results Returned to LLM
         |
         v
Further Investigation
         |
         v
DevOps Findings
         |
         v
Report Validation
         |
         v
     report.json
```

The LLM chooses which tools to use. Python validates tool arguments, executes the permitted operations, and returns their results to the LLM.

The investigation continues until the model produces its final findings or the maximum investigation limit is reached.

## 4. Repository Inspection Tools

The application provides five inspection tools.

### list_files()

Lists tracked files in a repository.

The agent uses this tool to understand the repository structure and identify potentially relevant configuration files.

### read_file(path)

Reads the contents of a repository file with line numbers.

Includes file-path validation, file-size restrictions, and basic credential redaction.

### search_code(pattern)

Searches tracked repository files for a literal text pattern.

Returns matching file paths, line numbers, and redacted snippets.

### git_log()

Retrieves recent Git commit history.

This allows the agent to inspect commit messages and understand recent repository activity.

### validate_yaml(path)

Checks whether a YAML file contains syntax errors.

This tool helps prevent incorrect claims about malformed YAML or invalid indentation.

It checks general YAML syntax, not complete GitHub Actions workflow semantics.

## 5. DevOps Auditing Categories

The agent is instructed to investigate nine categories:

1. Repository hygiene
2. Dependency management
3. Code quality
4. Testing practices
5. GitHub Actions and CI/CD
6. Security
7. Configuration management
8. Collaboration practices
9. Build and release processes

Findings must be supported by inspection evidence.

The absence of an optional file or tool does not automatically represent a violation.

## 6. Installation

### Prerequisites

Ensure the following are installed:

- Python 3.10 or newer
- Git
- pip
- Internet connectivity
- A GroqCloud API key

### Clone the Project

```bash
git clone https://github.com/rayyme6/devops-auditing-agent.git
```

Navigate into the directory:

```bash
cd devops-auditing-agent
```

### Create a Virtual Environment

```bash
python3 -m venv venv
```

Activate it on Linux or macOS:

```bash
source venv/bin/activate
```

### Install Dependencies

```bash
python3 -m pip install -r requirements.txt
```

## 7. Groq API Configuration

Create an API key through GroqCloud.

Copy the example environment file:

```bash
cp .env.example .env
```

Open `.env` and configure:

```env
GROQ_API_KEY=your_actual_groq_api_key
GROQ_MODEL=openai/gpt-oss-20b
```

Replace the placeholder with your own API key.

**Security warning:** Never commit `.env` or expose API credentials in source code, screenshots, or reports.

The application uses the Groq API, which is subject to model availability and usage limits.

## 8. Running the Application

The application is executed through `agent.py`.

### Command Syntax

```bash
python3 agent.py --repo <github_repository_url> --output <report_file>
```

### Example

```bash
python3 agent.py --repo https://github.com/octocat/Hello-World --output report.json
```

The application automatically:

1. Validates the supplied repository URL.
2. Clones the public GitHub repository.
3. Initializes the Groq-powered auditing agent.
4. Begins autonomous repository inspection.
5. Executes LLM-selected inspection tools.
6. Generates preliminary DevOps findings.
7. Validates the report structure and selected evidence.
8. Saves the JSON report.
9. Removes the temporary repository.

The investigation does not require interactive questions or manual selection of inspection tools.

### Command-Line Arguments

| Argument     | Description                               |
| ------------ | ----------------------------------------- |
| `--repo`   | Public GitHub repository URL              |
| `--output` | Destination for the generated JSON report |
| `--help`   | Displays command-line help                |

## 9. JSON Report Format

The application generates a structured JSON report.

Each reported violation contains:

- `rule_id`
- `category`
- `severity`
- `file`
- `line`
- `description`
- `evidence`
- `recommendation`

### Example Finding

The following is an illustrative finding from a deliberately misconfigured test workflow:

```json
{
  "repository": "https://github.com/example/demo",
  "violations": [
    {
      "rule_id": "SEC-001",
      "category": "security",
      "severity": "high",
      "file": ".github/workflows/ci.yml",
      "line": 6,
      "description": "Excessive workflow permissions",
      "evidence": "The workflow requests write-all permissions.",
      "recommendation": "Grant only the permissions required by the workflow."
    }
  ]
}
```

This example is not a claim about the illustrative repository URL.

### Severity Levels

| Severity | Meaning                                                      |
| -------- | ------------------------------------------------------------ |
| Critical | Confirmed issue with exceptionally serious consequences      |
| High     | Serious security or DevOps weakness                          |
| Medium   | Significant configuration, testing, or maintainability issue |
| Low      | Minor hygiene or documentation issue                         |

### No Violations Found

If the investigation identifies no supported violations, the report may contain:

```json
{
  "repository": "https://github.com/octocat/Hello-World",
  "violations": []
}
```

An empty violations array is a valid result.

## 10. Automated Testing

The project uses pytest to verify its components.

Run the complete test suite:

```bash
python3 -m pytest tests/ -v
```

Run an individual test module:

```bash
python3 -m pytest tests/test_agent.py -v
```

The automated tests cover:

- Repository inspection functions
- Safe file-path handling
- YAML syntax validation
- LLM tool definitions
- Autonomous tool execution
- Unknown-tool rejection
- CLI behavior
- JSON validation
- Duplicate finding removal
- Selected evidence-verification checks
- Basic credential redaction
- API retry behavior

At the time of documentation, the project had **40 passing automated tests**.

Automated unit-test success does not independently establish detection accuracy on all unseen repositories.

## 11. Manual Evaluation

The repository includes scripts for development and evaluation.

### Misconfigured Repository

```bash
python3 manual_agent.py
```

Creates a temporary repository with deliberately unsafe GitHub Actions permissions.

It is used to evaluate whether the agent can identify genuine configuration concerns.

### Healthy Repository

```bash
python3 manual_healthy.py
```

Creates a small repository containing documentation, tests, a `.gitignore`, and a basic CI workflow.

It is used to evaluate whether the agent avoids unsupported findings.

### LLM Tool Selection

```bash
python3 manual_llm.py
```

Tests whether Groq can select a repository inspection tool.

### Public Repository Evaluation

```bash
python3 agent.py --repo https://github.com/octocat/Hello-World --output report.json
```

Runs the complete CLI against a public repository.

An authentic report from this evaluation is included in `sample_report.json`.

## 12. Security and Reliability

The application includes several defensive measures:

- Restricts repository cloning to validated public GitHub URLs
- Uses a whitelist of permitted inspection tools
- Validates LLM-generated tool arguments
- Restricts file access to repository-relative paths
- Limits inspected file sizes
- Avoids executing repository application code
- Applies basic credential redaction
- Uses temporary directories for repository cloning
- Validates JSON report structure and referenced locations
- Independently checks certain YAML and workflow-permission findings
- Implements bounded retries for selected API errors

These safeguards reduce risk but do not provide complete isolation or guaranteed secret protection.

Only public, non-sensitive repositories should be audited unless the inspection environment and data-handling controls have been independently reviewed.

## 13. Known Limitations

- LLM-generated findings may contain false positives or miss genuine issues.
- Only selected types of findings receive independent semantic verification.
- Credential redaction is based on limited patterns and is not comprehensive.
- Large repositories may exceed file, context, or API token limits.
- The agent examines a limited number of tracked files and investigation steps.
- YAML parsing does not fully validate GitHub Actions semantics.
- GitHub-hosted settings, such as branch protection, cannot be established from repository files alone.
- Rate limits or API errors may interrupt an investigation.
- Reports should be reviewed before being used to make security or deployment decisions.

## 14. Project Structure

```text
devops-auditing-agent/
|
|-- agent.py
|-- tools.py
|-- llm.py
|-- prompts.py
|-- report.py
|-- requirements.txt
|-- .env.example
|-- .gitignore
|-- README.md
|-- sample_report.json
|
|-- manual_agent.py
|-- manual_healthy.py
|-- manual_clone.py
|-- manual_llm.py
|
|-- tests/
|   |-- test_agent.py
|   |-- test_cli.py
|   |-- test_llm.py
|   |-- test_prompts.py
|   |-- test_report.py
|   |-- test_tools.py
```

### Main Components

**agent.py:** Autonomous investigation loop and CLI.

**llm.py:** Groq API integration and function-calling definitions.

**tools.py:** Repository cloning and inspection tools.

**prompts.py:** DevOps auditing instructions and evidence requirements.

**report.py:** JSON validation, selected evidence verification, and report generation.

**tests/:** Automated unit tests.

## 15. Future Improvements

Potential future enhancements include:

- More comprehensive credential detection
- Stronger evidence verification across all auditing categories
- Additional CI/CD and deployment configuration validators
- Improved context management for large repositories
- Quantitative precision and recall evaluation
- Additional LLM providers
- Improved logging and audit traceability
- Better handling of repository-specific DevOps practices

## 16. Conclusion

The AI-Powered DevOps Repository Auditing Agent demonstrates how an LLM can dynamically investigate GitHub repositories through controlled Python inspection tools.

The project combines autonomous tool selection, repository analysis, evidence-based reporting, and automated validation into a command-line application.

It is intended as an educational implementation of an AI-assisted DevOps auditing workflow, not as a replacement for professional security auditing or dedicated analysis tools.
