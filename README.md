# Muban CLI

A robust command-line interface for the **Muban Document Generation Service**. Manage JasperReports templates and generate documents directly from your terminal.

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)

## Features

- **Secure Authentication** - JWT token-based auth with password or OAuth2 client credentials flow
- **Template Management** - List, upload, download, and delete templates
- **Document Generation** - Generate PDF, XLSX, DOCX, RTF, and HTML documents
- **Async Processing** - Submit bulk document generation jobs and monitor progress
- **Search & Filter** - Search templates and filter audit logs
- **Audit & Monitoring** - Access audit logs and security dashboards (admin)
- **Automation Ready** - Perfect for CI/CD pipelines with service account support
- **Cross-Platform** - Works on Windows, macOS, and Linux

## Installation

### From PyPI (Recommended)

```bash
pip install muban-cli
```

### From Source

```bash
git clone https://github.com/muban/muban-cli.git
cd muban-cli
pip install -e .
```

### Development Installation

```bash
pip install -e ".[dev]"
```

## Quick Start

### 1. Configure the Server

```bash
# Interactive setup
muban configure

# Or with command-line options
muban configure --server https://api.muban.me
```

### 2. Login with Your Credentials

```bash
# Interactive login (prompts for username/password)
muban login

# Or with command-line options
muban login --username your@email.com
```

### 3. List Available Templates

```bash
muban list
```

### 4. Generate a Document

```bash
muban generate TEMPLATE_ID -p title="Monthly Report" -p date="2025-01-08"
```

## Configuration

### Configuration File

Configuration is stored in `~/.muban/config.json`. JWT tokens are stored separately in `~/.muban/credentials.json` with restricted permissions.

### Environment Variables

| Variable | Description |
| -------- | ----------- |
| `MUBAN_TOKEN` | JWT Bearer token (obtained via `muban login`) |
| `MUBAN_SERVER_URL` | API server URL (default: <https://api.muban.me>) |
| `MUBAN_AUTH_SERVER_URL` | OAuth2/IdP token endpoint (if different from API server) |
| `MUBAN_CLIENT_ID` | OAuth2 Client ID (for client credentials flow) |
| `MUBAN_CLIENT_SECRET` | OAuth2 Client Secret (for client credentials flow) |
| `MUBAN_TIMEOUT` | Request timeout in seconds |
| `MUBAN_VERIFY_SSL` | Enable/disable SSL verification |
| `MUBAN_CONFIG_DIR` | Custom configuration directory |

Environment variables take precedence over configuration files.

## Commands Reference

### Authentication

```bash
# Login with credentials (interactive)
muban login

# Login with username provided
muban login --username admin@example.com

# Login with custom server
muban login --server https://api.muban.me

# Login with OAuth2 Client Credentials (for CI/CD / service accounts)
muban login --client-credentials
muban login -c --client-id my-client --client-secret secret123

# Login with external IdP (ADFS, Azure AD, Keycloak)
muban login -c --auth-server https://adfs.company.com/adfs/oauth2/token

# Skip SSL verification (development only)
muban login --no-verify-ssl

# Check authentication status (shows token expiry)
muban whoami

# Manually refresh access token
muban refresh

# Logout (clear all tokens)
muban logout
```

**Token Refresh:**

- If the server provides a refresh token, it's automatically stored
- The CLI automatically refreshes expired tokens when making API requests
- Use `muban refresh` to manually refresh before expiration
- Use `muban whoami` to see token expiration time

### Configuration Commands

```bash
# Interactive configuration
muban configure

# Set server URL
muban configure --server https://api.muban.me

# Set auth server (if different from API server)
muban configure --auth-server https://auth.muban.me

# Show current configuration
muban configure --show

# Clear all configuration
muban config-clear
```

### Template Management

```bash
# List all templates
muban list
muban list --search "invoice" --format json
muban list --page 2 --size 50

# Search templates
muban search "quarterly report"

# Get template details
muban get TEMPLATE_ID
muban get TEMPLATE_ID --params  # Show parameters
muban get TEMPLATE_ID --fields  # Show fields

# Upload a template (ZIP format)
muban push report.zip --name "Monthly Report" --author "John Doe"
muban push invoice.zip -n "Invoice" -a "Finance Team" -m "Standard invoice template"

# Download a template
muban pull TEMPLATE_ID
muban pull TEMPLATE_ID -o ./templates/report.zip

# Delete a template
muban delete TEMPLATE_ID
muban delete TEMPLATE_ID --yes  # Skip confirmation
```

### Document Generation

```bash
# Basic generation
muban generate TEMPLATE_ID -p title="Sales Report"

# Multiple parameters
muban generate TEMPLATE_ID -p title="Report" -p year=2025 -p amount=15750.25

# Different output formats
muban generate TEMPLATE_ID -F xlsx -o report.xlsx
muban generate TEMPLATE_ID -F docx -o report.docx
muban generate TEMPLATE_ID -F html -o report.html

# Using parameter file
muban generate TEMPLATE_ID --params-file params.json

# Using JSON data source
muban generate TEMPLATE_ID --data-file data.json

# PDF options
muban generate TEMPLATE_ID --pdf-pdfa PDF/A-1b --locale pl_PL
muban generate TEMPLATE_ID --pdf-password secret123

# Output options
muban generate TEMPLATE_ID -o ./output/report.pdf --filename "Sales_Report_Q4"
```

**Parameter File Format (params.json):**

```json
{
  "title": "Monthly Sales Report",
  "year": 2025,
  "department": "Finance"
}
```

Or as a list:

```json
[
  {"name": "title", "value": "Monthly Sales Report"},
  {"name": "year", "value": 2025}
]
```

**Data Source File Format (data.json):**

```json
{
  "items": [
    {"productName": "Widget A", "quantity": 100, "unitPrice": 25.50},
    {"productName": "Widget B", "quantity": 50, "unitPrice": 45.00}
  ],
  "summary": {
    "totalItems": 150,
    "totalValue": 4800.00
  }
}
```

### Utility Commands

```bash
# List available fonts
muban fonts

# List ICC color profiles (for PDF export)
muban icc-profiles
```

### Admin Commands

```bash
# Verify template integrity
muban admin verify-integrity TEMPLATE_ID

# Regenerate integrity digest
muban admin regenerate-digest TEMPLATE_ID

# Regenerate all digests
muban admin regenerate-all-digests --yes

# Get server configuration
muban admin server-config
```

### Async Document Generation

```bash
# Submit a single async request
muban async submit -t TEMPLATE_ID -F PDF -p title="Report"
muban async submit -t TEMPLATE_ID -d params.json -c my-correlation-id

# Submit bulk requests from JSON file
muban async bulk requests.json
muban async bulk requests.json --batch-id batch-2026-01-15

# List async requests
muban async list
muban async list --status FAILED --since 1d
muban async list --template TEMPLATE_ID --format json

# Get request details
muban async get REQUEST_ID

# Monitor workers and metrics (admin)
muban async workers
muban async metrics
muban async health

# View error log
muban async errors --since 24h
```

**Bulk Request File Format (requests.json):**

```json
[
  {
    "templateId": "abc123-uuid",
    "format": "PDF",
    "parameters": {"title": "Report 1"},
    "correlationId": "req-001"
  },
  {
    "templateId": "abc123-uuid",
    "format": "XLSX",
    "parameters": {"title": "Report 2"}
  }
]
```

### Audit Commands

```bash
# View audit logs
muban audit logs
muban audit logs --severity HIGH --since 1d
muban audit logs --event-type LOGIN_FAILURE --format json

# Get audit statistics
muban audit statistics --since 7d

# View security events
muban audit security --since 24h

# Dashboard and monitoring
muban audit dashboard
muban audit threats
muban audit health

# List available event types
muban audit event-types

# Trigger cleanup
muban audit cleanup --yes
```

### Common Options

All commands support these options:

| Option      | Short | Description                   |
|-------------|-------|-------------------------------|
| `--verbose` | `-v`  | Enable verbose output         |
| `--quiet`   | `-q`  | Suppress non-essential output |
| `--format`  | `-f`  | Output format (table, json)   |
| `--help`    |       | Show help message             |

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Deploy Report Template

on:
  push:
    branches: [main]
    paths:
      - 'templates/**'

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.9'
      
      - name: Install Muban CLI
        run: pip install muban-cli
      
      - name: Deploy Template
        env:
          MUBAN_SERVER_URL: https://api.muban.me
          MUBAN_CLIENT_ID: ${{ secrets.MUBAN_CLIENT_ID }}
          MUBAN_CLIENT_SECRET: ${{ secrets.MUBAN_CLIENT_SECRET }}
        run: |
          muban login --client-credentials
          cd templates
          zip -r report.zip ./monthly_report/
          muban push report.zip --name "Monthly Report" --author "CI/CD"
```

### GitLab CI Example

```yaml
deploy_template:
  image: python:3.9-slim
  stage: deploy
  only:
    changes:
      - templates/**
  script:
    - pip install muban-cli
    - muban login --client-credentials
    - cd templates && zip -r report.zip ./monthly_report/
    - muban push report.zip --name "Monthly Report" --author "GitLab CI"
  variables:
    MUBAN_SERVER_URL: https://api.muban.me
    MUBAN_CLIENT_ID: $MUBAN_CLIENT_ID
    MUBAN_CLIENT_SECRET: $MUBAN_CLIENT_SECRET
```

### Shell Script Example

```bash
#!/bin/bash
# deploy-template.sh

set -e

TEMPLATE_DIR="./my_jasper_project"
TEMPLATE_NAME="Monthly Sales Report"
AUTHOR="Deploy Script"

# Create ZIP archive
zip -r template.zip "$TEMPLATE_DIR"

# Upload to Muban
muban push template.zip \
  --name "$TEMPLATE_NAME" \
  --author "$AUTHOR" \
  --metadata "Deployed from commit ${GIT_COMMIT:-unknown}"

# Cleanup
rm template.zip

echo "Template deployed successfully!"
```

## Error Handling

The CLI provides detailed error messages and appropriate exit codes:

| Exit Code | Meaning |
| --------- | ------- |
| 0 | Success |
| 1 | General error |
| 130 | Interrupted (Ctrl+C) |

### Common Errors

```bash
# Not configured
$ muban list
✗ Muban CLI is not configured.
  Run 'muban configure' to set up your server, then 'muban login'.

# Not authenticated
$ muban list
✗ Not authenticated. Run 'muban login' to sign in.

# Template not found
$ muban get invalid-id
✗ Template not found: invalid-id

# Permission denied
$ muban delete some-template
✗ Permission denied. Manager role required.
```

## Development

### Running Tests

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run with coverage
pytest --cov=muban_cli --cov-report=html
```

### Code Quality

```bash
# Format code
black muban_cli
isort muban_cli

# Type checking
mypy muban_cli

# Linting
flake8 muban_cli
```

### Project Structure

```text
muban-cli/
├── muban_cli/
│   ├── __init__.py      # Package initialization
│   ├── cli.py           # Main CLI entry point
│   ├── api.py           # REST API client
│   ├── auth.py          # Authentication (password + OAuth2)
│   ├── config.py        # Configuration management
│   ├── utils.py         # Utility functions
│   ├── exceptions.py    # Custom exceptions
│   ├── py.typed         # PEP 561 marker
│   └── commands/        # Command modules
│       ├── auth.py      # login, logout, whoami, refresh
│       ├── templates.py # list, get, push, pull, delete
│       ├── generate.py  # generate documents
│       ├── async_ops.py # async job management
│       ├── audit.py     # audit logs and monitoring
│       ├── admin.py     # admin operations
│       └── users.py     # user management
├── tests/               # Test suite
├── pyproject.toml       # Project configuration
└── README.md            # Documentation
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

- Email: <contact@muban.me>
- Documentation: <https://muban.me/features.html>

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request
