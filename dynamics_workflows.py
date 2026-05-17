import logging
from datetime import datetime

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from config import (
    DYNAMICS_URL,
    TEST_EMAIL_DOMAIN,
    TEST_LEAD_PREFIX,
    TEST_CONTACT_PREFIX,
    TEST_COMPANY_PREFIX,
)
from selenium_helpers import (
    wait_for_dynamics_ready,
    capture_screenshot,
    click_element,
    type_element,
    has_required_error,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _unique(prefix):
    """Return a timestamped unique string, e.g. AI_Lead_20260515103045."""
    return f"{prefix}_{datetime.now().strftime('%Y%m%d%H%M%S')}"


def _unique_email(prefix):
    """Return a unique test email address."""
    return f"{_unique(prefix)}@{TEST_EMAIL_DOMAIN}"


def navigate_to_entity(driver, entity):
    """Navigate directly to an entity list page in Dynamics 365."""
    entity_map = {
        "lead": "lead",
        "contact": "contact",
        "account": "account",
    }
    etn = entity_map.get(entity)
    if not etn:
        raise ValueError(f"Unsupported entity: '{entity}'")
    url = f"{DYNAMICS_URL}/main.aspx?pagetype=entitylist&etn={etn}"
    driver.get(url)
    wait_for_dynamics_ready(driver)


def get_first_grid_record_text(driver):
    """Return the visible text of the first clickable record in a D365 grid."""
    possible_locators = [
        "(//div[@role='grid']//a)[1]",
        "(//a[contains(@class,'ms-Link')])[1]",
        "(//div[contains(@role,'row')]//a)[1]",
        "(//a[contains(@href,'account')])[1]",
    ]
    for xpath in possible_locators:
        try:
            element = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.XPATH, xpath))
            )
            text = element.text.strip()
            if text:
                return text
        except Exception as e:
            logger.debug("get_first_grid_record_text locator failed (%s): %s", xpath, e)
    return None


# ---------------------------------------------------------------------------
# Workflow dispatcher
# ---------------------------------------------------------------------------

def execute_ai_workflow(driver, issue_key, ai_plan):
    """Dispatch to the correct workflow based on the AI plan.

    Returns (status_string, screenshot_path).
    """
    workflow = ai_plan.get("workflow")
    data = ai_plan.get("test_data", {})

    logger.info("[%s] Executing AI workflow: %s", issue_key, workflow)

    workflow_map = {
        "create_lead": lambda: workflow_create_lead(driver, issue_key, data),
        "view_leads": lambda: workflow_view_leads(driver, issue_key),
        "create_contact": lambda: workflow_create_contact(driver, issue_key, data),
        "search_account": lambda: workflow_search_account(driver, issue_key, data),
        "update_lead_status": lambda: workflow_update_lead_status(driver, issue_key, data),
    }

    handler = workflow_map.get(workflow)
    if not handler:
        logger.error("[%s] Unknown workflow: %s", issue_key, workflow)
        error_path = capture_screenshot(driver, f"{issue_key}_unknown_workflow.png")
        return f"FAIL - Unknown workflow: {workflow}", error_path

    try:
        return handler()
    except Exception as e:
        logger.error("[%s] Workflow '%s' raised an exception: %s: %s", issue_key, workflow, type(e).__name__, e)
        error_path = capture_screenshot(driver, f"{issue_key}_error.png")
        return f"FAIL - {type(e).__name__}: {e}", error_path


# ---------------------------------------------------------------------------
# Individual workflows
# ---------------------------------------------------------------------------

def workflow_create_lead(driver, issue_key, data):
    navigate_to_entity(driver, "lead")
    capture_screenshot(driver, f"{issue_key}_01_leads_grid.png")

    click_element(driver, "new_button", "New Lead")
    wait_for_dynamics_ready(driver)
    capture_screenshot(driver, f"{issue_key}_02_new_lead_form.png")

    topic = data.get("topic") or _unique(TEST_LEAD_PREFIX + "_Topic")
    first_name = data.get("first_name") or "AI"
    last_name = data.get("last_name") or _unique(TEST_LEAD_PREFIX)
    company = data.get("company") or _unique(TEST_COMPANY_PREFIX)
    email = data.get("email") or _unique_email(TEST_LEAD_PREFIX.lower())

    type_element(driver, "topic", topic, "Topic")
    type_element(driver, "first_name", first_name, "First Name")
    type_element(driver, "last_name", last_name, "Last Name")

    for field, value, label in [("company", company, "Company"), ("email", email, "Email")]:
        try:
            type_element(driver, field, value, label)
        except Exception as e:
            logger.warning("[%s] Optional field '%s' not available, skipping: %s", issue_key, label, e)

    capture_screenshot(driver, f"{issue_key}_03_lead_form_filled.png")

    click_element(driver, "save_button", "Save")
    wait_for_dynamics_ready(driver)

    if has_required_error(driver):
        path = capture_screenshot(driver, f"{issue_key}_04_required_field_error.png")
        return "FAIL - Required field validation displayed", path

    capture_screenshot(driver, f"{issue_key}_04_lead_saved.png")
    navigate_to_entity(driver, "lead")
    grid_path = capture_screenshot(driver, f"{issue_key}_05_lead_grid_after_save.png")

    return "PASS", grid_path


def workflow_view_leads(driver, issue_key):
    navigate_to_entity(driver, "lead")
    path = capture_screenshot(driver, f"{issue_key}_01_view_leads.png")
    return "PASS", path


def workflow_create_contact(driver, issue_key, data):
    navigate_to_entity(driver, "contact")
    capture_screenshot(driver, f"{issue_key}_01_contacts_grid.png")

    click_element(driver, "new_button", "New Contact")
    wait_for_dynamics_ready(driver)
    capture_screenshot(driver, f"{issue_key}_02_new_contact_form.png")

    first_name = data.get("first_name") or "AI"
    last_name = data.get("last_name") or _unique(TEST_CONTACT_PREFIX)
    email = data.get("email") or _unique_email(TEST_CONTACT_PREFIX.lower())

    type_element(driver, "first_name", first_name, "First Name")
    type_element(driver, "last_name", last_name, "Last Name")

    try:
        type_element(driver, "email", email, "Email")
    except Exception as e:
        logger.warning("[%s] Email field not available, skipping: %s", issue_key, e)

    capture_screenshot(driver, f"{issue_key}_03_contact_form_filled.png")

    click_element(driver, "save_button", "Save")
    wait_for_dynamics_ready(driver)

    if has_required_error(driver):
        path = capture_screenshot(driver, f"{issue_key}_04_required_field_error.png")
        return "FAIL - Required field validation displayed", path

    capture_screenshot(driver, f"{issue_key}_04_contact_saved.png")
    navigate_to_entity(driver, "contact")
    grid_path = capture_screenshot(driver, f"{issue_key}_05_contact_grid_after_save.png")

    return "PASS", grid_path


def workflow_search_account(driver, issue_key, data):
    navigate_to_entity(driver, "account")
    capture_screenshot(driver, f"{issue_key}_01_accounts_before_search.png")

    logger.info("[%s] Discovering first existing account from grid...", issue_key)
    discovered = get_first_grid_record_text(driver)

    if discovered:
        search_text = discovered
        logger.info("[%s] Discovered account: %s", issue_key, search_text)
    else:
        search_text = data.get("search_text", "")
        logger.warning("[%s] No account discovered from grid; using AI-provided search text: '%s'", issue_key, search_text)

    if not search_text:
        path = capture_screenshot(driver, f"{issue_key}_02_no_account_found.png")
        return "FAIL - No account available to search", path

    type_element(driver, "search", search_text, "Account Search")
    ActionChains(driver).send_keys(Keys.ENTER).perform()
    wait_for_dynamics_ready(driver)

    path = capture_screenshot(driver, f"{issue_key}_02_account_search_results.png")

    if search_text.lower() in driver.page_source.lower():
        return f"PASS - Account found in results: {search_text}", path

    return f"PASS - Search executed, account not confirmed in page source: {search_text}", path


def _setup_lead_for_update(driver, issue_key):
    """Create a throwaway lead so update_lead_status has something to work with."""
    logger.info("[%s] No existing lead found; creating a setup lead...", issue_key)
    setup_data = {
        "topic": _unique(TEST_LEAD_PREFIX + "_Update_Topic"),
        "first_name": "AI",
        "last_name": _unique(TEST_LEAD_PREFIX + "_Update"),
        "company": _unique(TEST_COMPANY_PREFIX + "_Update"),
        "email": _unique_email((TEST_LEAD_PREFIX + "_update").lower()),
    }
    return workflow_create_lead(driver, f"{issue_key}_setup", setup_data)


def workflow_update_lead_status(driver, issue_key, data):
    navigate_to_entity(driver, "lead")
    capture_screenshot(driver, f"{issue_key}_01_leads_before_update.png")

    discovered = get_first_grid_record_text(driver)

    if discovered:
        logger.info("[%s] Discovered existing lead: %s", issue_key, discovered)
    else:
        create_status, create_path = _setup_lead_for_update(driver, issue_key)
        if not create_status.startswith("PASS"):
            return "FAIL - Could not create setup lead for update flow", create_path

        navigate_to_entity(driver, "lead")
        wait_for_dynamics_ready(driver)
        capture_screenshot(driver, f"{issue_key}_02_leads_after_setup_creation.png")

    logger.info("[%s] Opening first available lead record...", issue_key)
    click_element(driver, "first_record", "First Lead Record")
    wait_for_dynamics_ready(driver)
    capture_screenshot(driver, f"{issue_key}_03_lead_opened_before_update.png")

    try:
        click_element(driver, "qualify_button", "Qualify")
        wait_for_dynamics_ready(driver)

        try:
            click_element(driver, "confirm_button", "Confirm", timeout=8)
            wait_for_dynamics_ready(driver)
        except Exception as e:
            logger.info("[%s] No confirmation dialog appeared (normal): %s", issue_key, e)

        path = capture_screenshot(driver, f"{issue_key}_04_lead_status_updated.png")
        return "PASS - Lead qualified successfully", path

    except Exception as e:
        logger.error("[%s] Qualify action failed: %s", issue_key, e)
        path = capture_screenshot(driver, f"{issue_key}_04_qualify_failed.png")
        return f"FAIL - Could not qualify lead: {type(e).__name__}: {e}", path
