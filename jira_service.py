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
    """Fetch only Story issues from Jira for the configured project."""
    try:
        issues = jira_client.search_issues(
            f'project={PROJECT_KEY} AND issuetype = Story ORDER BY created ASC',
            maxResults=JIRA_MAX_RESULTS
        )
    except Exception as e:
        logger.error("Failed to fetch user stories from Jira: %s", e)
        return []

    if len(issues) == JIRA_MAX_RESULTS:
        logger.warning(
            "Fetched exactly %d stories — there may be more. "
            "Increase JIRA_MAX_RESULTS in .env if needed.",
            JIRA_MAX_RESULTS
        )

    logger.info(
        "Fetched %d user stories from Jira project %s",
        len(issues),
        PROJECT_KEY
    )
    return issues


def post_result_to_jira(jira_client, issue_key, test_cases, ai_plan, test_status,
                        screenshot_path, failure_analysis=None):
    """Post test results as a comment on the given Jira issue.
    Includes AI failure analysis section if a failure occurred.
    """
    analysis_section = ""
    if failure_analysis:
        from failure_analysis_service import format_analysis_for_jira
        analysis_section = f"\n\n{format_analysis_for_jira(failure_analysis)}"

    comment = (
        f"*[AI Test Agent] Test Execution Result*\n\n"
        f"*Status:* {test_status}\n\n"
        f"*AI Generated Test Cases:*\n\n{test_cases}\n\n"
        f"*AI Selected Workflow:*\n"
        f"{{code:json}}\n{json.dumps(ai_plan, indent=2)}\n{{code}}\n\n"
        f"*Screenshot Evidence:* {screenshot_path}"
        f"{analysis_section}"
    )

    try:
        jira_client.add_comment(issue_key, comment)
        logger.info("Posted result to Jira issue %s", issue_key)
    except Exception as e:
        logger.error("Failed to post comment to Jira issue %s: %s", issue_key, e)


def _link_bug_to_story(jira_client, bug_key, parent_issue_key):
    """Link a generated bug to its source story using an available Jira link type."""
    try:
        link_types = jira_client.issue_link_types()
    except Exception as e:
        logger.warning(
            "Bug %s created, but Jira link types could not be retrieved: %s",
            bug_key, e
        )
        return False

    # Prefer the standard Jira relationship if available, then fall back to
    # another existing non-hierarchical link type. Never invent a link type.
    preferred_names = ("Relates", "Relates to")
    available = {str(link_type.name).strip().lower(): str(link_type.name).strip()
                 for link_type in link_types}

    selected_type = None
    for preferred in preferred_names:
        selected_type = available.get(preferred.lower())
        if selected_type:
            break

    if not selected_type:
        for link_type in link_types:
            name = str(getattr(link_type, "name", "") or "").strip()
            if name:
                selected_type = name
                break

    if not selected_type:
        logger.warning(
            "Bug %s created, but this Jira instance exposes no usable issue-link type.",
            bug_key
        )
        return False

    try:
        jira_client.create_issue_link(
            type=selected_type,
            inwardIssue=bug_key,
            outwardIssue=parent_issue_key,
        )
        logger.info(
            "Linked bug %s to story %s using Jira link type '%s'",
            bug_key, parent_issue_key, selected_type
        )
        return True
    except Exception as e:
        logger.warning(
            "Bug %s created, but linking it to story %s with type '%s' failed: %s",
            bug_key, parent_issue_key, selected_type, e
        )
        return False


def create_jira_bug(jira_client, parent_issue_key, summary, failure_analysis,
                    test_status, screenshot_path):
    """Automatically create a Jira Bug when AI identifies a product bug.

    Returns the created issue key or None if creation failed.
    """
    if not failure_analysis or not failure_analysis.get("create_bug"):
        return None

    bug_summary = f"[AI Detected Bug] {summary[:80]}"

    description = (
        f"*Automatically created by AI Test Agent*\n\n"
        f"*Related Story:* {parent_issue_key}\n"
        f"*Failure Status:* {test_status}\n\n"
        f"*AI Root Cause Analysis:*\n\n"
        f"*Category:* {failure_analysis.get('category', '—')}\n"
        f"*Root Cause:* {failure_analysis.get('root_cause', '—')}\n"
        f"*Likely Reason:* {failure_analysis.get('likely_reason', '—')}\n"
        f"*Recommended Fix:* {failure_analysis.get('recommended_fix', '—')}\n"
        f"*Business Impact:* {failure_analysis.get('business_impact', '—')}\n\n"
        f"*Screenshot Evidence:* {screenshot_path}\n\n"
        f"*Steps to Reproduce:*\n"
        f"1. Run AI test agent against {parent_issue_key}\n"
        f"2. Execute workflow as per story: {summary}\n"
        f"3. Observe failure: {test_status}"
    )

    try:
        # A product defect should be created as a Bug. If Bug is unavailable,
        # fall back to Task rather than creating another Story.
        created = False
        bug = None
        for issue_type in ["Bug", "Task"]:
            try:
                bug = jira_client.create_issue(
                    project=PROJECT_KEY,
                    summary=bug_summary,
                    description=description,
                    issuetype={"name": issue_type},
                    labels=["AI-Detected", "AutomationFailure"],
                )
                created = True
                if issue_type != "Bug":
                    logger.warning(
                        "[%s] Jira Bug issue type unavailable; created %s as Task",
                        parent_issue_key, bug.key
                    )
                break
            except Exception:
                continue

        if not created or bug is None:
            raise Exception("Could not create Jira issue as Bug or Task")

        logger.info("[%s] Auto-created Jira bug: %s", parent_issue_key, bug.key)

        # Discover a valid Jira link type before linking.
        _link_bug_to_story(jira_client, bug.key, parent_issue_key)

        return bug.key

    except Exception as e:
        logger.error("[%s] Failed to create Jira bug: %s", parent_issue_key, e)
        return None
