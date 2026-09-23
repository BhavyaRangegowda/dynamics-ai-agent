import json
import logging
import urllib.request

from config import SLACK_WEBHOOK_URL

logger = logging.getLogger(__name__)


def send_slack_notification(status, total, passed, failed, report_path=None,
                             test_results=None):
    if not SLACK_WEBHOOK_URL:
        logger.warning("SLACK_WEBHOOK_URL not configured — skipping Slack.")
        return

    emoji = "✅" if failed == 0 else "❌"
    colour = "#22c55e" if failed == 0 else "#ef4444"

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"{emoji} D365 AI Test Automation — {status}"
            }
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Total:*\n{total}"},
                {"type": "mrkdwn", "text": f"*Passed:*\n✅ {passed}"},
                {"type": "mrkdwn", "text": f"*Failed:*\n❌ {failed}"},
                {"type": "mrkdwn", "text": f"*Skipped:*\n⏭️ {total - passed - failed}"},
            ]
        },
        {"type": "divider"},
    ]

    # Add per-story results
    if test_results:
        story_lines = []
        for r in test_results:
            s = str(r.get("status", ""))
            icon = "✅" if s.startswith("PASS") else ("⏭️" if s.startswith("SKIP") else "❌")
            story_lines.append(f"{icon} *{r['issue_key']}* — {s[:60]}")
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*Story Results:*\n" + "\n".join(story_lines)
            }
        })
        blocks.append({"type": "divider"})

        # Add failure analysis for failed stories
        failures = [r for r in test_results
                    if not str(r.get("status","")).startswith("PASS")
                    and not str(r.get("status","")).startswith("SKIP")
                    and r.get("failure_analysis")]

        if failures:
            fa_lines = []
            for r in failures:
                fa = r["failure_analysis"]
                cat = fa.get("category", "UNKNOWN")
                fix = fa.get("recommended_fix", "—")
                bug = f" | 🐛 Bug: {r['bug_key']}" if r.get("bug_key") else ""
                fa_lines.append(
                    f"*{r['issue_key']}* [{cat}]{bug}\n"
                    f"  _{fa.get('root_cause','—')}_\n"
                    f"  🔧 {fix[:100]}"
                )
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "🤖 *AI Failure Analysis:*\n\n" + "\n\n".join(fa_lines)
                }
            })
            blocks.append({"type": "divider"})

    if report_path:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"📊 *Report:* `{report_path}`"
            }
        })

    message = {
        "text": f"{emoji} D365 AI Test Automation — {status} ({passed}/{total} passed)",
        "attachments": [{"color": colour, "blocks": blocks}]
    }

    data = json.dumps(message).encode("utf-8")
    request = urllib.request.Request(
        SLACK_WEBHOOK_URL,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            logger.info("Slack notification sent. Status: %s", response.status)
    except Exception as e:
        logger.error("Failed to send Slack notification: %s", e)