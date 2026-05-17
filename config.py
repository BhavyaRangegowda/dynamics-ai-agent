import os
from dotenv import load_dotenv

load_dotenv()

# =====================================================================
# JIRA Configuration
# =====================================================================
JIRA_URL = os.getenv("JIRA_URL")
JIRA_EMAIL = os.getenv("JIRA_EMAIL")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")
PROJECT_KEY = os.getenv("PROJECT_KEY")
JIRA_MAX_RESULTS = int(os.getenv("JIRA_MAX_RESULTS", "50"))

# =====================================================================
# Groq AI Configuration
# =====================================================================
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

# =====================================================================
# Dynamics 365 Configuration
# =====================================================================
DYNAMICS_URL = os.getenv("DYNAMICS_URL")
DYNAMICS_USERNAME = os.getenv("DYNAMICS_USERNAME")
DYNAMICS_PASSWORD = os.getenv("DYNAMICS_PASSWORD")

# =====================================================================
# Selenium & Screenshots
# =====================================================================
SCREENSHOT_DIR = os.getenv("SCREENSHOT_DIR", "screenshots")
MFA_WAIT_SECONDS = int(os.getenv("MFA_WAIT_SECONDS", "30"))
TEST_DATA_PREFIX = os.getenv("TEST_DATA_PREFIX", "AI_Test")

# =====================================================================
# Email Configuration (Outlook/Office 365)
# =====================================================================
EMAIL_SENDER = os.getenv("EMAIL_SENDER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
EMAIL_RECIPIENTS = os.getenv("EMAIL_RECIPIENTS", "")
EMAIL_SMTP_HOST = os.getenv("EMAIL_SMTP_HOST", "smtp.office365.com")
EMAIL_SMTP_PORT = int(os.getenv("EMAIL_SMTP_PORT", "587"))

# =====================================================================
# Zephyr Scale Configuration (optional)
# =====================================================================
ZEPHYR_ENABLED = os.getenv("ZEPHYR_ENABLED", "false").lower() == "true"
ZEPHYR_API_TOKEN = os.getenv("ZEPHYR_API_TOKEN", "")

# =====================================================================

# =====================================================================
# Test Data Defaults
# =====================================================================
TEST_EMAIL_DOMAIN = os.getenv("TEST_EMAIL_DOMAIN", "testcorp.com")
TEST_LEAD_PREFIX = os.getenv("TEST_LEAD_PREFIX", "AI_Lead")
TEST_CONTACT_PREFIX = os.getenv("TEST_CONTACT_PREFIX", "AI_Contact")
TEST_COMPANY_PREFIX = os.getenv("TEST_COMPANY_PREFIX", "AI_Testing_Corp")

# Startup Validation
# =====================================================================
_required_keys = [
    "JIRA_URL",
    "JIRA_EMAIL",
    "JIRA_API_TOKEN",
    "PROJECT_KEY",
    "GROQ_API_KEY",
    "DYNAMICS_URL",
    "DYNAMICS_USERNAME",
    "DYNAMICS_PASSWORD",
    "EMAIL_SENDER",
    "EMAIL_PASSWORD",
    "EMAIL_RECIPIENTS",
]

_missing = [key for key in _required_keys if not os.getenv(key)]
if _missing:
    raise EnvironmentError(
        f"Missing required environment variables: {', '.join(_missing)}\n"
        f"Please check your .env file."
    )