import json
import re
import logging

from config import GROQ_MODEL

logger = logging.getLogger(__name__)

_MAX_RETRIES = 3


def extract_json(text):
    """Extract the first complete JSON object from a string.

    Uses brace counting so nested objects (like test_data) are included
    correctly, rather than stopping at the first closing brace.
    """
    start = text.find("{")
    if start == -1:
        raise ValueError("No JSON object found in AI response")

    depth = 0
    for i, ch in enumerate(text[start:], start):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                candidate = text[start:i + 1]
                try:
                    return json.loads(candidate)
                except json.JSONDecodeError as e:
                    raise ValueError(
                        f"AI returned invalid JSON: {e}\nRaw text: {candidate[:300]}"
                    )

    raise ValueError(f"Unbalanced braces in AI response: {text[:300]}")


def ai_generate_test_cases(groq_client, user_story):
    """Ask the AI to generate 3 test cases for a given user story."""
    prompt = f"""
Generate 3 simple test cases for this Dynamics 365 Sales user story.

User story:
{user_story}

Format:
1. Test Case Name
Steps:
Expected Result:
"""
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            response = groq_client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.warning("ai_generate_test_cases attempt %d/%d failed: %s", attempt, _MAX_RETRIES, e)
            if attempt == _MAX_RETRIES:
                raise

    return ""  # unreachable, satisfies linters


def ai_decide_workflow(groq_client, user_story):
    """Ask the AI to decide which automation workflow to run for a user story.

    Returns a dict with keys: workflow, entity, test_data.
    Retries up to _MAX_RETRIES times on bad JSON or API errors.
    """
    prompt = f"""
You are an AI test automation agent for Microsoft Dynamics 365 Sales.

Read this Jira user story and decide which workflow to execute.

User story:
{user_story}

Return ONLY valid JSON with no extra text, explanation, or markdown fences.

Allowed workflow values:
- create_lead
- view_leads
- create_contact
- search_account
- update_lead_status

Return format:
{{
  "workflow": "create_lead",
  "entity": "lead",
  "test_data": {{
    "topic": "AI Generated Lead Topic",
    "first_name": "AI",
    "last_name": "TestLead",
    "company": "AI Testing Corp",
    "email": "aitestlead@testcorp.com",
    "search_text": "Fabrikam"
  }}
}}
"""
    last_error = None

    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            response = groq_client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[{"role": "user", "content": prompt}]
            )
            raw = response.choices[0].message.content
            return extract_json(raw)
        except (ValueError, json.JSONDecodeError) as e:
            last_error = e
            logger.warning("ai_decide_workflow JSON parse failed (attempt %d/%d): %s", attempt, _MAX_RETRIES, e)
        except Exception as e:
            last_error = e
            logger.warning("ai_decide_workflow API error (attempt %d/%d): %s", attempt, _MAX_RETRIES, e)

    raise RuntimeError(
        f"ai_decide_workflow failed after {_MAX_RETRIES} attempts: {last_error}"
    )
