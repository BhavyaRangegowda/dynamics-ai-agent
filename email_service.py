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
    """Build a compact inline HTML summary for the email body."""
    total = len(test_results)
    passed = sum(1 for r in test_results if str(r.get("status", "")).startswith("PASS"))
    failed = total - passed
    pass_pct = round((passed / total) * 100) if total else 0
    run_time = datetime.now().strftime("%d %B %Y at %H:%M")

    rows = ""
    for r in test_results:
        status = str(r.get("status", "UNKNOWN"))
        colour = "#22c55e" if status.startswith("PASS") else "#ef4444"
        rows += f"""
        <tr>
          <td style="padding:10px 14px;font-family:monospace;font-size:12px;color:#6366f1">{r.get("issue_key","")}</td>
          <td style="padding:10px 14px;font-size:13px;color:#374151">{r.get("summary","")}</td>
          <td style="padding:10px 14px">
            <span style="background:{colour}20;color:{colour};border:1px solid {colour}60;
                         border-radius:20px;padding:3px 12px;font-size:11px;font-weight:600">
              {"PASS" if status.startswith("PASS") else "FAIL"}
            </span>
          </td>
        </tr>"""

    return f"""
    <div style="font-family:'Segoe UI',Arial,sans-serif;max-width:640px;margin:0 auto;background:#f9fafb;padding:32px 20px">
      <div style="background:#0d0f14;border-radius:12px;padding:28px 32px;margin-bottom:20px">
        <h1 style="font-size:20px;font-weight:700;color:#fff;margin:0 0 4px">
          D365 AI Test Report
        </h1>
        <p style="font-size:12px;color:#6b7280;margin:0">Generated {run_time}</p>
      </div>

      <div style="display:flex;gap:12px;margin-bottom:20px;flex-wrap:wrap">
        {"".join(f'''
        <div style="flex:1;min-width:120px;background:#fff;border-radius:10px;padding:20px 24px;
                    border:1px solid #e5e7eb;border-top:3px solid {c}">
          <div style="font-size:11px;letter-spacing:1px;text-transform:uppercase;color:#9ca3af;margin-bottom:6px">{lbl}</div>
          <div style="font-size:32px;font-weight:700;color:{c}">{val}</div>
        </div>''' for lbl, val, c in [
            ("Total", total, "#6366f1"),
            ("Passed", passed, "#22c55e"),
            ("Failed", failed, "#ef4444"),
            ("Pass Rate", f"{pass_pct}%", "#f59e0b"),
        ])}
      </div>

      <div style="background:#fff;border-radius:10px;border:1px solid #e5e7eb;overflow:hidden;margin-bottom:20px">
        <table style="width:100%;border-collapse:collapse">
          <thead>
            <tr style="background:#f3f4f6">
              <th style="padding:10px 14px;text-align:left;font-size:11px;letter-spacing:1px;
                         text-transform:uppercase;color:#9ca3af;border-bottom:1px solid #e5e7eb">Issue</th>
              <th style="padding:10px 14px;text-align:left;font-size:11px;letter-spacing:1px;
                         text-transform:uppercase;color:#9ca3af;border-bottom:1px solid #e5e7eb">Story</th>
              <th style="padding:10px 14px;text-align:left;font-size:11px;letter-spacing:1px;
                         text-transform:uppercase;color:#9ca3af;border-bottom:1px solid #e5e7eb">Result</th>
            </tr>
          </thead>
          <tbody>{rows}</tbody>
        </table>
      </div>

      <p style="font-size:12px;color:#9ca3af;text-align:center;margin:0">
        Full HTML report with screenshots attached · Dynamics 365 AI Test Automation Agent
      </p>
    </div>"""


def send_test_report_email(test_results, report_path=None):
    """Send test results email via Outlook/Office 365 SMTP.

    Args:
        test_results: list of result dicts
        report_path: path to the HTML report file to attach (optional)

    Returns:
        True on success, False on failure.
    """
    if not all([EMAIL_SENDER, EMAIL_PASSWORD, EMAIL_RECIPIENTS]):
        logger.warning("Email not configured — skipping notification. "
                       "Set EMAIL_SENDER, EMAIL_PASSWORD, EMAIL_RECIPIENTS in .env")
        return False

    total = len(test_results)
    passed = sum(1 for r in test_results if str(r.get("status", "")).startswith("PASS"))
    failed = total - passed
    subject = (
        f"✅ D365 Test Report — {passed}/{total} Passed"
        if failed == 0
        else f"❌ D365 Test Report — {failed} Failed ({passed}/{total} Passed)"
    )

    recipients = [r.strip() for r in EMAIL_RECIPIENTS.split(",") if r.strip()]

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = EMAIL_SENDER
    msg["To"] = ", ".join(recipients)

    # Plain text fallback
    plain = f"D365 AI Test Report\nPassed: {passed}  Failed: {failed}  Total: {total}\n"
    for r in test_results:
        plain += f"\n{r.get('issue_key','')} — {r.get('status','')}"
    msg.attach(MIMEText(plain, "plain"))

    # Rich HTML body
    html_body = _build_summary_html(test_results)
    msg.attach(MIMEText(html_body, "html"))

    # Attach the full HTML report if it exists
    if report_path and os.path.exists(report_path):
        try:
            with open(report_path, "rb") as f:
                attachment = MIMEBase("application", "octet-stream")
                attachment.set_payload(f.read())
            encoders.encode_base64(attachment)
            attachment.add_header(
                "Content-Disposition",
                f'attachment; filename="{os.path.basename(report_path)}"'
            )
            msg.attach(attachment)
            logger.info("Attached report: %s", report_path)
        except Exception as e:
            logger.warning("Could not attach report file: %s", e)

    try:
        logger.info("Connecting to %s:%s...", EMAIL_SMTP_HOST, EMAIL_SMTP_PORT)
        with smtplib.SMTP(EMAIL_SMTP_HOST, int(EMAIL_SMTP_PORT), timeout=30) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_SENDER, recipients, msg.as_string())
        logger.info("Email sent successfully to: %s", ", ".join(recipients))
        return True
    except smtplib.SMTPAuthenticationError:
        logger.error("Email authentication failed — check EMAIL_SENDER and EMAIL_PASSWORD in .env")
    except smtplib.SMTPException as e:
        logger.error("SMTP error sending email: %s", e)
    except Exception as e:
        logger.error("Unexpected error sending email: %s", e)

    return False
