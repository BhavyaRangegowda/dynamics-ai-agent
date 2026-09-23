import os
import time
import logging

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from config import SCREENSHOT_DIR
from locators import LOCATOR_LIBRARY

logger = logging.getLogger(__name__)

os.makedirs(SCREENSHOT_DIR, exist_ok=True)


def wait_for_page_load(driver, timeout=30):
    """Wait until document.readyState is complete.
    
    Uses smart polling instead of fixed sleep for speed.
    """
    try:
        WebDriverWait(driver, timeout).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
    except Exception as e:
        logger.warning("wait_for_page_load timed out: %s", e)
    # Small buffer only — not a fixed long sleep
    time.sleep(0.5)


def wait_for_dynamics_ready(driver, timeout=45):
    """Wait for D365 page to be fully loaded.
    
    Uses smart waiting — polls for readiness instead of fixed sleeps.
    Much faster than the old version for dynamic workflows.
    """
    wait_for_page_load(driver, timeout)

    # Wait for body to be visible
    try:
        WebDriverWait(driver, timeout).until(
            EC.visibility_of_element_located((By.TAG_NAME, "body"))
        )
    except Exception as e:
        logger.warning("wait_for_dynamics_ready body wait timed out: %s", e)

    # Wait for D365 spinners to disappear (smart — exits as soon as ready)
    spinner_xpaths = [
        "//div[contains(@class,'ms-Spinner')]",
        "//*[contains(@class,'loadingIndicator')]",
        "//*[contains(@data-id,'loading')]",
    ]
    for xpath in spinner_xpaths:
        try:
            WebDriverWait(driver, 10).until(
                EC.invisibility_of_element_located((By.XPATH, xpath))
            )
        except Exception:
            pass  # Spinner may not exist

    # Minimal buffer — just enough for D365 JS to settle
    time.sleep(1)


def capture_screenshot(driver, filename, quick=False):
    """Save a screenshot to SCREENSHOT_DIR and return the full path.

    Args:
        driver:   WebDriver instance
        filename: Screenshot filename
        quick:    If True, skip the full wait (use for step-by-step screenshots)
                  If False (default), do full wait (use for final evidence shots)

    Temporarily applies 90% zoom for readability, then resets it.
    """
    # Full wait for important screenshots, quick wait for step screenshots
    if quick:
        time.sleep(0.3)  # Minimal wait for step screenshots
    else:
        wait_for_dynamics_ready(driver)

    path = os.path.join(SCREENSHOT_DIR, filename)

    try:
        driver.execute_script("document.body.style.zoom='90%'")
        time.sleep(0.3)
    except Exception as e:
        logger.warning("Could not set zoom before screenshot: %s", e)

    driver.save_screenshot(path)
    logger.info("Screenshot captured: %s", path)

    try:
        driver.execute_script("document.body.style.zoom='100%'")
    except Exception as e:
        logger.warning("Could not reset zoom after screenshot: %s", e)

    return path


def get_locators(locator_name):
    """Look up a locator list by name; raise clearly if not found."""
    locators = LOCATOR_LIBRARY.get(locator_name)
    if not locators:
        raise KeyError(f"Locator '{locator_name}' not found in LOCATOR_LIBRARY")
    return locators


def click_element_resilient(driver, locator_name, display_name=None, timeout=8, primary_locator=None):
    """Click an element while making locator recovery visible in logs.

    If primary_locator is supplied, it is attempted first. On failure the
    function tries the configured LOCATOR_LIBRARY alternatives and logs the
    recovery. This is useful both for resilient automation and for demonstrating
    that a stale locator does not stop the test.

    Returns a dict describing whether fallback recovery was used.
    """
    name = display_name or locator_name
    configured = get_locators(locator_name)
    candidates = []
    if primary_locator is not None:
        candidates.append(("primary", primary_locator))
    candidates.extend((f"fallback-{i}", locator) for i, locator in enumerate(configured, 1))

    last_error = None
    primary_failed = False

    for label, locator in candidates:
        try:
            logger.info("SELF-HEALING [%s]: trying %s locator: %s", name, label, locator)
            element = WebDriverWait(driver, timeout).until(
                EC.element_to_be_clickable(locator)
            )
            driver.execute_script(
                "arguments[0].scrollIntoView({block:'center', inline:'center'});",
                element,
            )
            try:
                element.click()
            except Exception:
                driver.execute_script("arguments[0].click();", element)

            if primary_failed or label.startswith("fallback-") and primary_locator is not None:
                logger.info("SELF-HEALED [%s]: %s locator succeeded", name, label)
                return {"clicked": True, "self_healed": True, "locator": str(locator)}

            logger.info("Clicked [%s] using primary locator", name)
            return {"clicked": True, "self_healed": False, "locator": str(locator)}

        except Exception as e:
            last_error = e
            if label == "primary":
                primary_failed = True
                logger.warning("PRIMARY LOCATOR FAILED [%s] — activating fallback recovery", name)
            else:
                logger.info("SELF-HEALING [%s]: %s locator unavailable; trying next", name, label)

    raise RuntimeError(
        f"Could not click '{name}' — primary and fallback locators exhausted. "
        f"Last error: {last_error}"
    )


def click_element(driver, locator_name, display_name=None, timeout=20):
    """Try each locator in turn until one is clickable, then click it.

    Falls back to JS click if a normal click fails.
    Raises if all locators are exhausted.
    """
    name = display_name or locator_name
    locators = get_locators(locator_name)
    last_error = None

    for locator in locators:
        try:
            element = WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located(locator)
            )
            driver.execute_script(
                "arguments[0].scrollIntoView({block:'center', inline:'center'});",
                element
            )
            time.sleep(0.5)

            element = WebDriverWait(driver, timeout).until(
                EC.element_to_be_clickable(locator)
            )
            try:
                element.click()
            except Exception:
                driver.execute_script("arguments[0].click();", element)

            logger.info("Clicked: %s", name)
            return True

        except Exception as e:
            logger.debug("Locator %s failed for '%s': %s", locator, name, e)
            last_error = e
            continue

    raise RuntimeError(f"Could not click '{name}' — all locators exhausted. Last error: {last_error}")


def type_element(driver, locator_name, value, display_name=None, timeout=20):
    """Try each locator in turn until one accepts keyboard input.

    Clears the field before typing. Raises if all locators are exhausted.
    """
    name = display_name or locator_name
    locators = get_locators(locator_name)
    last_error = None

    for locator in locators:
        try:
            field = WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located(locator)
            )
            driver.execute_script(
                "arguments[0].scrollIntoView({block:'center', inline:'center'});",
                field
            )
            time.sleep(0.5)

            field.click()
            try:
                field.clear()
            except Exception:
                field.send_keys(Keys.CONTROL, "a")
                field.send_keys(Keys.DELETE)

            field.send_keys(value)
            logger.info("Typed %s: %s", name, value)
            return True

        except Exception as e:
            logger.debug("Locator %s failed for '%s': %s", locator, name, e)
            last_error = e
            continue

    raise RuntimeError(f"Could not type into '{name}' — all locators exhausted. Last error: {last_error}")


def has_required_error(driver):
    """Return True if the page contains a required-field validation message."""
    page = driver.page_source.lower()
    return (
        "required fields must be filled in" in page
        or "required fields" in page
    )


def handle_duplicate_popup(driver):
    """Detect and dismiss the Dynamics 365 duplicate records popup.

    If a duplicate is found, clicks Ignore and save to proceed.
    Returns True if popup was found and dismissed, False if no popup.
    """
    page = driver.page_source.lower()
    if "duplicate records found" not in page and "duplicates found" not in page:
        return False

    logger.warning("Duplicate records popup detected — clicking Ignore and save")
    try:
        click_element(driver, "ignore_and_save", "Ignore and save", timeout=10)
        wait_for_dynamics_ready(driver)
        logger.info("Duplicate popup dismissed successfully")
        return True
    except Exception as e:
        logger.error("Could not dismiss duplicate popup: %s", e)
        return False


def wait_for_d365_spinner(driver, timeout=30):
    """Wait for D365 loading spinners to disappear.

    D365 shows various spinners during form loads and saves.
    Waiting for them to disappear ensures the page is truly ready.
    """
    spinner_selectors = [
        "//div[contains(@class,'ms-Spinner')]",
        "//div[contains(@class,'loading')]",
        "//div[contains(@data-id,'loading')]",
        "//*[contains(@class,'progressIndicator')]",
    ]
    for xpath in spinner_selectors:
        try:
            WebDriverWait(driver, timeout).until(
                EC.invisibility_of_element_located((By.XPATH, xpath))
            )
        except Exception:
            pass  # Spinner may not exist — that's fine


def wait_for_element_stable(driver, xpath, timeout=20):
    """Wait for an element to appear AND be stable (not moving/changing).

    Useful for D365 elements that animate into position.
    Returns the element or None.
    """
    try:
        element = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.XPATH, xpath))
        )
        # Wait a moment for animation to settle
        time.sleep(0.5)
        return element
    except Exception as e:
        logger.debug("wait_for_element_stable failed for %s: %s", xpath, e)
        return None


def smart_wait(driver, timeout=45):
    """Comprehensive D365 wait — combines all wait strategies.

    Use this after any major action (navigate, save, click button).
    """
    wait_for_page_load(driver, timeout)
    wait_for_d365_spinner(driver, timeout=15)
    try:
        WebDriverWait(driver, timeout).until(
            EC.visibility_of_element_located((By.TAG_NAME, "body"))
        )
    except Exception:
        pass
    time.sleep(2)


def is_dialog_present(driver):
    """Check if any D365 dialog/modal is currently open."""
    try:
        page = driver.page_source.lower()
        return any(kw in page for kw in [
            "role=\"dialog\"", "role=\"alertdialog\"",
            "duplicate records", "unsaved changes",
            "are you sure", "confirm"
        ])
    except Exception:
        return False


def dismiss_any_dialog(driver):
    """Attempt to dismiss any open D365 dialog intelligently.

    Tries: Ignore and save → OK → Yes → Confirm → Cancel (last resort).
    Returns True if a dialog was dismissed.
    """
    if not is_dialog_present(driver):
        return False

    logger.info("Dialog detected — attempting to dismiss...")

    # Try dismiss buttons in priority order
    dismiss_xpaths = [
        "//button[contains(text(),'Ignore and save')]",
        "//button[contains(@aria-label,'Ignore and save')]",
        "//button[contains(text(),'OK')]",
        "//button[contains(text(),'Yes')]",
        "//button[contains(text(),'Confirm')]",
        "//button[contains(@aria-label,'OK')]",
        "//button[contains(@aria-label,'Yes')]",
    ]

    for xpath in dismiss_xpaths:
        try:
            btn = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, xpath))
            )
            btn.click()
            wait_for_dynamics_ready(driver)
            logger.info("Dialog dismissed using: %s", xpath)
            return True
        except Exception:
            continue

    logger.warning("Could not dismiss dialog automatically")
    return False


def get_visible_buttons(driver):
    """Return list of visible button texts on current page.

    Useful for debugging — helps understand what actions are available.
    """
    try:
        buttons = driver.find_elements(
            By.XPATH,
            "//button[not(@disabled) and not(@aria-disabled='true')]"
        )
        return [
            b.get_attribute("aria-label") or b.text
            for b in buttons
            if (b.get_attribute("aria-label") or b.text or "").strip()
        ][:20]  # Max 20
    except Exception:
        return []


def scroll_to_top(driver):
    """Scroll page back to top — useful before reading DOM."""
    try:
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(0.3)
    except Exception:
        pass


def clear_and_type(driver, element, value):
    """Reliably clear a field and type a value.

    Tries multiple clear strategies for D365 controlled inputs.
    """
    try:
        element.click()
        time.sleep(0.2)
    except Exception:
        pass

    # Strategy 1: standard clear
    try:
        element.clear()
    except Exception:
        pass

    # Strategy 2: Ctrl+A + Delete
    try:
        element.send_keys(Keys.CONTROL, "a")
        element.send_keys(Keys.DELETE)
    except Exception:
        pass

    # Strategy 3: JS clear
    try:
        driver.execute_script("arguments[0].value = '';", element)
    except Exception:
        pass

    # Now type
    element.send_keys(value)
    time.sleep(0.1)