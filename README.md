# Muban CLI

A robust command-line interface for the **Muban Document Generation Service**. Manage JasperReports templates and generate documents directly from your terminal.

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)

## Features

- **Graphical User Interface** - Optional PyQt6-based GUI for visual template management and document generation
- **Secure Authentication** - JWT token-based auth with password or OAuth2 client credentials flow
- **Template Management** - List, upload, download, and delete templates
- **Template Packaging** - Package JRXML templates with all dependencies (images, subreports) into ZIP
- **Document Generation** - Generate PDF, XLSX, DOCX, RTF, and HTML documents
- **Async Processing** - Submit bulk document generation jobs and monitor progress
- **Search & Filter** - Search templates and filter audit logs
- **Audit & Monitoring** - Access audit logs and security dashboards (admin)
- **Multiple Output Formats** - Table, JSON, and CSV for easy data export
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

### GUI Installation

To use the graphical user interface, install with GUI extras:

```bash
pip install muban-cli[gui]
```

This installs PyQt6 and enables the `muban-gui` command.

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

## Unauthenticated Access

If your Muban API server has authentication disabled (common in development or internal deployments), you can use the CLI without logging in:

```bash
# Configure the server only (no login required)
muban configure --server http://localhost:8080

# Start using the CLI immediately
muban list
muban generate TEMPLATE_ID -p name="Test"
```

The CLI automatically detects when no credentials are configured and sends requests without an `Authorization` header.

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

# Set default author for template uploads
muban configure --author "John Doe"

# Enable auto-upload after packaging
muban configure --auto-upload

# Disable auto-upload
muban configure --no-auto-upload

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
muban list --format csv > templates.csv    # Export to CSV
muban list --page 2 --size 50

# Search templates
muban search "quarterly report"

# Get template details
muban get TEMPLATE_ID
muban get TEMPLATE_ID --params  # Show parameters
muban get TEMPLATE_ID --fields  # Show fields

# Export template details for Excel (CSV unified format)
muban get TEMPLATE_ID --params --fields --format csv > template.csv

# Export as single JSON object with nested parameters/fields
muban get TEMPLATE_ID --params --fields --format json

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

### Template Packaging

The `package` command analyzes a JRXML template file and packages it with all its dependencies (images, subreports) into a ZIP file ready for upload.

```bash
# Package a template (creates template.zip)
muban package template.jrxml

# Specify output path
muban package template.jrxml -o package.zip

# Dry run - analyze without creating ZIP
muban package template.jrxml --dry-run

# Verbose output - show all discovered assets
muban package template.jrxml --dry-run -v

# Custom REPORTS_DIR parameter name
muban package template.jrxml --reports-dir-param TEMPLATE_PATH

# Bundle custom fonts (creates fonts.xml for JasperReports)
muban package template.jrxml \
  --font-file fonts/OpenSans-Regular.ttf --font-name "Open Sans" --font-face normal --embedded \
  --font-file fonts/OpenSans-Bold.ttf --font-name "Open Sans" --font-face bold --embedded

# Multiple font families
muban package template.jrxml \
  --font-file arial.ttf --font-name "Arial Custom" --font-face normal --embedded \
  --font-file times.ttf --font-name "Times Custom" --font-face normal --no-embedded

# Package and upload in one step
muban package template.jrxml --upload

# Package and upload with custom name/author
muban package template.jrxml --upload --name "My Report" --author "John Doe"
```

**Features:**

- **Automatic Asset Discovery** - Parses JRXML to find all referenced images and subreports
- **Recursive Subreport Analysis** - Analyzes subreport `.jrxml` files to include their dependencies
- **Font Bundling** - Include custom fonts with auto-generated `fonts.xml` for JasperReports
- **REPORTS_DIR Resolution** - Respects the `REPORTS_DIR` parameter default value for path resolution
- **Dynamic Directory Support** - Includes all files from directories with dynamic filenames (`$P{DIR} + "path/" + $P{filename}`)
- **URL Skipping** - Automatically skips remote resources (http://, https://, etc.)
- **POSIX Path Handling** - Correctly handles path concatenation (e.g., `"../" + "/img"` → `"../img"`)
- **Auto-Upload** - Optionally upload immediately after packaging with `--upload` flag or enable globally via `muban configure --auto-upload`

**Example Output (verbose mode):**

```text
ℹ Packaging: invoice.jrxml
ℹ Working directory: /projects/templates

Main template:
  invoice.jrxml

Assets found: 8
  ✓ subreports/header.jasper
  ✓ subreports/footer.jasper
  ✓ assets/img/logo.png
  ✓ assets/img/signature.png [from subreports/header.jrxml]
  ✓ assets/img/faksymile/* (dynamic: $P{signatureFile}, 3 files included)
  ✗ assets/img/missing.png (missing)

⚠ Dynamic asset: assets/img/faksymile/* - included all 3 files from directory
⚠ Asset not found: assets/img/missing.png (referenced in invoice.jrxml)

✓ Created: invoice.zip
```

**Typical Workflow:**

```bash
# 1. Package the template
muban package my-report.jrxml -o my-report.zip

# 2. Upload to the server
muban push my-report.zip --name "My Report" --author "Developer"
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
# List available server fonts (default)
muban fonts

# List all fonts including template-bundled ones
muban fonts --show-all

# List ICC color profiles (for PDF export)
muban icc-profiles
```

The `fonts` command shows server-installed fonts by default. Use `--show-all` to include fonts bundled with uploaded templates. When using `--show-all`, a "Source" column indicates whether each font comes from the server or a template.

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
muban async list --format csv > async_jobs.csv    # Export to CSV

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
muban audit logs --format csv > audit_export.csv    # Export to CSV

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

### User Management

```bash
# View your own profile
muban users me

# Update your profile
muban users update-me --email new@email.com --first-name John

# Change your password
muban users change-password

# List all users (admin only)
muban users list
muban users list --search "john" --role ROLE_ADMIN
muban users list --format csv > users.csv

# Get user details (admin only)
muban users get USER_ID

# Create a new user (admin only)
muban users create --username john --email john@example.com --role ROLE_USER

# Update a user (admin only)
muban users update USER_ID --email new@email.com

# Delete a user (admin only)
muban users delete USER_ID --yes

# Manage user roles (admin only)
muban users roles USER_ID --set ROLE_USER ROLE_MANAGER
muban users roles USER_ID --add ROLE_ADMIN

# Enable/disable user accounts (admin only)
muban users enable USER_ID
muban users disable USER_ID

# Set user password (admin only)
muban users set-password USER_ID
```

### Common Options

All commands support these options:

| Option       | Short | Description                                    |
|--------------|-------|------------------------------------------------|
| `--verbose`  | `-v`  | Enable verbose output                          |
| `--quiet`    | `-q`  | Suppress non-essential output                  |
| `--format`   | `-f`  | Output format: `table`, `json`, or `csv`       |
| `--truncate` |       | Max string length in table output (0=no limit) |
| `--help`     |       | Show help message                              |

**Output Format Examples:**

```bash
# Table output (default) - human-readable with colors
muban list

# JSON output - for programmatic parsing
muban list --format json

# CSV output - for Excel/spreadsheet integration
muban list --format csv > templates.csv
muban audit logs --format csv > audit.csv

# Template details with params/fields as unified CSV table
# (columns: Category, Name, Type, Value, Description)
muban get TEMPLATE_ID --params --fields --format csv > template.csv

# Template details as single JSON object with nested arrays
muban get TEMPLATE_ID --params --fields --format json

# Control truncation in table output (default: 50 chars)
muban list --truncate 80          # Longer strings
muban audit logs --truncate 0     # No truncation
```

**CSV Output Notes:**

- All CSV output uses raw numeric values (bytes, milliseconds) for data processing
- No pagination headers or decorative text in CSV output
- The `get` command with `--format csv` outputs a unified table with all template info, parameters, and fields in a single Excel-friendly format

## Graphical User Interface

Muban CLI includes an optional graphical user interface (GUI) for users who prefer a visual approach to template management and document generation.

### Launching the GUI

```bash
muban-gui
```

### GUI Features

The GUI provides a tabbed interface with the following sections:

#### **📦 Package Tab**

- Package JRXML template files with all dependencies (images, subreports)
- Visual asset discovery and preview
- Font bundling configuration
- Dry-run mode to preview package contents
- Auto-upload to server after packaging (when enabled in Settings)

#### **📄 Templates Tab**

- Browse all templates on the server with pagination
- Search and filter templates
- View template details, parameters, and fields
- Upload new templates (ZIP format)
- Download templates to local filesystem
- Delete templates with confirmation

#### **⚙️ Generate Tab**

- Select template and output format (PDF, XLSX, DOCX, RTF, HTML)
- Fill in template parameters with a dynamic form
- Load parameters from JSON file
- Provide JSON data sources
- Configure export options:
  - **PDF options**: PDF/A compliance, embedded ICC profiles, password protection, permission settings
  - **HTML options**: Resource embedding, single-file output, custom CSS
- Save generated documents to local filesystem

#### **🖥️ Server Info Tab**

- View server configuration and status
- List available fonts (server and template-bundled)
- List available ICC color profiles
- Check API connectivity and version

#### **⚙️ Settings Tab**

- Configure server URL
- Set authentication credentials
- Manage OAuth2 client credentials
- Set default author for template uploads
- Enable/disable auto-upload after packaging
- Test connection to server

### GUI Requirements

- Python 3.9+
- PyQt6 6.5.0 or later
- Configured Muban server (via CLI or Settings tab)

The GUI shares configuration with the CLI, so if you've already configured the CLI with `muban configure` and `muban login`, the GUI will use those settings automatically.

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
│   ├── __init__.py      # Package initialization, version info
│   ├── __main__.py      # Entry point for python -m muban_cli
│   ├── cli.py           # Main CLI entry point
│   ├── api.py           # REST API client
│   ├── auth.py          # Authentication (password + OAuth2)
│   ├── config.py        # Configuration management
│   ├── utils.py         # Utility functions (formatting, output)
│   ├── exceptions.py    # Custom exceptions
│   ├── py.typed         # PEP 561 marker
│   ├── commands/        # Command modules
│   │   ├── __init__.py  # Common options decorator
│   │   ├── auth.py      # login, logout, whoami, refresh
│   │   ├── templates.py # list, search, get, push, pull, delete
│   │   ├── generate.py  # generate documents
│   │   ├── async_ops.py # async job management
│   │   ├── audit.py     # audit logs and monitoring
│   │   ├── admin.py     # admin operations
│   │   ├── users.py     # user management
│   │   ├── resources.py # fonts, icc-profiles
│   │   └── settings.py  # configure, config-clear
│   └── gui/             # Graphical User Interface (optional)
│       ├── __init__.py
│       ├── main.py      # GUI entry point
│       ├── main_window.py
│       ├── tabs/        # Tab widgets
│       │   ├── package_tab.py
│       │   ├── templates_tab.py
│       │   ├── generate_tab.py
│       │   ├── server_info_tab.py
│       │   └── settings_tab.py
│       ├── dialogs/     # Dialog windows
│       └── resources/   # Icons and images
├── tests/               # Test suite
│   ├── conftest.py      # Test fixtures
│   ├── test_api.py
│   ├── test_auth.py
│   ├── test_cli_simple.py
│   ├── test_commands.py
│   ├── test_config.py
│   ├── test_exceptions.py
│   └── test_utils.py
├── docs/                # Documentation
├── pyproject.toml       # Project configuration
├── LICENSE              # MIT License
└── README.md            # This file
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
