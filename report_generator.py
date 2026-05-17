import base64
import logging
import os
from datetime import datetime

logger = logging.getLogger(__name__)


def _encode_image(path):
    """Base64-encode a screenshot for embedding in HTML."""
    if not path or not os.path.exists(path):
        return None
    try:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    except Exception as e:
        logger.warning("Could not encode screenshot %s: %s", path, e)
        return None


def _status_class(status):
    if str(status).startswith("PASS"):
        return "pass"
    if str(status).startswith("FAIL"):
        return "fail"
    return "partial"


def generate_html_report(test_results, output_path="test_report.html"):
    """Generate a rich HTML dashboard report from test results.

    Args:
        test_results: list of dicts with keys:
            issue_key, summary, status, screenshot, test_cases, ai_plan
        output_path: where to write the HTML file

    Returns:
        The output_path on success, None on failure.
    """
    if not test_results:
        logger.warning("No test results to generate report from")
        return None

    total = len(test_results)
    passed = sum(1 for r in test_results if str(r.get("status", "")).startswith("PASS"))
    failed = total - passed
    pass_pct = round((passed / total) * 100) if total else 0
    run_time = datetime.now().strftime("%d %B %Y at %H:%M")

    # Build result rows
    rows_html = ""
    cards_html = ""

    for r in test_results:
        key = r.get("issue_key", "—")
        summary = r.get("summary", "—")
        status = r.get("status", "UNKNOWN")
        screenshot = r.get("screenshot", "")
        test_cases = r.get("test_cases", "")
        ai_plan = r.get("ai_plan", {})
        sc = _status_class(status)
        img_b64 = _encode_image(screenshot)
        img_html = (
            f'<img src="data:image/png;base64,{img_b64}" alt="Screenshot for {key}" class="screenshot">'
            if img_b64 else '<div class="no-screenshot">No screenshot available</div>'
        )

        workflow = ai_plan.get("workflow", "—") if isinstance(ai_plan, dict) else "—"

        # Table row
        rows_html += f"""
        <tr class="row-{sc}">
            <td><span class="issue-key">{key}</span></td>
            <td>{summary}</td>
            <td><span class="workflow-badge">{workflow}</span></td>
            <td><span class="status-badge {sc}">{status}</span></td>
        </tr>"""

        # Detail card
        tc_html = test_cases.replace("\n", "<br>") if test_cases else "—"
        cards_html += f"""
        <div class="detail-card">
            <div class="card-header {sc}">
                <div class="card-title">
                    <span class="issue-key">{key}</span>
                    <span class="card-summary">{summary}</span>
                </div>
                <span class="status-badge {sc}">{status}</span>
            </div>
            <div class="card-body">
                <div class="card-left">
                    <h4>AI Generated Test Cases</h4>
                    <div class="test-cases">{tc_html}</div>
                    <h4>Workflow Executed</h4>
                    <div class="workflow-detail">{workflow}</div>
                </div>
                <div class="card-right">
                    <h4>Evidence Screenshot</h4>
                    {img_html}
                </div>
            </div>
        </div>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>D365 AI Test Report — {run_time}</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
  @import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Syne:wght@400;600;800&family=DM+Sans:wght@300;400;500&display=swap');

  :root {{
    --bg: #0d0f14;
    --surface: #13161e;
    --surface2: #1a1e2a;
    --border: #252a38;
    --text: #e8eaf0;
    --muted: #6b7280;
    --pass: #22c55e;
    --pass-bg: #052e16;
    --fail: #ef4444;
    --fail-bg: #2d0a0a;
    --partial: #f59e0b;
    --partial-bg: #2d1f00;
    --accent: #6366f1;
    --accent2: #818cf8;
  }}

  * {{ box-sizing: border-box; margin: 0; padding: 0; }}

  body {{
    background: var(--bg);
    color: var(--text);
    font-family: 'DM Sans', sans-serif;
    font-size: 14px;
    line-height: 1.6;
    min-height: 100vh;
  }}

  /* ── Header ── */
  .header {{
    background: linear-gradient(135deg, #0d0f14 0%, #13161e 50%, #1a1e2a 100%);
    border-bottom: 1px solid var(--border);
    padding: 40px 48px 32px;
    position: relative;
    overflow: hidden;
  }}
  .header::before {{
    content: '';
    position: absolute;
    top: -80px; right: -80px;
    width: 300px; height: 300px;
    background: radial-gradient(circle, rgba(99,102,241,0.15) 0%, transparent 70%);
    pointer-events: none;
  }}
  .header-top {{
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 24px;
    flex-wrap: wrap;
  }}
  .header h1 {{
    font-family: 'Syne', sans-serif;
    font-size: 28px;
    font-weight: 800;
    letter-spacing: -0.5px;
    color: #fff;
  }}
  .header h1 span {{ color: var(--accent2); }}
  .run-meta {{
    font-family: 'DM Mono', monospace;
    font-size: 12px;
    color: var(--muted);
    margin-top: 6px;
  }}
  .header-badge {{
    background: var(--surface2);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 8px 16px;
    font-family: 'DM Mono', monospace;
    font-size: 12px;
    color: var(--muted);
    white-space: nowrap;
  }}

  /* ── Layout ── */
  .container {{ max-width: 1200px; margin: 0 auto; padding: 40px 48px; }}

  /* ── KPI cards ── */
  .kpi-row {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 16px;
    margin-bottom: 40px;
  }}
  .kpi {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 24px;
    position: relative;
    overflow: hidden;
  }}
  .kpi::after {{
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
    border-radius: 12px 12px 0 0;
  }}
  .kpi.total::after {{ background: var(--accent); }}
  .kpi.passed::after {{ background: var(--pass); }}
  .kpi.failed::after {{ background: var(--fail); }}
  .kpi.rate::after {{ background: var(--partial); }}
  .kpi-label {{
    font-size: 11px;
    font-weight: 500;
    letter-spacing: 1px;
    text-transform: uppercase;
    color: var(--muted);
    margin-bottom: 10px;
  }}
  .kpi-value {{
    font-family: 'Syne', sans-serif;
    font-size: 40px;
    font-weight: 800;
    line-height: 1;
    color: #fff;
  }}
  .kpi.passed .kpi-value {{ color: var(--pass); }}
  .kpi.failed .kpi-value {{ color: var(--fail); }}
  .kpi.rate .kpi-value {{ color: var(--partial); }}

  /* ── Charts row ── */
  .charts-row {{
    display: grid;
    grid-template-columns: 280px 1fr;
    gap: 20px;
    margin-bottom: 40px;
  }}
  .chart-card {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 24px;
  }}
  .chart-card h3 {{
    font-family: 'Syne', sans-serif;
    font-size: 14px;
    font-weight: 600;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 20px;
  }}
  .donut-wrap {{
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 20px;
  }}
  canvas {{ max-width: 100%; }}
  .legend {{ display: flex; flex-direction: column; gap: 8px; width: 100%; }}
  .legend-item {{ display: flex; align-items: center; gap: 10px; font-size: 13px; }}
  .legend-dot {{ width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }}

  /* ── Table ── */
  .section-title {{
    font-family: 'Syne', sans-serif;
    font-size: 18px;
    font-weight: 600;
    margin-bottom: 16px;
    color: #fff;
  }}
  .table-wrap {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    overflow: hidden;
    margin-bottom: 40px;
  }}
  table {{ width: 100%; border-collapse: collapse; }}
  thead th {{
    background: var(--surface2);
    padding: 14px 20px;
    text-align: left;
    font-size: 11px;
    font-weight: 500;
    letter-spacing: 1px;
    text-transform: uppercase;
    color: var(--muted);
    border-bottom: 1px solid var(--border);
  }}
  tbody tr {{
    border-bottom: 1px solid var(--border);
    transition: background 0.15s;
  }}
  tbody tr:last-child {{ border-bottom: none; }}
  tbody tr:hover {{ background: var(--surface2); }}
  tbody td {{ padding: 14px 20px; vertical-align: middle; }}

  /* ── Badges ── */
  .issue-key {{
    font-family: 'DM Mono', monospace;
    font-size: 12px;
    background: var(--surface2);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 3px 8px;
    color: var(--accent2);
  }}
  .workflow-badge {{
    font-family: 'DM Mono', monospace;
    font-size: 11px;
    background: var(--surface2);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 3px 8px;
    color: var(--muted);
  }}
  .status-badge {{
    display: inline-block;
    font-size: 11px;
    font-weight: 500;
    border-radius: 20px;
    padding: 3px 12px;
    letter-spacing: 0.3px;
  }}
  .status-badge.pass {{ background: var(--pass-bg); color: var(--pass); border: 1px solid rgba(34,197,94,0.3); }}
  .status-badge.fail {{ background: var(--fail-bg); color: var(--fail); border: 1px solid rgba(239,68,68,0.3); }}
  .status-badge.partial {{ background: var(--partial-bg); color: var(--partial); border: 1px solid rgba(245,158,11,0.3); }}

  /* ── Detail cards ── */
  .detail-card {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    overflow: hidden;
    margin-bottom: 20px;
  }}
  .card-header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 16px 24px;
    border-bottom: 1px solid var(--border);
    gap: 12px;
    flex-wrap: wrap;
  }}
  .card-header.pass {{ border-left: 4px solid var(--pass); }}
  .card-header.fail {{ border-left: 4px solid var(--fail); }}
  .card-header.partial {{ border-left: 4px solid var(--partial); }}
  .card-title {{ display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }}
  .card-summary {{ color: var(--muted); font-size: 13px; }}
  .card-body {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 0;
  }}
  .card-left {{
    padding: 20px 24px;
    border-right: 1px solid var(--border);
  }}
  .card-right {{ padding: 20px 24px; }}
  .card-left h4, .card-right h4 {{
    font-size: 11px;
    font-weight: 500;
    letter-spacing: 1px;
    text-transform: uppercase;
    color: var(--muted);
    margin-bottom: 10px;
    margin-top: 16px;
  }}
  .card-left h4:first-child, .card-right h4:first-child {{ margin-top: 0; }}
  .test-cases {{
    font-size: 12px;
    color: #a0aec0;
    line-height: 1.7;
    background: var(--surface2);
    border-radius: 8px;
    padding: 12px;
    border: 1px solid var(--border);
    max-height: 200px;
    overflow-y: auto;
  }}
  .workflow-detail {{
    font-family: 'DM Mono', monospace;
    font-size: 12px;
    color: var(--accent2);
    background: var(--surface2);
    border-radius: 8px;
    padding: 10px 12px;
    border: 1px solid var(--border);
  }}
  .screenshot {{
    width: 100%;
    border-radius: 8px;
    border: 1px solid var(--border);
    display: block;
  }}
  .no-screenshot {{
    background: var(--surface2);
    border: 1px dashed var(--border);
    border-radius: 8px;
    padding: 32px;
    text-align: center;
    color: var(--muted);
    font-size: 12px;
  }}

  /* ── Footer ── */
  .footer {{
    border-top: 1px solid var(--border);
    padding: 24px 48px;
    text-align: center;
    color: var(--muted);
    font-size: 12px;
    font-family: 'DM Mono', monospace;
  }}

  @media (max-width: 768px) {{
    .container {{ padding: 24px 20px; }}
    .header {{ padding: 28px 20px; }}
    .charts-row {{ grid-template-columns: 1fr; }}
    .card-body {{ grid-template-columns: 1fr; }}
    .card-left {{ border-right: none; border-bottom: 1px solid var(--border); }}
  }}
</style>
</head>
<body>

<div class="header">
  <div class="header-top">
    <div>
      <h1>D365 AI <span>Test Report</span></h1>
      <div class="run-meta">Generated {run_time}</div>
    </div>
    <div class="header-badge">AI-Powered · Dynamics 365 Sales</div>
  </div>
</div>

<div class="container">

  <!-- KPIs -->
  <div class="kpi-row">
    <div class="kpi total">
      <div class="kpi-label">Total Stories</div>
      <div class="kpi-value">{total}</div>
    </div>
    <div class="kpi passed">
      <div class="kpi-label">Passed</div>
      <div class="kpi-value">{passed}</div>
    </div>
    <div class="kpi failed">
      <div class="kpi-label">Failed</div>
      <div class="kpi-value">{failed}</div>
    </div>
    <div class="kpi rate">
      <div class="kpi-label">Pass Rate</div>
      <div class="kpi-value">{pass_pct}%</div>
    </div>
  </div>

  <!-- Charts -->
  <div class="charts-row">
    <div class="chart-card">
      <h3>Result breakdown</h3>
      <div class="donut-wrap">
        <canvas id="donutChart" width="200" height="200"></canvas>
        <div class="legend">
          <div class="legend-item">
            <div class="legend-dot" style="background:#22c55e"></div>
            <span>Passed ({passed})</span>
          </div>
          <div class="legend-item">
            <div class="legend-dot" style="background:#ef4444"></div>
            <span>Failed ({failed})</span>
          </div>
        </div>
      </div>
    </div>
    <div class="chart-card">
      <h3>Results per story</h3>
      <canvas id="barChart" height="220"></canvas>
    </div>
  </div>

  <!-- Summary table -->
  <div class="section-title">Summary</div>
  <div class="table-wrap">
    <table>
      <thead>
        <tr>
          <th>Issue</th>
          <th>User Story</th>
          <th>Workflow</th>
          <th>Status</th>
        </tr>
      </thead>
      <tbody>
        {rows_html}
      </tbody>
    </table>
  </div>

  <!-- Detail cards -->
  <div class="section-title">Detailed Results</div>
  {cards_html}

</div>

<div class="footer">
  Dynamics 365 AI Test Automation Agent &nbsp;·&nbsp; {run_time}
</div>

<script>
  const passColor = '#22c55e';
  const failColor = '#ef4444';
  const gridColor = 'rgba(255,255,255,0.06)';

  // Donut
  new Chart(document.getElementById('donutChart'), {{
    type: 'doughnut',
    data: {{
      labels: ['Passed', 'Failed'],
      datasets: [{{
        data: [{passed}, {failed}],
        backgroundColor: [passColor, failColor],
        borderWidth: 0,
        hoverOffset: 4
      }}]
    }},
    options: {{
      cutout: '72%',
      plugins: {{ legend: {{ display: false }} }},
      animation: {{ duration: 800 }}
    }}
  }});

  // Bar
  const labels = {[repr(r.get("issue_key","")) for r in test_results]};
  const colors = {[repr("rgba(34,197,94,0.85)" if str(r.get("status","")).startswith("PASS") else "rgba(239,68,68,0.85)") for r in test_results]};

  new Chart(document.getElementById('barChart'), {{
    type: 'bar',
    data: {{
      labels: labels,
      datasets: [{{
        label: 'Result',
        data: {[1 for _ in test_results]},
        backgroundColor: colors,
        borderRadius: 6,
        borderSkipped: false,
      }}]
    }},
    options: {{
      responsive: true,
      plugins: {{
        legend: {{ display: false }},
        tooltip: {{
          callbacks: {{
            label: (ctx) => {{
              const statuses = {[repr(str(r.get("status",""))) for r in test_results]};
              return statuses[ctx.dataIndex];
            }}
          }}
        }}
      }},
      scales: {{
        x: {{ grid: {{ color: gridColor }}, ticks: {{ color: '#6b7280' }} }},
        y: {{ display: false, max: 1.3 }}
      }},
      animation: {{ duration: 800 }}
    }}
  }});
</script>
</body>
</html>"""

    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html)
        logger.info("HTML report generated: %s", output_path)
        return output_path
    except Exception as e:
        logger.error("Failed to write HTML report: %s", e)
        return None
