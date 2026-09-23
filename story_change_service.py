import hashlib
import json
import logging
import os

from config import STORY_HASH_FILE

logger = logging.getLogger(__name__)


def _load_hashes():
    if not os.path.exists(STORY_HASH_FILE):
        return {}
    try:
        with open(STORY_HASH_FILE, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.warning("Could not load story hashes from %s: %s", STORY_HASH_FILE, e)
        return {}


def _save_hashes(hashes):
    try:
        with open(STORY_HASH_FILE, "w") as f:
            json.dump(hashes, f, indent=2)
        logger.debug("Story hashes saved to %s", STORY_HASH_FILE)
    except Exception as e:
        logger.error("Could not save story hashes: %s", e)


def _hash_story(issue):
    """Generate a SHA256 hash of a Jira issue's key content fields."""
    content = {
        "summary": issue.fields.summary or "",
        "description": str(issue.fields.description or ""),
        "status": str(issue.fields.status) if issue.fields.status else "",
    }
    try:
        ac = getattr(issue.fields, "customfield_10016", None)
        if ac:
            content["acceptance_criteria"] = str(ac)
    except Exception:
        pass
    raw = json.dumps(content, sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()


def detect_story_changes(issues):
    """Compare current Jira issues against stored hashes from the last run.

    Returns dict with:
        new_issues:       list of issue keys that are brand new
        changed_issues:   list of issue keys whose content changed
        unchanged_issues: list of issue keys with no changes
        current_hashes:   dict of current hashes to save after run
    """
    stored_hashes = _load_hashes()
    current_hashes = {}
    new_issues = []
    changed_issues = []
    unchanged_issues = []

    for issue in issues:
        key = issue.key
        current_hash = _hash_story(issue)
        current_hashes[key] = current_hash

        if key not in stored_hashes:
            new_issues.append(key)
            logger.info("[STORY CHANGE] %s is NEW", key)
        elif stored_hashes[key] != current_hash:
            changed_issues.append(key)
            logger.info("[STORY CHANGE] %s has CHANGED since last run", key)
        else:
            unchanged_issues.append(key)
            logger.debug("[STORY CHANGE] %s is unchanged", key)

    return {
        "new_issues": new_issues,
        "changed_issues": changed_issues,
        "unchanged_issues": unchanged_issues,
        "current_hashes": current_hashes,
    }


def save_story_hashes(change_result):
    """Persist the current story hashes after a successful run."""
    _save_hashes(change_result["current_hashes"])
    logger.info("Story hashes saved — next run will detect changes against these.")


def should_regenerate(issue_key, change_result):
    """Return True if this issue is new or changed and needs fresh test cases."""
    return (
        issue_key in change_result["new_issues"]
        or issue_key in change_result["changed_issues"]
    )


def get_change_summary(change_result):
    """Return a human-readable summary of story changes."""
    new = change_result["new_issues"]
    changed = change_result["changed_issues"]
    unchanged = change_result["unchanged_issues"]
    lines = ["Story Change Detection:"]
    if new:
        lines.append(f"  NEW stories: {', '.join(new)}")
    if changed:
        lines.append(f"  CHANGED stories: {', '.join(changed)}")
    if unchanged:
        lines.append(f"  Unchanged: {', '.join(unchanged)}")
    if not new and not changed:
        lines.append("  No story changes detected — all stories unchanged")
    return "\n".join(lines)