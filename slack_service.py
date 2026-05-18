import json
import logging
import urllib.request

from config import SLACK_WEBHOOK_URL

logger = logging.getLogger(__name__)


def send_slack_notification(status, total, passed, failed, report_path=None):
    if not SLACK_WEBHOOK_URL:
        logger.warning("SLACK_WEBHOOK_URL is not configured. Skipping Slack notification.")
        return

    emoji = "✅" if failed == 0 else "❌"

    message = {
        "text": f"{emoji} Dynamics AI Automation Run Completed",
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"{emoji} *Dynamics AI Automation Run Completed*"
                }
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Status:*\n{status}"},
                    {"type": "mrkdwn", "text": f"*Total Tests:*\n{total}"},
                    {"type": "mrkdwn", "text": f"*Passed:*\n{passed}"},
                    {"type": "mrkdwn", "text": f"*Failed:*\n{failed}"},
                ],
            },
        ],
    }

    if report_path:
        message["blocks"].append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Report Generated:*\n`{report_path}`"
            }
        })

    data = json.dumps(message).encode("utf-8")

    request = urllib.request.Request(
        SLACK_WEBHOOK_URL,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            logger.info("Slack notification sent. Status code: %s", response.status)
    except Exception as e:
        logger.error("Failed to send Slack notification: %s", e)