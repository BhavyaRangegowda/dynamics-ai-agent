import json
import logging

from jira import JIRA

from config import JIRA_URL, JIRA_EMAIL, JIRA_API_TOKEN, PROJECT_KEY, JIRA_MAX_RESULTS

logger = logging.getLogger(__name__)


def create_jira_client():
    """Create and return an authenticated Jira client."""
    return JIRA(
        server=JIRA_URL,
        basic_auth=(JIRA_EMAIL, JIRA_API_TOKEN)
    )


def fetch_user_stories(jira_client):
    """Fetch user stories from Jira for the configured project.

    Logs a warning if results may have been truncated by maxResults.
    """
    try:
        issues = jira_client.search_issues(
            f"project={PROJECT_KEY} ORDER BY created ASC",
            maxResults=JIRA_MAX_RESULTS
        )
    except Exception as e:
        logger.error("Failed to fetch user stories from Jira: %s", e)
        return []

    if len(issues) == JIRA_MAX_RESULTS:
        logger.warning(
            "Fetched exactly %d issues — there may be more. "
            "Increase JIRA_MAX_RESULTS in .env if needed.",
            JIRA_MAX_RESULTS
        )

    logger.info("Fetched %d user stories from Jira project %s", len(issues), PROJECT_KEY)
    return issues


def post_result_to_jira(jira_client, issue_key, test_cases, ai_plan, test_status, screenshot_path):
    """Post test results as a comment on the given Jira issue.

    Logs an error and continues if the comment cannot be posted.
    """
    comment = (
        f"*AI Generated Test Cases:*\n\n"
        f"{test_cases}\n\n"
        f"*AI Selected Workflow:*\n"
        f"{{code:json}}\n{json.dumps(ai_plan, indent=2)}\n{{code}}\n\n"
        f"*Test Execution Status:* {test_status}\n\n"
        f"*Screenshot Evidence Path:* {screenshot_path}"
    )

    try:
        jira_client.add_comment(issue_key, comment)
        logger.info("Posted result to Jira issue %s", issue_key)
    except Exception as e:
        logger.error("Failed to post comment to Jira issue %s: %s", issue_key, e)
