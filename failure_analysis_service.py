import base64
import logging
import os

from config import GROQ_MODEL

logger = logging.getLogger(__name__)

FAILURE_CATEGORIES = {
    "LOCATOR_CHANGED": "Element locator changed — D365 UI updated",
    "TIMING_ISSUE": "Page load or timing issue — element not ready",
    "ENVIRONMENT_ISSUE": "Environment or network issue — retry recommended",
    "PRODUCT_BUG": "Potential product bug — Jira defect recommended",
    "TEST_DATA_ISSUE": "Test data problem — data missing or invalid",
    "AUTH_ISSUE": "Authentication or session expired",
    "UNKNOWN": "Unable to classify automatically",
}


def _encode_screenshot(screenshot_path):
    if not screenshot_path or not os.path.exists(screenshot_path):
        return None
    try:
        with open(screenshot_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    except Exception as e:
        logger.warning("Could not encode screenshot %s: %s", screenshot_path, e)
        return None


def _classify_failure(error_message):
    """Quick evidence-based pre-classification before sending to AI."""
    error_lower = str(error_message).lower()

    # Assertion / expected-value mismatch.
    # This remains a conservative hint only; the AI may correct it to
    # PRODUCT_BUG when the Jira requirement explicitly establishes the
    # expected application behaviour and the observed result contradicts it.
    if (
        "expected status" in error_lower
        or "expected value" in error_lower
        or "was not displayed" in error_lower
        or "expected condition failed" in error_lower
    ):
        return "TEST_DATA_ISSUE"

    if any(k in error_lower for k in [
        "locator", "element not found", "no such element",
        "locators exhausted", "could not click", "could not type"
    ]):
        return "LOCATOR_CHANGED"

    if any(k in error_lower for k in [
        "timeout", "time out", "timed out", "wait"
    ]):
        return "TIMING_ISSUE"

    if any(k in error_lower for k in [
        "network", "connection", "refused", "unreachable",
        "dns", "ssl", "certificate"
    ]):
        return "ENVIRONMENT_ISSUE"

    if any(k in error_lower for k in [
        "auth", "session", "login", "mfa", "token expired"
    ]):
        return "AUTH_ISSUE"

    if any(k in error_lower for k in [
        "required field", "validation", "invalid", "test data"
    ]):
        return "TEST_DATA_ISSUE"

    return "UNKNOWN"


def analyze_failure_with_ai(
    groq_client,
    issue_key,
    summary,
    error_message,
    screenshot_path=None,
    requirement_text=None,
):
    """Analyse a test failure using AI and return a structured analysis dict."""
    pre_category = _classify_failure(error_message)
    screenshot_note = (
        f"A screenshot was captured at: {screenshot_path}"
        if screenshot_path else "No screenshot available."
    )
    requirement_note = (
        str(requirement_text).strip()
        if requirement_text
        else "No detailed Jira requirement/acceptance criteria were supplied."
    )

    prompt = f"""You are a senior QA automation engineer specialising in Microsoft Dynamics 365.

Analyse this failed test and provide a structured root cause analysis.

== FAILED TEST DETAILS ==
Issue Key: {issue_key}
User Story: {summary}

JIRA REQUIREMENT / ACCEPTANCE CRITERIA:
{requirement_note}

OBSERVED TEST FAILURE:
{error_message}

Pre-Classification: {pre_category} — {FAILURE_CATEGORIES.get(pre_category, "")}
Screenshot: {screenshot_note}

== INSTRUCTIONS ==

Analyse ONLY the evidence supplied above.

IMPORTANT EVIDENCE RULES:
- Treat the Jira requirement/acceptance criteria as the authoritative statement
  of expected application behaviour for this test.
- Do NOT invent application behaviour that is not present in the evidence.
- Do NOT assume that Dynamics 365 performs an asynchronous update unless the
  error message or supplied evidence explicitly indicates asynchronous processing.
- Do NOT classify a failure as TIMING_ISSUE merely because waiting might make
  the test pass.
- Do NOT classify something as PRODUCT_BUG merely because the test failed.
- PRODUCT_BUG requires:
    1. the Jira requirement explicitly establishes the expected behaviour,
    2. the test reached the relevant application behaviour successfully,
    3. the observed result contradicts that requirement,
    4. the evidence does not primarily indicate locator, timing,
       authentication, environment, or test-data failure.
- When those conditions are satisfied, classify the failure as PRODUCT_BUG.
- Distinguish the OBSERVED FAILURE from the SUSPECTED ROOT CAUSE.
- If the expected value/status may not have been configured, created, or set
  by the test data/workflow, prefer TEST_DATA_ISSUE.
- If there is insufficient evidence to determine the root cause, use UNKNOWN
  rather than inventing an explanation.
- Treat Pre-Classification as a hint only. Correct it when the evidence
  supports another category.
- Preserve literal business values from the Jira requirement and observed failure exactly as supplied.
- Curly-brace tokens such as {{{{unique}}}} are automation template syntax only. Never add curly braces around ordinary requirement text, prefixes, suffixes, statuses, or expected values.
- If the Jira requirement contains a literal prefix or suffix, reproduce that literal text exactly in the analysis; do not convert it into template syntax.

For an expected-versus-actual status/value mismatch:
- TEST_DATA_ISSUE = expected status/value was not configured, created, supplied,
  or established by the test setup.
- PRODUCT_BUG = there is clear evidence that the requirement says the application
  must produce that status/value, but the application failed to do so.
- TIMING_ISSUE = there is explicit evidence that the correct value is expected
  after asynchronous processing or delayed loading.
- UNKNOWN = the available evidence cannot establish which of the above occurred.

1. Confirm or correct the failure category. Choose ONE from:
   - LOCATOR_CHANGED
   - TIMING_ISSUE
   - ENVIRONMENT_ISSUE
   - PRODUCT_BUG
   - TEST_DATA_ISSUE
   - AUTH_ISSUE
   - UNKNOWN

2. Should a Jira bug be created?
   Answer YES only when CATEGORY is PRODUCT_BUG and the supplied evidence
   supports a product defect. Otherwise answer NO.

Return your response in EXACTLY this format (no extra text):

CATEGORY: <one of the categories above>
ROOT_CAUSE: <describe what the supplied evidence establishes; do not speculate>
LIKELY_REASON: <technical explanation based only on available evidence>
RECOMMENDED_FIX: <specific actionable next step>
BUSINESS_IMPACT: <impact if the issue represents the expected application behaviour>
CREATE_BUG: <YES or NO>
"""

    try:
        response = groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        raw_text = response.choices[0].message.content
        logger.info("[%s] AI failure analysis complete", issue_key)
        result = _parse_analysis(raw_text, pre_category, error_message)
        result["raw_text"] = raw_text
        result["issue_key"] = issue_key
        result["screenshot_path"] = screenshot_path
        return result
    except Exception as e:
        logger.error("[%s] AI failure analysis failed: %s", issue_key, e)
        return _fallback_analysis(issue_key, pre_category, error_message, screenshot_path)


def _parse_analysis(raw_text, pre_category, error_message):
    result = {
        "category": pre_category,
        "root_cause": "Could not determine automatically",
        "likely_reason": str(error_message),
        "recommended_fix": "Review pipeline logs and screenshots manually",
        "business_impact": "Unable to determine automatically",
        "create_bug": False,
    }
    for line in raw_text.strip().split("\n"):
        line = line.strip()
        if line.startswith("CATEGORY:"):
            cat = line.replace("CATEGORY:", "").strip()
            if cat in FAILURE_CATEGORIES:
                result["category"] = cat
        elif line.startswith("ROOT_CAUSE:"):
            result["root_cause"] = line.replace("ROOT_CAUSE:", "").strip()
        elif line.startswith("LIKELY_REASON:"):
            result["likely_reason"] = line.replace("LIKELY_REASON:", "").strip()
        elif line.startswith("RECOMMENDED_FIX:"):
            result["recommended_fix"] = line.replace("RECOMMENDED_FIX:", "").strip()
        elif line.startswith("BUSINESS_IMPACT:"):
            result["business_impact"] = line.replace("BUSINESS_IMPACT:", "").strip()
        elif line.startswith("CREATE_BUG:"):
            val = line.replace("CREATE_BUG:", "").strip().upper()
            result["create_bug"] = val == "YES"

    # Safety invariant: a Jira bug may only be auto-created for PRODUCT_BUG.
    # This prevents an inconsistent AI response such as CATEGORY=UNKNOWN +
    # CREATE_BUG=YES from opening a defect.
    if result["category"] != "PRODUCT_BUG":
        result["create_bug"] = False

    return result


def _fallback_analysis(issue_key, pre_category, error_message, screenshot_path):
    return {
        "issue_key": issue_key,
        "category": pre_category,
        "root_cause": "AI analysis unavailable — manual review required",
        "likely_reason": str(error_message),
        "recommended_fix": "Review pipeline logs and screenshots manually",
        "business_impact": "Unable to determine automatically",
        "create_bug": False,
        "raw_text": f"AI analysis failed.\nError: {error_message}",
        "screenshot_path": screenshot_path,
    }


def format_analysis_for_jira(analysis):
    """Format a failure analysis dict as a Jira comment string."""
    if not analysis:
        return ""
    category = analysis.get("category", "UNKNOWN")
    category_label = FAILURE_CATEGORIES.get(category, category)
    return (
        f"*🤖 AI Failure Analysis*\\n\\n"
        f"*Category:* {category} — {category_label}\\n"
        f"*Root Cause:* {analysis.get('root_cause', '—')}\\n"
        f"*Likely Reason:* {analysis.get('likely_reason', '—')}\\n"
        f"*Recommended Fix:* {analysis.get('recommended_fix', '—')}\\n"
        f"*Business Impact:* {analysis.get('business_impact', '—')}\\n"
        f"*Auto-create Bug:* {'Yes ✅' if analysis.get('create_bug') else 'No'}\\n"
    )
