# Muban CLI Toolkit Concept

## Considerations

### Why a Python CLI is the Right Choice

* **Portability**: Runs on Windows, macOS, and Linux, which covers all Jaspersoft Studio environments.
* **Automation-Friendly**: Can be called from shell scripts, Git hooks, and any CI/CD pipeline (GitHub Actions, GitLab CI, Jenkins).
* **Developer-Centric**: Familiar and easy to distribute (`pip install muban-cli`).

### Core Design for Your CLI Tool

Here’s a suggested structure and key commands for your `muban-cli` tool:

**1. Authentication & Configuration**
Users should authenticate once, and the CLI should store credentials securely.

```bash
# Example setup flow
muban configure --api-key "YOUR_MUBAN_API_KEY" --server "https://api.muban.me"
```

**2. Essential Commands**
Your CLI would map directly to your API's core functions:

| Command | Purpose | Example |
| :--- | :--- | :--- |
| `muban push <report.zip>` | Upload/update a template. | `muban push my_report.zip --category finance` |
| `muban list` | List all templates on the server. | `muban list --format json` |
| `muban pull <template_id>` | Download a template package. | `muban pull tpl_12345 -o ./report/` |
| `muban search <query>` | Search template names/descriptions. | `muban search "quarterly sales"` |
| `muban delete <template_id>` | Remove a template. | `muban delete tpl_12345` |

**3. Advanced CI/CD Integration**
The real power is in scripting. A user's Git hook or CI/CD pipeline script could be as simple as:

```bash
#!/bin/bash
# A post-merge Git hook or CI/CD script
zip -r my_report.zip ./my_jasper_project/
muban push my_report.zip --message "Deployed from commit ${CI_COMMIT_SHA}"
```

### Implementation Blueprint

Here is a conceptual structure for your Python project to get you started:

```text
muban-cli/
├── muban_cli/
│   ├── __init__.py
│   ├── cli.py           # Main Click/Typer command definitions
│   ├── api.py           # Client for your Muban REST API
│   ├── auth.py          # Handles API key storage (use keyring lib)
│   └── utils.py         # Helpers for ZIP, config, etc.
├── pyproject.toml       # Project metadata and dependencies
├── README.md            # Docs with setup and CI/CD examples
└── tests/
```

**Recommended Python Stack:**

* **CLI Framework**: **Typer** (built on Click) is modern and makes creating elegant CLIs very easy.
* **HTTP Client**: **`httpx`** or **`requests`** for calling your API.
* **Configuration**: Use **`pydantic`** with **`python-dotenv`** to manage settings in a `.mubanrc` file or environment variables.
* **Distribution**: Package with **`setuptools`** or **`poetry`** and publish to **PyPI** so users can simply `pip install muban-cli`.

### Key Considerations for a Robust CLI

1. **Idempotent Operations**: Ensure `muban push` is safe to run multiple times (e.g., by using a unique template identifier from the `.jrxml` file).
2. **Detailed Logging & Verbose Mode**: Crucial for debugging in automated pipelines.
3. **Non-Interactive Mode**: Support a `--yes` flag or rely on environment variables for fully automated runs in CI/CD.
4. **Comprehensive Error Handling**: Return meaningful, actionable error codes for scripts to react to.

This CLI-centric approach puts you on a path where:

* **End-users** get a simple tool for manual template management.
* **Corporations** get a scriptable component that slots perfectly into their approved Git/CI/CD workflows.
* **You** maintain a single, clean codebase (the CLI and its backing API) instead of complex, client-specific integrations.

Would you like a more detailed sketch of the `api.py` client class or an example `pyproject.toml` file to kickstart development?
