# Dynamics AI Agent

AI-powered Dynamics 365 test automation for Jira user stories.

## Project overview

This repository provides a full workflow to:

- fetch user stories from Jira
- classify testable Dynamics 365 workflows using AI
- execute Selenium-driven automation against Dynamics 365
- analyse failures with AI and create Jira bugs
- generate reports, send email notifications and Slack updates

## Project structure

```
.dockerignore? (optional)
.env                  # environment variables for local execution
README.md
requirements.txt
pyproject.toml       # project metadata and dependencies
config.py             # configuration loader and validation
ai_agent.py           # AI classification, validation and test-case generation
dynamics_workflows.py # Dynamics 365 Selenium workflows + dynamic action engine
jira_service.py       # Jira issue fetch and reporting
email_service.py      # email reporting
slack_service.py      # Slack notifications
failure_analysis_service.py # AI failure classification
story_change_service.py     # detect changed Jira stories across runs
report_generator.py   # HTML report generation
selenium_helpers.py   # Selenium helpers and robust UI wrappers
locators.py           # locator library for reusable selectors
test_orchestrator.py  # main execution entrypoint
zephyr_service.py     # optional Zephyr integration
tests/                # automated regression tests
screenshots/          # automatically saved screenshots from runs
```

## Setup

1. Create and activate a Python virtual environment:

```bash
python -m venv .venv
.\.venv\Scripts\activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Copy `.env.example` or create `.env` with the required values.

## Required environment variables

Set these values in `.env` or your environment:

```text
JIRA_URL
JIRA_EMAIL
JIRA_API_TOKEN
PROJECT_KEY
GROQ_API_KEY
DYNAMICS_URL
DYNAMICS_USERNAME
DYNAMICS_PASSWORD
EMAIL_SENDER
EMAIL_PASSWORD
EMAIL_RECIPIENTS
```

Optional variables:

```text
SLACK_WEBHOOK_URL
GROQ_MODEL
SCREENSHOT_DIR
MFA_WAIT_SECONDS
TEST_DATA_PREFIX
EMAIL_SMTP_HOST
EMAIL_SMTP_PORT
ZEPHYR_ENABLED
ZEPHYR_API_TOKEN
STORY_HASH_FILE
TEST_EMAIL_DOMAIN
TEST_LEAD_PREFIX
TEST_CONTACT_PREFIX
TEST_COMPANY_PREFIX
```

## Running the agent

Use the main orchestrator script:

```bash
python test_orchestrator.py
```

This will:

- log into Dynamics 365
- fetch stories from Jira
- decide the workflow for each story
- execute automation steps
- save `test_results.json` and `test_report.html`
- send notifications via email and Slack

## Testing

Run the regression tests with:

```bash
python -m unittest discover -s tests
```

## Recommended project enhancements

- convert the repo into a proper package with `src/` layout
- add `pytest` and CI pipeline validation for package installs
- add a `.env.example` file for onboarding
- expand test coverage for workflows and Selenium helpers
- add a CLI wrapper for environment selection and dry-run mode

## Notes

- `screenshots/` is used to store evidence from each run.
- `story_hashes.json` persists Jira story checksums for change detection.
- AI step generation is intentionally separated from the pre-built workflow engine.
