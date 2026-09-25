import os

import json

import logging

import time
import sys

# ---------------------------------------------------------------------------
# UTF-8 console safety
# ---------------------------------------------------------------------------
# Azure DevOps self-hosted Windows agents may use a legacy console encoding.
# Force UTF-8 so Unicode symbols in logs/summaries cannot crash the run.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")



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

    ConfigError,

    validate_environment,

)

from selenium_helpers import (

    wait_for_page_load,

    wait_for_dynamics_ready,

    smart_wait,

    capture_screenshot,

    click_element,

    dismiss_any_dialog,

)

from ai_agent import ai_generate_test_cases, ai_decide_workflow

from dynamics_workflows import execute_ai_workflow

from jira_service import (

    create_jira_client,

    fetch_user_stories,

    post_result_to_jira,

    create_jira_bug,

)

from zephyr_service import post_test_result, reset_cycle_cache

from report_generator import generate_html_report

from email_service import send_test_report_email

from slack_service import send_slack_notification

from failure_analysis_service import analyze_failure_with_ai

from story_change_service import (

    detect_story_changes,

    save_story_hashes,

    should_regenerate,

    get_change_summary,

)



# ---------------------------------------------------------------------------

# Logging

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



        # Reuse a dedicated Chrome profile on the self-hosted agent.

        # This allows Microsoft authentication cookies/session state to persist

        # between automation runs.

        chrome_profile = os.getenv(

            "D365_CHROME_PROFILE",

            r"C:**\U**sers\bhavy\d365-automation-chrome"

        )



        options.add_argument(f"--user-data-dir={chrome_profile}")

        options.add_argument("--profile-directory=Default")



        logger.info(

            "Using persistent D365 Chrome profile: %s",

            chrome_profile

        )



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

    logger.info("Opening Dynamics 365...")

    driver.get(DYNAMICS_URL)

    wait_for_page_load(driver)



    # ---------------------------------------------------------------

    # Reuse existing authenticated Microsoft session when available.

    # ---------------------------------------------------------------

    try:

        WebDriverWait(driver, 8).until(

            lambda d:

                "login.microsoftonline.com" not in d.current_url.lower()

                and "login.live.com" not in d.current_url.lower()

        )



        if "login.microsoftonline.com" not in driver.current_url.lower():

            logger.info(

                "Existing Microsoft authentication session detected — "

                "skipping username/password/MFA login"

            )



            smart_wait(driver)

            capture_screenshot(driver, "00_login_success.png")

            return



    except Exception:

        logger.info(

            "No reusable Microsoft session detected — performing normal login"

        )



    # ---------------------------------------------------------------

    # Normal Microsoft login

    # ---------------------------------------------------------------

    logger.info("Logging into Dynamics 365...")



    WebDriverWait(driver, 20).until(

        EC.presence_of_element_located((By.NAME, "loginfmt"))

    )



    driver.find_element(By.NAME, "loginfmt").send_keys(DYNAMICS_USERNAME)

    click_element(driver, "login_next", "Login Next")

    time.sleep(2)



    WebDriverWait(driver, 20).until(

        EC.presence_of_element_located((By.NAME, "passwd"))

    )



    driver.find_element(By.NAME, "passwd").send_keys(DYNAMICS_PASSWORD)

    click_element(driver, "login_next", "Sign In")



    logger.info(

        "Waiting %d seconds for MFA approval — check your phone!",

        MFA_WAIT_SECONDS

    )



    time.sleep(MFA_WAIT_SECONDS)



    # Microsoft may display the Stay signed in prompt on the first

    # authentication for this persistent Chrome profile.

    try:

        click_element(

            driver,

            "login_next",

            "Stay Signed In",

            timeout=8

        )

        logger.info("Accepted Microsoft Stay Signed In prompt")

    except Exception:

        logger.info("No 'Stay signed in' prompt appeared")



    smart_wait(driver)



    logger.info("Login successful")

    capture_screenshot(driver, "00_login_success.png")





# ---------------------------------------------------------------------------

# Summary helpers

# ---------------------------------------------------------------------------



def _calculate_summary(test_results):

    """Calculate pass/fail/skip counts correctly.



    SKIP stories are NOT counted as failures.

    """

    total = len(test_results)

    passed = sum(1 for r in test_results if str(r["status"]).startswith("PASS"))

    skipped = sum(1 for r in test_results if str(r["status"]).startswith("SKIP"))

    failed = total - passed - skipped

    overall = "PASSED" if failed == 0 else "FAILED"

    return overall, total, passed, failed, skipped





def _print_summary(test_results):

    print("\n" + "=" * 75)

    print(f"{'ISSUE':<12} {'STATUS':<40} SCREENSHOT")

    print("-" * 75)



    for r in test_results:

        status = r["status"]

        # Truncate long status for display

        display_status = status[:38] + ".." if len(status) > 40 else status

        screenshot = r.get("screenshot") or "—"

        print(f"{r['issue_key']:<12} {display_status:<40} {screenshot}")



    overall, total, passed, failed, skipped = _calculate_summary(test_results)

    print("=" * 75)

    print(

        f"Total: {total}  |  "

        f"Passed: {passed}  |  "

        f"Failed: {failed}  |  "

        f"Skipped: {skipped}"

    )

    print(f"Overall Status: {overall}")

    print("=" * 75 + "\n")



    # Print auto-created bugs

    bugs = [r for r in test_results if r.get("bug_key")]

    if bugs:

        print("Auto-created Jira bugs:")

        for r in bugs:

            print(f"  {r['bug_key']} ← {r['issue_key']}: {r['status'][:50]}")

        print()





def _send_notifications(test_results, report_path):

    overall, total, passed, failed, skipped = _calculate_summary(test_results)



    logger.info("Sending email notification...")

    send_test_report_email(test_results, report_path=report_path)



    logger.info("Sending Slack notification...")

    send_slack_notification(

        status=overall,

        total=total,

        passed=passed,

        failed=failed,

        report_path=report_path,

        test_results=test_results,

    )





# ---------------------------------------------------------------------------

# Main

# ---------------------------------------------------------------------------



def main():

    print("=" * 60)

    print("AI-POWERED DYNAMICS 365 TEST AUTOMATION AGENT")

    print("=" * 60)



    try:

        validate_environment()

    except ConfigError as error:

        logger.error("Configuration invalid: %s", error)

        return



    jira_client = create_jira_client()

    groq_client = Groq(api_key=GROQ_API_KEY)

    reset_cycle_cache()



    driver = _build_driver()

    test_results = []

    report_path = None



    try:

        login_to_dynamics(driver)



        # ── Step 1: Pull user stories ─────────────────────────────────────────





        logger.info("[STEP 1] Pulling user stories from Jira...")

        issues = fetch_user_stories(jira_client)



        logger.info("Found %d user stories", len(issues))





        if not issues:

                    logger.warning("No user stories found — check PROJECT_KEY in .env")

                    return



        # ── Step 2: Detect story changes ──────────────────────────────────────

        logger.info("[STEP 2] Detecting story changes since last run...")

        change_result = detect_story_changes(issues)

        print(get_change_summary(change_result))



        # ── Step 3: Process each story ────────────────────────────────────────

        for issue in issues:

            logger.info(

                "[PROCESSING] %s: %s",

                issue.key,

                issue.fields.summary

            )



            is_changed = should_regenerate(issue.key, change_result)

            if is_changed:

                logger.info("  Story is NEW or CHANGED — regenerating")

            else:

                logger.info("  Story unchanged since last run")



            # Dismiss any leftover dialogs from previous story

            dismiss_any_dialog(driver)



            # Build the complete Jira requirement so AI uses both the story

            # summary and the detailed description / acceptance criteria.

            requirement_text = (

                f"{issue.fields.summary}\n\n"

                f"{getattr(issue.fields, 'description', '') or ''}"

            )



            # Generate AI test cases from the complete Jira requirement

            logger.info("  Generating AI test cases...")

            test_cases = ai_generate_test_cases(groq_client, requirement_text)



            # Classify workflow intent from the complete Jira requirement

            logger.info("  Classifying workflow intent...")

            ai_plan = ai_decide_workflow(groq_client, requirement_text)



            # Pass the complete requirement to dynamic step generation

            ai_plan["summary"] = requirement_text



            logger.info(

                "  Workflow: %s | Entity: %s",

                ai_plan.get("workflow"),

                ai_plan.get("entity")

            )



            # Execute — fully dynamic, AI reads DOM and generates steps

            test_status, screenshot_path = execute_ai_workflow(

                driver,

                issue.key,

                ai_plan,

                groq_client=groq_client,

            )



            # ── Handle SKIP ───────────────────────────────────────────────────

            failure_analysis = None

            bug_key = None



            if str(test_status).startswith("SKIP"):

                logger.warning(

                    "  [%s] SKIPPED — %s",

                    issue.key, test_status

                )

                # Don't post to Jira/Zephyr for skipped stories

                # Post SKIP result to Zephyr / Jira so the execution is traceable

                logger.info("  Posting SKIP result to Zephyr/Jira...")

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

                    "failure_analysis": None,

                    "bug_key": None,

                    "story_changed": is_changed,

                })

                logger.info("  Completed: %s → %s", issue.key, test_status)

                continue



            # ── AI Failure Analysis (for real failures only) ──────────────────

            elif not str(test_status).startswith("PASS"):

                logger.info("  Test FAILED — running AI failure analysis...")

                failure_analysis = analyze_failure_with_ai(

                    groq_client=groq_client,

                    issue_key=issue.key,

                    summary=issue.fields.summary,

                    error_message=test_status,

                    screenshot_path=screenshot_path,

                    requirement_text=requirement_text,

                )

                logger.info(

                    "  Category: %s",

                    failure_analysis.get("category", "UNKNOWN")

                )

                logger.info(

                    "  Root cause: %s",

                    failure_analysis.get("root_cause", "—")

                )

                logger.info(

                    "  Fix: %s",

                    failure_analysis.get("recommended_fix", "—")

                )



                # ── Auto Jira Bug Creation ────────────────────────────────────

                if failure_analysis.get("create_bug"):

                    logger.info(

                        "  AI identified PRODUCT BUG — auto-creating Jira bug..."

                    )

                    bug_key = create_jira_bug(

                        jira_client=jira_client,

                        parent_issue_key=issue.key,

                        summary=issue.fields.summary,

                        failure_analysis=failure_analysis,

                        test_status=test_status,

                        screenshot_path=screenshot_path,

                    )

                    if bug_key:

                        logger.info("  Jira bug created: %s", bug_key)



            # ── Post results to Zephyr / Jira ─────────────────────────────────

            logger.info("  Posting result to Zephyr/Jira...")

            post_test_result(

                issue_key=issue.key,

                summary=issue.fields.summary,

                test_cases=test_cases,

                ai_plan=ai_plan,

                test_status=test_status,

                screenshot_path=screenshot_path,

            )



            # Post detailed failure analysis as separate Jira comment

            if failure_analysis:

                post_result_to_jira(

                    jira_client=jira_client,

                    issue_key=issue.key,

                    test_cases=test_cases,

                    ai_plan=ai_plan,

                    test_status=test_status,

                    screenshot_path=screenshot_path,

                    failure_analysis=failure_analysis,

                )



            test_results.append({

                "issue_key": issue.key,

                "summary": issue.fields.summary,

                "ai_plan": ai_plan,

                "test_cases": test_cases,

                "status": test_status,

                "screenshot": screenshot_path,

                "failure_analysis": failure_analysis,

                "bug_key": bug_key,

                "story_changed": is_changed,

            })



            logger.info("  Completed: %s → %s", issue.key, test_status)



        # ── Step 4: Save raw results ──────────────────────────────────────────

        logger.info("[STEP 4] Saving test_results.json...")

        with open("test_results.json", "w") as f:

            json.dump(test_results, f, indent=2, default=str)



        # ── Step 5: Save story hashes for next run ────────────────────────────

        logger.info("[STEP 5] Saving story hashes...")

        save_story_hashes(change_result)



        # ── Step 6: Generate HTML report ──────────────────────────────────────

        logger.info("[STEP 6] Generating HTML report...")

        report_path = generate_html_report(

            test_results, output_path="test_report.html"

        )

        if report_path:

            logger.info("HTML report saved: %s", report_path)

        else:

            logger.warning("HTML report generation failed")



        # ── Step 7: Print console summary ─────────────────────────────────────

        _print_summary(test_results)

        logger.info("Screenshots saved in: %s", SCREENSHOT_DIR)



        # ── Step 8: Send notifications ────────────────────────────────────────

        logger.info("[STEP 8] Sending notifications...")

        _send_notifications(test_results, report_path)



    except Exception as e:

        logger.error("Fatal error: %s: %s", type(e).__name__, e)

        try:

            capture_screenshot(driver, "fatal_error.png", quick=True)

        except Exception:

            pass

        if test_results:

            logger.info("Generating partial failure report...")

            report_path = generate_html_report(

                test_results, output_path="test_report.html"

            )

            _send_notifications(test_results, report_path)



    finally:

        time.sleep(2)

        driver.quit()





if __name__ == "__main__":

    main()