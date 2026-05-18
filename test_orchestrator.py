import os
import json
import logging
import time

from groq import Groq
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

from config import (
    GROQ_API_KEY,
    DYNAMICS_URL,
    DYNAMICS_USERNAME,
    DYNAMICS_PASSWORD,
    SCREENSHOT_DIR,
    MFA_WAIT_SECONDS,
)

from selenium_helpers import (
    wait_for_page_load,
    wait_for_dynamics_ready,
    capture_screenshot,
    click_element,
)

from ai_agent import ai_generate_test_cases, ai_decide_workflow
from dynamics_workflows import execute_ai_workflow
from jira_service import create_jira_client, fetch_user_stories
from zephyr_service import post_test_result, reset_cycle_cache
from report_generator import generate_html_report
from email_service import send_test_report_email


# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Browser setup
# ---------------------------------------------------------------------------

def _build_driver():
    options = webdriver.ChromeOptions()

    # Default local execution = visible browser
    # Azure hosted pipeline can override using HEADLESS=true
    headless = os.getenv("HEADLESS", "false").lower() == "true"

    if headless:
        logger.info("Running browser in HEADLESS mode")

        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--remote-debugging-port=9222")

    else:
        logger.info("Running browser in VISIBLE mode")

        options.add_argument("--start-maximized")

    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-popup-blocking")

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options,
    )

    driver.set_window_size(1920, 1080)

    return driver


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------

def login_to_dynamics(driver):
    logger.info("Logging into Dynamics 365...")

    driver.get(DYNAMICS_URL)

    wait_for_page_load(driver)

    WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.NAME, "loginfmt"))
    )

    driver.find_element(By.NAME, "loginfmt").send_keys(
        DYNAMICS_USERNAME
    )

    click_element(driver, "login_next", "Login Next")

    time.sleep(2)

    WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.NAME, "passwd"))
    )

    driver.find_element(By.NAME, "passwd").send_keys(
        DYNAMICS_PASSWORD
    )

    click_element(driver, "login_next", "Sign In")

    logger.info(
        "Waiting %d seconds for MFA approval — check your phone!",
        MFA_WAIT_SECONDS,
    )

    time.sleep(MFA_WAIT_SECONDS)

    try:
        click_element(
            driver,
            "login_next",
            "Stay Signed In",
            timeout=8,
        )

    except Exception:
        logger.info("No 'Stay signed in' prompt appeared")

    wait_for_dynamics_ready(driver)

    logger.info("Login successful")

    capture_screenshot(driver, "00_login_success.png")


# ---------------------------------------------------------------------------
# Results summary
# ---------------------------------------------------------------------------

def _print_summary(test_results):

    print("\n" + "=" * 70)

    print(f"{'ISSUE':<12} {'STATUS':<45} {'SCREENSHOT'}")

    print("-" * 70)

    for r in test_results:

        status = r["status"]

        screenshot = r.get("screenshot", "—")

        print(
            f"{r['issue_key']:<12} "
            f"{status:<45} "
            f"{screenshot}"
        )

    print("=" * 70)

    passed = sum(
        1 for r in test_results
        if str(r["status"]).startswith("PASS")
    )

    failed = len(test_results) - passed

    print(
        f"Total: {len(test_results)}  |  "
        f"Passed: {passed}  |  "
        f"Failed: {failed}"
    )

    print("=" * 70 + "\n")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():

    print("=" * 60)
    print("AI-POWERED DYNAMICS 365 TEST AUTOMATION AGENT")
    print("=" * 60)

    jira_client = create_jira_client()

    groq_client = Groq(api_key=GROQ_API_KEY)

    # Fresh Zephyr cycle
    reset_cycle_cache()

    driver = _build_driver()

    test_results = []

    try:

        # -------------------------------------------------------------------
        # Step 1 - Login
        # -------------------------------------------------------------------

        login_to_dynamics(driver)

        # -------------------------------------------------------------------
        # Step 2 - Pull Jira stories
        # -------------------------------------------------------------------

        logger.info("[STEP 1] Pulling user stories from Jira...")

        issues = fetch_user_stories(jira_client)

        logger.info("Found %d user stories", len(issues))

        # -------------------------------------------------------------------
        # Step 3 - Process each story
        # -------------------------------------------------------------------

        for issue in issues:

            logger.info(
                "[PROCESSING] %s: %s",
                issue.key,
                issue.fields.summary,
            )

            logger.info("Generating AI test cases...")

            test_cases = ai_generate_test_cases(
                groq_client,
                issue.fields.summary,
            )

            logger.info("Generating AI workflow plan...")

            ai_plan = ai_decide_workflow(
                groq_client,
                issue.fields.summary,
            )

            logger.info(
                "AI plan: %s",
                json.dumps(ai_plan, indent=2),
            )

            test_status, screenshot_path = execute_ai_workflow(
                driver,
                issue.key,
                ai_plan,
            )

            logger.info("Posting result to Zephyr/Jira...")

            post_test_result(
                issue_key=issue.key,
                summary=issue.fields.summary,
                test_cases=test_cases,
                ai_plan=ai_plan,
                test_status=test_status,
                screenshot_path=screenshot_path,
            )

            test_results.append({
                "issue_key": issue.key,
                "summary": issue.fields.summary,
                "ai_plan": ai_plan,
                "test_cases": test_cases,
                "status": test_status,
                "screenshot": screenshot_path,
            })

            logger.info(
                "Completed: %s → %s",
                issue.key,
                test_status,
            )

        # -------------------------------------------------------------------
        # Step 4 - Save JSON
        # -------------------------------------------------------------------

        logger.info(
            "[STEP 3] Saving test results to test_results.json..."
        )

        with open("test_results.json", "w") as f:
            json.dump(test_results, f, indent=2)

        # -------------------------------------------------------------------
        # Step 5 - Generate HTML report
        # -------------------------------------------------------------------

        logger.info("[STEP 4] Generating HTML report...")

        report_path = generate_html_report(
            test_results,
            output_path="test_report.html",
        )

        if report_path:
            logger.info("HTML report saved: %s", report_path)
        else:
            logger.warning("HTML report generation failed")

        # -------------------------------------------------------------------
        # Step 6 - Console summary
        # -------------------------------------------------------------------

        _print_summary(test_results)

        logger.info(
            "Screenshots saved in: %s",
            SCREENSHOT_DIR,
        )

        # -------------------------------------------------------------------
        # Step 7 - Email notification
        # -------------------------------------------------------------------

        logger.info("[STEP 6] Sending email notification...")

        send_test_report_email(
            test_results,
            report_path=report_path,
        )

    except Exception as e:

        logger.error(
            "Fatal error: %s: %s",
            type(e).__name__,
            e,
        )

        try:
            capture_screenshot(driver, "fatal_error.png")
        except Exception:
            pass

        # Send partial results if available
        if test_results:

            logger.info("Sending partial results email...")

            report_path = generate_html_report(
                test_results,
                output_path="test_report.html",
            )

            send_test_report_email(
                test_results,
                report_path=report_path,
            )

    finally:

        time.sleep(3)

        driver.quit()


if __name__ == "__main__":
    main()