# Muban CLI Toolkit Concept

## Overview

Muban CLI is a Python-based command-line interface for managing Jaspersoft report templates through the Muban API.

## Design Rationale

### Python CLI

* **Portability**: Runs on Windows, macOS, and Linux, covering all Jaspersoft Studio environments.
* **Automation-Friendly**: Callable from shell scripts, Git hooks, and CI/CD pipelines (GitHub Actions, GitLab CI, Jenkins).
* **Developer-Centric**: Distributed via `pip install muban-cli`.

## Core Design

### Authentication & Configuration

Users authenticate once, and the CLI stores credentials securely.

```bash
muban configure --api-key "YOUR_MUBAN_API_KEY" --server "https://api.muban.me"
```

### Commands

The CLI maps directly to the Muban API's core functions:

| Command | Purpose | Example |
| :--- | :--- | :--- |
| `muban push <report.zip>` | Upload/update a template. | `muban push my_report.zip --category finance` |
| `muban list` | List all templates on the server. | `muban list --format json` |
| `muban pull <template_id>` | Download a template package. | `muban pull tpl_12345 -o ./report/` |
| `muban search <query>` | Search template names/descriptions. | `muban search "quarterly sales"` |
| `muban delete <template_id>` | Remove a template. | `muban delete tpl_12345` |

### CI/CD Integration

The CLI integrates with Git hooks and CI/CD pipeline scripts:

```bash
#!/bin/bash
# Post-merge Git hook or CI/CD script
zip -r my_report.zip ./my_jasper_project/
muban push my_report.zip --message "Deployed from commit ${CI_COMMIT_SHA}"
```

## Project Structure

```text
muban-cli/
├── muban_cli/
│   ├── __init__.py
│   ├── cli.py           # Main Click/Typer command definitions
│   ├── api.py           # Client for the Muban REST API
│   ├── auth.py          # Handles API key storage (uses keyring lib)
│   └── utils.py         # Helpers for ZIP, config, etc.
├── pyproject.toml       # Project metadata and dependencies
├── README.md            # Documentation with setup and CI/CD examples
└── tests/
```

## Technology Stack

* **CLI Framework**: Typer (built on Click)
* **HTTP Client**: `httpx` or `requests`
* **Configuration**: `pydantic` with `python-dotenv` for `.mubanrc` files and environment variables
* **Distribution**: Packaged with `setuptools` or `poetry`, published to PyPI

## Design Principles

1. **Idempotent Operations**: `muban push` is safe to run multiple times using unique template identifiers from `.jrxml` files.
2. **Detailed Logging & Verbose Mode**: Supports debugging in automated pipelines.
3. **Non-Interactive Mode**: Supports `--yes` flag and environment variables for fully automated CI/CD runs.
4. **Comprehensive Error Handling**: Returns meaningful, actionable error codes for script integration.

## Target Users

* **End-users**: Simple tool for manual template management.
* **Corporations**: Scriptable component for approved Git/CI/CD workflows.
* **Maintainers**: Single, clean codebase (CLI and backing API) without complex client-specific integrations.
