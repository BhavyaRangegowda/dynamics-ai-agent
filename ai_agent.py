"""
ai_agent.py — AI Decision Engine

Responsibilities:
1. validate_user_story()    — reject invalid/placeholder stories before any AI call
2. ai_generate_test_cases() — generate structured test cases from a user story
3. ai_decide_workflow()     — decide workflow name from user story (used for logging/routing)

Note: Actual step generation is now in dynamics_workflows.py via
      generate_steps_from_story() which reads the live DOM.
      ai_decide_workflow() now just classifies the story intent —
      the real automation is fully dynamic.
"""

import json
import logging
import re

from config import GROQ_MODEL

logger = logging.getLogger(__name__)

_MAX_RETRIES = 3

# Minimum requirements for a valid user story
_MIN_STORY_LENGTH = 10
_MIN_STORY_WORDS = 3

# Keywords that indicate a placeholder / non-story
_INVALID_KEYWORDS = {
    "fail", "test", "todo", "placeholder", "dummy", "sample",
    "delete me", "ignore", "n/a", "tbd", "xxx", "temp", "fix",
    "bug", "error", "broken", "untitled", "new issue", "issue"
}

# Keywords that indicate a valid D365 user story
_VALID_ACTION_KEYWORDS = [
    "as a", "i want", "i need", "so that", "user want", "user need",
    "create", "view", "search", "update", "delete", "manage", "add",
    "edit", "list", "find", "open", "close", "submit", "qualify",
    "convert", "assign", "filter", "export", "import", "merge",
    "activate", "deactivate", "schedule", "track", "record", "log",
    "validate", "verify", "handle", "handling", "locator", "fallback", "resilient"
]


# ---------------------------------------------------------------------------
# JSON extraction
# ---------------------------------------------------------------------------

def extract_json(text):
    """Extract the first complete JSON object or array from a string.

    Handles markdown fences and extra text around the JSON payload.
    """
    if not isinstance(text, str) or not text.strip():
        raise ValueError("No JSON text provided")

    # Remove fenced code blocks that may wrap JSON responses.
    text = re.sub(r"```(?:json)?\n", "", text, flags=re.DOTALL)
    text = text.replace("```", "")

    def _scan_for_json(open_char, close_char, start_index):
        depth = 0
        in_string = False
        escape = False
        for i, ch in enumerate(text[start_index:], start_index):
            if ch == '"' and not escape:
                in_string = not in_string
            if ch == '\\' and not escape:
                escape = True
                continue
            escape = False
            if in_string:
                continue
            if ch == open_char:
                depth += 1
            elif ch == close_char:
                depth -= 1
                if depth == 0:
                    return text[start_index:i + 1]
        return None

    candidates = []
    for open_char, close_char in (("{", "}"), ("[", "]")):
        start = text.find(open_char)
        if start == -1:
            continue
        candidate = _scan_for_json(open_char, close_char, start)
        if candidate:
            candidates.append((start, candidate))

    if not candidates:
        raise ValueError("No complete JSON object or array found in AI response")

    # Choose the earliest valid JSON payload in the text.
    candidates.sort(key=lambda item: item[0])
    for _, candidate in candidates:
        try:
            return json.loads(candidate)
        except json.JSONDecodeError as e:
            continue

    raise ValueError("AI returned invalid JSON in all discovered payloads")

    raise ValueError("No complete JSON object or array found in AI response")


def _normalize_ai_plan(plan, summary):
    if not isinstance(plan, dict):
        plan = {}

    workflow = str(plan.get("workflow") or "skip").strip()
    if not workflow:
        workflow = "skip"

    entity = str(plan.get("entity") or "none").strip()

    test_data = plan.get("test_data")
    if not isinstance(test_data, dict):
        test_data = {}

    return {
        "workflow": workflow,
        "entity": entity,
        "skip_reason": str(plan.get("skip_reason") or "Story not testable"),
        "test_data": test_data,
        "summary": summary,
    }


# ---------------------------------------------------------------------------
# Story validation
# ---------------------------------------------------------------------------

def validate_user_story(user_story):
    """Validate that a user story is meaningful and testable.

    Returns (is_valid: bool, reason: str).
    """
    if not user_story or not user_story.strip():
        return False, "User story is empty"

    story = user_story.strip()

    # Too short
    if len(story) < _MIN_STORY_LENGTH:
        return False, f"Too short ({len(story)} chars): '{story}'"

    # Too few words
    words = [w for w in story.split() if w]
    if len(words) < _MIN_STORY_WORDS:
        return False, f"Too vague ({len(words)} words): '{story}'"

    # Exact match with known invalid keywords
    story_lower = story.lower().strip(".!?,;:-")
    if story_lower in _INVALID_KEYWORDS:
        return False, f"Looks like a placeholder: '{story}'"

    # Single invalid keyword as entire story
    for kw in _INVALID_KEYWORDS:
        if story_lower == kw or story_lower.replace(" ", "") == kw:
            return False, f"Placeholder content: '{story}'"

    # Must contain at least one action keyword to be testable
    story_lower_full = story.lower()
    has_action = any(kw in story_lower_full for kw in _VALID_ACTION_KEYWORDS)
    if not has_action:
        return False, f"No testable action found in story: '{story}'"

    return True, "Valid"


# ---------------------------------------------------------------------------
# Test case generation
# ---------------------------------------------------------------------------

def ai_generate_test_cases(groq_client, user_story):
    """Generate 3 structured test cases for a user story.

    Returns a formatted string with test cases, or a skip notice for invalid stories.
    """
    is_valid, reason = validate_user_story(user_story)
    if not is_valid:
        logger.warning("Skipping test-case generation for invalid story: %s", reason)
        return f"SKIPPED - {reason}"

    prompt = f"""You are a QA engineer specialising in Microsoft Dynamics 365 Sales.

Generate exactly 3 test cases for this user story. Be specific to D365.

User story:
{user_story}

Format each test case exactly like this:

Test Case [N]: [Descriptive Name]
Precondition: [What must be true before this test]
Steps:
  1. [Step]
  2. [Step]
  3. [Step]
Expected Result: [What D365 should show/do]
Priority: [High/Medium/Low]

---
"""

    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            response = groq_client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
            )
            result = response.choices[0].message.content
            logger.info("Generated test cases for: %s", user_story[:60])
            return result
        except Exception as e:
            logger.warning(
                "ai_generate_test_cases attempt %d/%d failed: %s",
                attempt, _MAX_RETRIES, e
            )
            if attempt == _MAX_RETRIES:
                raise

    return ""


# ---------------------------------------------------------------------------
# Workflow classification
# ---------------------------------------------------------------------------

def ai_decide_workflow(groq_client, user_story):
    """Classify the user story intent into a workflow name.

    In the new dynamic architecture this is used for:
    - Logging and reporting (what kind of workflow was this?)
    - Skip detection (is this story testable at all?)
    - The workflow name is passed to execute_ai_workflow which
      uses it as context when generating steps from the live DOM

    Returns a dict with workflow, entity, skip_reason, test_data.
    """
    # Validate story first — before any AI call
    is_valid, reason = validate_user_story(user_story)
    if not is_valid:
        logger.warning("Skipping invalid user story — %s", reason)
        return {
            "workflow": "skip",
            "entity": "none",
            "skip_reason": reason,
            "test_data": {},
            "summary": user_story,
        }

    # Deterministic routing for framework-validation demo stories.
    # These stories test the automation framework itself, so do not leave their
    # classification to model wording/variance.
    story_lower = user_story.lower()

    if (
        "resilient locator" in story_lower
        or "fallback locator" in story_lower
        or ("locator" in story_lower and "lead" in story_lower)
    ):
        result = _normalize_ai_plan(
            {
                "workflow": "validate_resilient_locator",
                "entity": "lead",
                "skip_reason": "",
                "test_data": {},
            },
            user_story,
        )
        logger.info("Framework validation story routed deterministically → validate_resilient_locator")
        return result

    if (
        "failure handling" in story_lower
        or "condition that is not satisfied" in story_lower
        or "automation verified" in story_lower
    ):
        result = _normalize_ai_plan(
            {
                "workflow": "validate_failure_handling",
                "entity": "lead",
                "skip_reason": "",
                "test_data": {"expected_status": "Automation Verified"},
            },
            user_story,
        )
        logger.info("Framework validation story routed deterministically → validate_failure_handling")
        return result

    prompt = f"""You are an AI classification agent for Microsoft Dynamics 365 Sales.

Read this user story and classify it.

User story:
{user_story}

Return ONLY valid JSON with no extra text or markdown.

Rules:
1. workflow must be a snake_case description of what to automate
2. If the story is clearly not related to D365 or not automatable, use "skip"
3. entity must be the D365 entity involved (lead, contact, account,
   opportunity, task, etc.)
4. test_data should contain relevant field values — use descriptive
   placeholder names, NOT static emails (actual unique values are
   generated at runtime)

Examples of valid workflows:
  create_lead, view_leads, update_lead_status, qualify_lead,
  add_note_to_lead, assign_lead, delete_lead, filter_leads,
  export_to_excel, create_lead_missing_required,
  create_contact, update_contact, view_contacts, search_contact,
  delete_contact, create_account, search_account, update_account,
  create_opportunity, view_opportunities, view_opportunity_details,
  close_opportunity_won, create_task, assign_record

Return format:
{{
  "workflow": "create_lead",
  "entity": "lead",
  "skip_reason": "",
  "summary": "{user_story}",
  "test_data": {{
    "topic": "Test Lead Topic",
    "first_name": "Test",
    "last_name": "User",
    "company": "Test Company",
    "status": "Qualified"
  }}
}}
"""

    last_error = None

    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            response = groq_client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
            )
            raw = response.choices[0].message.content
            parsed = extract_json(raw)
            result = _normalize_ai_plan(parsed, user_story)

            logger.info(
                "Workflow classified: %s → %s (entity: %s)",
                user_story[:50], result.get("workflow"), result.get("entity")
            )
            return result

        except (ValueError, json.JSONDecodeError) as e:
            last_error = e
            logger.warning(
                "ai_decide_workflow JSON parse failed (attempt %d/%d): %s",
                attempt, _MAX_RETRIES, e
            )
        except Exception as e:
            last_error = e
            logger.warning(
                "ai_decide_workflow API error (attempt %d/%d): %s",
                attempt, _MAX_RETRIES, e
            )

    logger.error(
        "ai_decide_workflow failed after %d attempts: %s",
        _MAX_RETRIES, last_error
    )
    return _normalize_ai_plan(
        {
            "workflow": "skip",
            "entity": "none",
            "skip_reason": "AI classification failed",
            "test_data": {},
        },
        user_story,
    )