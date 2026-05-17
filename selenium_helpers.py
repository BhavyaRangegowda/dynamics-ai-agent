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
    """Wait until document.readyState is complete."""
    try:
        WebDriverWait(driver, timeout).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
    except Exception as e:
        logger.warning("wait_for_page_load timed out: %s", e)
    time.sleep(2)


def wait_for_dynamics_ready(driver, timeout=45):
    """Wait for the Dynamics 365 page to be fully loaded and visible."""
    wait_for_page_load(driver, timeout)
    try:
        WebDriverWait(driver, timeout).until(
            EC.visibility_of_element_located((By.TAG_NAME, "body"))
        )
    except Exception as e:
        logger.warning("wait_for_dynamics_ready timed out: %s", e)
    time.sleep(3)


def capture_screenshot(driver, filename):
    """Save a screenshot to SCREENSHOT_DIR and return the full path.

    Temporarily applies 90% zoom for readability, then resets it.
    """
    wait_for_dynamics_ready(driver)
    path = os.path.join(SCREENSHOT_DIR, filename)

    try:
        driver.execute_script("document.body.style.zoom='90%'")
        time.sleep(0.5)
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
