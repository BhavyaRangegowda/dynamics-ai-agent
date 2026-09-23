"""
add_stories.py — One-time script to add all D365 Sales stories to Jira.
Run once: python add_stories.py
"""
import logging
import os
from dotenv import load_dotenv
from jira import JIRA

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
logger = logging.getLogger(__name__)

JIRA_URL = os.getenv("JIRA_URL")
JIRA_EMAIL = os.getenv("JIRA_EMAIL")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")
PROJECT_KEY = os.getenv("PROJECT_KEY")

# ─── All stories to create ────────────────────────────────────────────────────
STORIES = [
    # ── Core Sales workflows ──────────────────────────────────────────────────
    {
        "summary": "As a sales user I want to qualify a lead to create an opportunity in Dynamics 365",
        "description": "When a lead is qualified, D365 should automatically create an opportunity, account and contact linked to that lead.",
        "labels": ["Sales", "Lead", "Opportunity"]
    },
    {
        "summary": "As a sales user I want to add a note to an existing lead in Dynamics 365",
        "description": "User should be able to open a lead record and add a timeline note with text content.",
        "labels": ["Sales", "Lead", "Notes"]
    },
    {
        "summary": "As a sales user I want to create a new account in Dynamics 365",
        "description": "User should be able to navigate to Accounts, click New, fill in account name and save successfully.",
        "labels": ["Sales", "Account"]
    },
    {
        "summary": "As a sales user I want to view the list of existing contacts in Dynamics 365",
        "description": "User should be able to navigate to the Contacts entity list and see all existing contacts.",
        "labels": ["Sales", "Contact"]
    },
    {
        "summary": "As a sales user I want to view all open opportunities in Dynamics 365",
        "description": "User should be able to navigate to Opportunities and see a list of open opportunities with their details.",
        "labels": ["Sales", "Opportunity"]
    },
    {
        "summary": "As a sales user I want to create a new task for a lead follow up in Dynamics 365",
        "description": "User should be able to create a task activity linked to a lead record with subject, due date and description.",
        "labels": ["Sales", "Task", "Activity"]
    },
    {
        "summary": "As a sales user I want to search for a contact by name in Dynamics 365",
        "description": "User should be able to use the search/filter functionality in the Contacts list to find a contact by name.",
        "labels": ["Sales", "Contact", "Search"]
    },
    {
        "summary": "As a sales user I want to update an existing contact phone number in Dynamics 365",
        "description": "User should be able to open an existing contact record, update the business phone number field and save.",
        "labels": ["Sales", "Contact", "Update"]
    },
    {
        "summary": "As a sales user I want to view the details of an existing opportunity in Dynamics 365",
        "description": "User should be able to open an opportunity record and view all details including estimated revenue, close date and stage.",
        "labels": ["Sales", "Opportunity"]
    },
    {
        "summary": "As a sales user I want to close an opportunity as won in Dynamics 365",
        "description": "User should be able to open an opportunity and use the Close as Won action to mark it complete.",
        "labels": ["Sales", "Opportunity", "Close"]
    },
    # ── Edge cases — intentional failures for different reasons ───────────────
    {
        "summary": "As a sales user I want to create a lead without required fields in Dynamics 365",
        "description": "EDGE CASE: Attempt to save a lead form without filling in required fields. Expected: validation error displayed.",
        "labels": ["EdgeCase", "Validation", "NegativeTest"]
    },
    {
        "summary": "As a sales user I want to filter leads by status New in Dynamics 365",
        "description": "User should be able to apply a filter on the Leads list to show only leads with status New.",
        "labels": ["Sales", "Lead", "Filter"]
    },
    {
        "summary": "As a sales user I want to export the leads list to Excel from Dynamics 365",
        "description": "User should be able to use the Export to Excel option from the Leads list view.",
        "labels": ["Sales", "Lead", "Export"]
    },
    {
        "summary": "As a sales user I want to assign a lead to a team member in Dynamics 365",
        "description": "User should be able to open a lead record and use the Assign action to reassign ownership to another user.",
        "labels": ["Sales", "Lead", "Assign"]
    },
    {
        "summary": "As a sales user I want to delete an existing lead in Dynamics 365",
        "description": "User should be able to select a lead from the list and delete it using the Delete button.",
        "labels": ["Sales", "Lead", "Delete"]
    },
    # ── Invalid/Skip stories — to test SKIP detection ─────────────────────────
    {
        "summary": "Update the system database configuration",
        "description": "INVALID: This is not a D365 Sales story — should be detected and skipped by the AI agent.",
        "labels": ["Invalid", "SkipTest"]
    },
    {
        "summary": "Fix the bug in production",
        "description": "INVALID: Placeholder story — should be detected and skipped.",
        "labels": ["Invalid", "SkipTest"]
    },
]


def main():
    logger.info("Connecting to Jira: %s", JIRA_URL)
    jira = JIRA(server=JIRA_URL, basic_auth=(JIRA_EMAIL, JIRA_API_TOKEN))

    logger.info("Creating %d stories in project %s...", len(STORIES), PROJECT_KEY)
    created = []
    failed = []

    for i, story in enumerate(STORIES, 1):
        try:
            issue = jira.create_issue(
                project=PROJECT_KEY,
                summary=story["summary"],
                description=story.get("description", ""),
                issuetype={"name": "Story"},
                labels=story.get("labels", []),
            )
            created.append(issue.key)
            logger.info("[%d/%d] Created %s: %s", i, len(STORIES), issue.key, story["summary"][:60])
        except Exception as e:
            failed.append(story["summary"][:60])
            logger.error("[%d/%d] FAILED: %s — %s", i, len(STORIES), story["summary"][:60], e)

    print("\n" + "=" * 60)
    print(f"Created: {len(created)} stories: {', '.join(created)}")
    if failed:
        print(f"Failed:  {len(failed)} stories")
        for f in failed:
            print(f"  - {f}")
    print("=" * 60)


if __name__ == "__main__":
    main()