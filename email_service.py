import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime

from config import (
    EMAIL_SENDER,
    EMAIL_PASSWORD,
    EMAIL_RECIPIENTS,
    EMAIL_SMTP_HOST,
    EMAIL_SMTP_PORT,
)

logger = logging.getLogger(__name__)


def _build_summary_html(test_results):
    total = len(test_results)
    passed = sum(1 for r in test_results if str(r.get("status","")).startswith("PASS"))
    skipped = sum(1 for r in test_results if str(r.get("status","")).startswith("SKIP"))
    failed = total - passed - skipped
    pass_pct = round((passed / total) * 100) if total else 0
    run_time = datetime.now().strftime("%d %B %Y at %H:%M")

    # Story rows
    rows = ""
    for r in test_results:
        status = str(r.get("status", "UNKNOWN"))
        if status.startswith("PASS"):
            colour = "#22c55e"
            label = "PASS"
        elif status.startswith("SKIP"):
            colour = "#f59e0b"
            label = "SKIP"
        else:
            colour = "#ef4444"
            label = "FAIL"
        rows += f"""
        <tr style="border-bottom:1px solid #e5e7eb">
          <td style="padding:10px 14px;font-family:monospace;font-size:12px;color:#6366f1;white-space:nowrap">{r.get("issue_key","")}</td>
          <td style="padding:10px 14px;font-size:12px;color:#374151">{r.get("summary","")[:70]}</td>
          <td style="padding:10px 14px;white-space:nowrap">
            <span style="background:{colour}20;color:{colour};border:1px solid {colour}60;
                         border-radius:20px;padding:3px 12px;font-size:11px;font-weight:600">{label}</span>
          </td>
        </tr>"""

    # Failure analysis rows
    failure_rows = ""
    failures = [r for r in test_results
                if not str(r.get("status","")).startswith("PASS")
                and not str(r.get("status","")).startswith("SKIP")
                and r.get("failure_analysis")]

    failure_section = ""
    if failures:
        for r in failures:
            fa = r.get("failure_analysis", {})
            cat = fa.get("category", "UNKNOWN")
            cat_colours = {
                "LOCATOR_CHANGED": "#f59e0b",
                "TIMING_ISSUE": "#3b82f6",
                "ENVIRONMENT_ISSUE": "#8b5cf6",
                "PRODUCT_BUG": "#ef4444",
                "TEST_DATA_ISSUE": "#f97316",
                "AUTH_ISSUE": "#ec4899",
                "UNKNOWN": "#6b7280",
            }
            cc = cat_colours.get(cat, "#6b7280")
            bug_note = f"<br><strong>🐛 Jira Bug Created:</strong> {r['bug_key']}" if r.get("bug_key") else ""
            failure_rows += f"""
            <tr style="background:#fff8f8;border-bottom:1px solid #fecaca">
              <td style="padding:12px 14px;vertical-align:top">
                <span style="font-family:monospace;font-size:12px;color:#6366f1">{r.get("issue_key","")}</span>
                <span style="margin-left:8px;background:{cc}20;color:{cc};border:1px solid {cc}40;
                             border-radius:20px;padding:2px 8px;font-size:10px">{cat}</span>
              </td>
              <td style="padding:12px 14px;font-size:12px;color:#374151">
                <strong>Root Cause:</strong> {fa.get("root_cause","—")}<br>
                <strong>Likely Reason:</strong> {fa.get("likely_reason","—")}<br>
                <strong style="color:#16a34a">🔧 Fix:</strong> {fa.get("recommended_fix","—")}<br>
                <strong style="color:#dc2626">⚠️ Impact:</strong> {fa.get("business_impact","—")}
                {bug_note}
              </td>
            </tr>"""

        failure_section = f"""
        <h3 style="font-size:14px;font-weight:600;color:#dc2626;margin:24px 0 12px">
            🤖 AI Failure Analysis
        </h3>
        <div style="background:#fff;border-radius:10px;border:1px solid #fecaca;overflow:hidden;margin-bottom:20px">
            <table style="width:100%;border-collapse:collapse">
                <thead>
                    <tr style="background:#fef2f2">
                        <th style="padding:10px 14px;text-align:left;font-size:11px;color:#9ca3af;
                                   text-transform:uppercase;letter-spacing:1px;width:150px">Issue</th>
                        <th style="padding:10px 14px;text-align:left;font-size:11px;color:#9ca3af;
                                   text-transform:uppercase;letter-spacing:1px">Analysis</th>
                    </tr>
                </thead>
                <tbody>{failure_rows}</tbody>
            </table>
        </div>"""

    return f"""
    <div style="font-family:'Segoe UI',Arial,sans-serif;max-width:700px;margin:0 auto;background:#f9fafb;padding:32px 20px">
      <div style="background:#0d0f14;border-radius:12px;padding:28px 32px;margin-bottom:20px">
        <h1 style="font-size:22px;font-weight:700;color:#fff;margin:0 0 4px">D365 AI Test Report</h1>
        <p style="font-size:12px;color:#6b7280;margin:0">Generated {run_time}</p>
      </div>

      <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:20px">
        {"".join(f'''<div style="background:#fff;border-radius:10px;padding:16px;border:1px solid #e5e7eb;border-top:3px solid {c}">
          <div style="font-size:10px;letter-spacing:1px;text-transform:uppercase;color:#9ca3af;margin-bottom:6px">{lbl}</div>
          <div style="font-size:28px;font-weight:700;color:{c}">{val}</div>
        </div>''' for lbl, val, c in [
            ("Total", total, "#6366f1"),
            ("Passed", passed, "#22c55e"),
            ("Failed", failed, "#ef4444"),
            ("Skipped", skipped, "#f59e0b"),
        ])}
      </div>

      <div style="background:#fff;border-radius:10px;border:1px solid #e5e7eb;overflow:hidden;margin-bottom:20px">
        <table style="width:100%;border-collapse:collapse">
          <thead>
            <tr style="background:#f3f4f6">
              <th style="padding:10px 14px;text-align:left;font-size:11px;letter-spacing:1px;text-transform:uppercase;color:#9ca3af">Issue</th>
              <th style="padding:10px 14px;text-align:left;font-size:11px;letter-spacing:1px;text-transform:uppercase;color:#9ca3af">Story</th>
              <th style="padding:10px 14px;text-align:left;font-size:11px;letter-spacing:1px;text-transform:uppercase;color:#9ca3af">Result</th>
            </tr>
          </thead>
          <tbody>{rows}</tbody>
        </table>
      </div>

      {failure_section}

      <p style="font-size:12px;color:#9ca3af;text-align:center;margin:0">
        Full HTML report attached · Dynamics 365 AI Test Automation Agent
      </p>
    </div>"""


def send_test_report_email(test_results, report_path=None):
    if not all([EMAIL_SENDER, EMAIL_PASSWORD, EMAIL_RECIPIENTS]):
        logger.warning("Email not configured — skipping.")
        return False

    total = len(test_results)
    passed = sum(1 for r in test_results if str(r.get("status","")).startswith("PASS"))
    skipped = sum(1 for r in test_results if str(r.get("status","")).startswith("SKIP"))
    failed = total - passed - skipped

    subject = (
        f"✅ D365 Test Report — {passed}/{total} Passed"
        if failed == 0
        else f"❌ D365 Test Report — {failed} Failed | {passed} Passed | {skipped} Skipped"
    )

    recipients = [r.strip() for r in EMAIL_RECIPIENTS.split(",") if r.strip()]
    msg = MIMEMultipart("mixed")
    msg["Subject"] = subject
    msg["From"] = EMAIL_SENDER
    msg["To"] = ", ".join(recipients)

    # Plain text fallback
    plain = f"D365 AI Test Report\nPassed:{passed} Failed:{failed} Skipped:{skipped} Total:{total}\n"
    for r in test_results:
        plain += f"\n{r.get('issue_key','')} — {r.get('status','')}"
        if r.get("failure_analysis"):
            fa = r["failure_analysis"]
            plain += f"\n  Category: {fa.get('category','')}"
            plain += f"\n  Fix: {fa.get('recommended_fix','')}"
    msg.attach(MIMEText(plain, "plain"))
    msg.attach(MIMEText(_build_summary_html(test_results), "html"))

    # Attach HTML report
    if report_path and os.path.exists(report_path):
        try:
            with open(report_path, "rb") as f:
                att = MIMEBase("application", "octet-stream")
                att.set_payload(f.read())
            encoders.encode_base64(att)
            att.add_header("Content-Disposition",
                           f'attachment; filename="{os.path.basename(report_path)}"')
            msg.attach(att)
            logger.info("Attached: %s", report_path)
        except Exception as e:
            logger.warning("Could not attach report: %s", e)

    try:
        with smtplib.SMTP(EMAIL_SMTP_HOST, int(EMAIL_SMTP_PORT), timeout=30) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_SENDER, recipients, msg.as_string())
        logger.info("Email sent to: %s", ", ".join(recipients))
        return True
    except smtplib.SMTPAuthenticationError:
        logger.error("Email auth failed")
    except Exception as e:
        logger.error("Email error: %s", e)
    return False