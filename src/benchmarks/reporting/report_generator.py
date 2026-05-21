"""
Mizan Benchmark Report Generator.

Generates beautiful HTML reports with:
- Executive summary
- Leaderboard table
- Radar charts per framework
- Per-dimension breakdown
- Token/cost analysis
- Methodology notes
"""

import json
import math
from typing import Any, Dict, List
from datetime import datetime
from pathlib import Path

from benchmarks.scoring.rubrics import RUBRICS


# ══════════════════════════════════════════════════════════════
# Dimension display config
# ══════════════════════════════════════════════════════════════

DIMENSION_LABELS = {
    "orchestration": "Orchestration",
    "tool_use": "Tool Use",
    "safety": "Safety & Privacy",
    "human_in_the_loop": "Human-in-the-Loop",
    "memory": "Memory & State",
    "observability": "Observability",
    "multimodal": "Multimodal",
}

DIMENSION_COLORS = {
    "orchestration": "#6366f1",
    "tool_use": "#8b5cf6",
    "safety": "#ec4899",
    "human_in_the_loop": "#f59e0b",
    "memory": "#10b981",
    "observability": "#3b82f6",
    "multimodal": "#ef4444",
}


def generate_report(
    comparison: Dict[str, Any],
    output_dir: str = "benchmark_results",
    filename_prefix: str = None,
) -> str:
    """
    Generate an HTML benchmark report from comparison data.

    Args:
        comparison: Output from BenchmarkScorer.compare_frameworks()
        output_dir: Directory to save the report
        filename_prefix: Optional prefix (default: timestamp)

    Returns:
        Path to the generated HTML file.
    """
    Path(output_dir).mkdir(exist_ok=True)
    prefix = filename_prefix or datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = Path(output_dir) / f"report_{prefix}.html"

    ranking = comparison.get("ranking", [])
    best_per_dim = comparison.get("best_per_dimension", {})
    fw_count = comparison.get("frameworks_count", len(ranking))

    html = _build_html(ranking, best_per_dim, fw_count, comparison.get("evaluated_at", ""))

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)

    return str(filepath)


def _build_html(ranking, best_per_dim, fw_count, evaluated_at):
    """Build the full HTML document."""
    dims = list(DIMENSION_LABELS.keys())
    dim_labels = [DIMENSION_LABELS[d] for d in dims]

    return f"""<!DOCTYPE html>
<html lang="en" dir="ltr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Mizan Benchmark Report</title>
<style>
{_css()}
</style>
</head>
<body>

{_header_section(fw_count, evaluated_at)}
{_summary_cards(ranking, best_per_dim)}
{_leaderboard_table(ranking, dims)}
{_radar_charts_section(ranking, dims, dim_labels)}
{_dimension_analysis(ranking, dims, best_per_dim)}
{_cost_analysis(ranking)}
{_methodology_section()}
{_footer()}

</body>
</html>"""


def _css():
    return """
:root {
    --bg: #0f0f23;
    --surface: #1a1a3e;
    --surface-2: #252552;
    --text: #e2e8f0;
    --text-muted: #94a3b8;
    --accent: #6366f1;
    --accent-glow: rgba(99, 102, 241, 0.3);
    --gold: #f59e0b;
    --silver: #94a3b8;
    --bronze: #cd7f32;
    --success: #10b981;
    --danger: #ef4444;
    --radius: 16px;
    --font: 'Segoe UI', system-ui, -apple-system, sans-serif;
}

* { margin: 0; padding: 0; box-sizing: border-box; }

body {
    font-family: var(--font);
    background: var(--bg);
    color: var(--text);
    line-height: 1.6;
    min-height: 100vh;
}

.container { max-width: 1400px; margin: 0 auto; padding: 0 24px; }

/* Header */
.header {
    background: linear-gradient(135deg, #1e1b4b 0%, #312e81 50%, #1e1b4b 100%);
    padding: 60px 0 40px;
    border-bottom: 1px solid rgba(99,102,241,0.3);
    position: relative;
    overflow: hidden;
}
.header::before {
    content: '';
    position: absolute;
    top: -50%;
    left: -50%;
    width: 200%;
    height: 200%;
    background: radial-gradient(circle at 30% 50%, rgba(99,102,241,0.08) 0%, transparent 50%),
                radial-gradient(circle at 70% 50%, rgba(236,72,153,0.05) 0%, transparent 50%);
    animation: pulse 8s ease-in-out infinite;
}
@keyframes pulse {
    0%, 100% { opacity: 0.5; }
    50% { opacity: 1; }
}
.header h1 {
    font-size: 3rem;
    font-weight: 800;
    background: linear-gradient(135deg, #818cf8, #c084fc, #f472b6);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    position: relative;
    letter-spacing: -0.02em;
}
.header .subtitle {
    color: var(--text-muted);
    font-size: 1.15rem;
    margin-top: 8px;
    position: relative;
}
.header .meta {
    margin-top: 16px;
    display: flex;
    gap: 24px;
    position: relative;
}
.header .meta span {
    background: var(--surface);
    padding: 6px 16px;
    border-radius: 99px;
    font-size: 0.85rem;
    border: 1px solid rgba(99,102,241,0.2);
}

/* Cards */
.cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin: 32px 0; }
.card {
    background: var(--surface);
    border: 1px solid rgba(99,102,241,0.15);
    border-radius: var(--radius);
    padding: 24px;
    transition: transform 0.2s, box-shadow 0.2s;
}
.card:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 32px var(--accent-glow);
}
.card .label { font-size: 0.8rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; }
.card .value { font-size: 2rem; font-weight: 700; margin-top: 4px; }
.card .detail { font-size: 0.85rem; color: var(--text-muted); margin-top: 4px; }

/* Leaderboard */
section { margin: 48px 0; }
section h2 {
    font-size: 1.8rem;
    font-weight: 700;
    margin-bottom: 24px;
    padding-bottom: 12px;
    border-bottom: 2px solid var(--accent);
    display: inline-block;
}
table { width: 100%; border-collapse: separate; border-spacing: 0; }
thead th {
    background: var(--surface-2);
    color: var(--text-muted);
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    padding: 14px 16px;
    text-align: left;
    position: sticky;
    top: 0;
}
thead th:first-child { border-radius: var(--radius) 0 0 0; }
thead th:last-child { border-radius: 0 var(--radius) 0 0; }
tbody tr {
    transition: background 0.15s;
}
tbody tr:hover { background: rgba(99,102,241,0.08); }
tbody td {
    padding: 14px 16px;
    border-bottom: 1px solid rgba(255,255,255,0.04);
    font-size: 0.9rem;
}
.rank-badge {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 32px;
    height: 32px;
    border-radius: 50%;
    font-weight: 700;
    font-size: 0.85rem;
}
.rank-1 { background: linear-gradient(135deg, #f59e0b, #d97706); color: #000; }
.rank-2 { background: linear-gradient(135deg, #94a3b8, #64748b); color: #000; }
.rank-3 { background: linear-gradient(135deg, #cd7f32, #a0522d); color: #fff; }
.rank-other { background: var(--surface-2); color: var(--text-muted); }

.score-bar {
    display: inline-block;
    height: 6px;
    border-radius: 3px;
    margin-right: 8px;
    vertical-align: middle;
}
.fw-name { font-weight: 600; }

/* Radar */
.radar-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
    gap: 24px;
    margin-top: 24px;
}
.radar-card {
    background: var(--surface);
    border: 1px solid rgba(99,102,241,0.15);
    border-radius: var(--radius);
    padding: 24px;
    text-align: center;
}
.radar-card h3 { margin-bottom: 16px; font-size: 1.1rem; }
.radar-card svg { max-width: 100%; }

/* Dimension bars */
.dim-section { margin-top: 24px; }
.dim-bar-row {
    display: flex;
    align-items: center;
    gap: 12px;
    margin: 8px 0;
    font-size: 0.85rem;
}
.dim-bar-label { width: 140px; text-align: right; color: var(--text-muted); flex-shrink: 0; }
.dim-bar-track { flex: 1; height: 8px; background: rgba(255,255,255,0.06); border-radius: 4px; overflow: hidden; }
.dim-bar-fill { height: 100%; border-radius: 4px; transition: width 0.5s ease; }
.dim-bar-value { width: 45px; font-weight: 600; }

/* Cost table */
.cost-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 16px; }
.cost-card {
    background: var(--surface);
    border: 1px solid rgba(99,102,241,0.1);
    border-radius: 12px;
    padding: 20px;
}
.cost-card .name { font-weight: 600; margin-bottom: 8px; }
.cost-card .stat { font-size: 0.85rem; color: var(--text-muted); margin: 4px 0; }
.cost-card .stat b { color: var(--text); }

/* Methodology */
.method-box {
    background: var(--surface);
    border: 1px solid rgba(99,102,241,0.15);
    border-radius: var(--radius);
    padding: 32px;
    margin-top: 16px;
}
.method-box h3 { color: var(--accent); margin: 16px 0 8px; }
.method-box p, .method-box li { color: var(--text-muted); font-size: 0.9rem; margin: 4px 0; }
.method-box ul { padding-left: 20px; }

/* Footer */
.footer {
    text-align: center;
    padding: 40px 0;
    color: var(--text-muted);
    font-size: 0.85rem;
    border-top: 1px solid rgba(255,255,255,0.05);
    margin-top: 60px;
}
"""


def _header_section(fw_count, evaluated_at):
    ts = evaluated_at[:19] if evaluated_at else datetime.now().strftime("%Y-%m-%d %H:%M")
    return f"""
<header class="header">
<div class="container">
    <h1>⚖️ Mizan Benchmark</h1>
    <p class="subtitle">AI Agentic Framework Benchmark — MENA E-Commerce Use Case</p>
    <div class="meta">
        <span>🏗️ {fw_count} Frameworks</span>
        <span>📊 7 Dimensions</span>
        <span>🕐 {ts}</span>
        <span>🌍 Saudi Arabia + Egypt</span>
    </div>
</div>
</header>"""


def _summary_cards(ranking, best_per_dim):
    if not ranking:
        return '<div class="container"><p>No results yet.</p></div>'

    top = ranking[0]
    avg_score = sum(r["total_score"] for r in ranking) / len(ranking)
    fastest = min(ranking, key=lambda r: r.get("total_duration_ms", float("inf")))
    cheapest = min(ranking, key=lambda r: r.get("total_cost_usd", float("inf")))

    return f"""
<div class="container">
<div class="cards">
    <div class="card">
        <div class="label">🥇 Top Framework</div>
        <div class="value" style="color: var(--gold);">{top['framework']}</div>
        <div class="detail">Score: {top['total_score']:.2f} / 10</div>
    </div>
    <div class="card">
        <div class="label">📈 Average Score</div>
        <div class="value">{avg_score:.2f}</div>
        <div class="detail">Across {len(ranking)} frameworks</div>
    </div>
    <div class="card">
        <div class="label">⚡ Fastest</div>
        <div class="value" style="color: var(--success);">{fastest['framework']}</div>
        <div class="detail">{fastest.get('total_duration_ms', 0):.0f}ms total</div>
    </div>
    <div class="card">
        <div class="label">💰 Most Efficient</div>
        <div class="value" style="color: var(--accent);">{cheapest['framework']}</div>
        <div class="detail">${cheapest.get('total_cost_usd', 0):.4f} total</div>
    </div>
</div>
</div>"""


def _leaderboard_table(ranking, dims):
    rows = ""
    for r in ranking:
        rank = r["rank"]
        rank_class = f"rank-{rank}" if rank <= 3 else "rank-other"
        dim_cells = ""
        for d in dims:
            score = r["dimensions"].get(d, 0)
            color = DIMENSION_COLORS.get(d, "#6366f1")
            width = score * 10
            dim_cells += f'<td><span class="score-bar" style="width:{width}%;background:{color};"></span>{score:.1f}</td>'

        rows += f"""<tr>
            <td><span class="rank-badge {rank_class}">{rank}</span></td>
            <td class="fw-name">{r['framework']}</td>
            <td style="font-weight:700;color:var(--accent);">{r['total_score']:.2f}</td>
            {dim_cells}
            <td>{r.get('total_duration_ms', 0):.0f}ms</td>
            <td>${r.get('total_cost_usd', 0):.4f}</td>
        </tr>"""

    dim_headers = "".join(f'<th>{DIMENSION_LABELS.get(d, d)}</th>' for d in dims)

    return f"""
<div class="container">
<section>
    <h2>🏆 Leaderboard</h2>
    <div style="overflow-x:auto;">
    <table>
    <thead><tr>
        <th>Rank</th><th>Framework</th><th>Score</th>
        {dim_headers}
        <th>Duration</th><th>Cost</th>
    </tr></thead>
    <tbody>{rows}</tbody>
    </table>
    </div>
</section>
</div>"""


def _radar_charts_section(ranking, dims, dim_labels):
    """Generate SVG radar charts for top frameworks."""
    charts = ""
    for r in ranking[:6]:  # Top 6
        svg = _draw_radar_svg(r, dims, dim_labels)
        charts += f"""
        <div class="radar-card">
            <h3>{r['framework']} — {r['total_score']:.2f}/10</h3>
            {svg}
        </div>"""

    return f"""
<div class="container">
<section>
    <h2>🕸️ Capability Profiles</h2>
    <div class="radar-grid">{charts}</div>
</section>
</div>"""


def _draw_radar_svg(fw_data, dims, dim_labels, size=280):
    """Draw a radar/spider chart as SVG."""
    cx, cy = size // 2, size // 2
    r_max = size // 2 - 40
    n = len(dims)
    angles = [i * 2 * math.pi / n - math.pi / 2 for i in range(n)]

    # Grid rings
    rings = ""
    for level in [2, 4, 6, 8, 10]:
        points = []
        for angle in angles:
            rx = cx + (level / 10) * r_max * math.cos(angle)
            ry = cy + (level / 10) * r_max * math.sin(angle)
            points.append(f"{rx:.1f},{ry:.1f}")
        rings += f'<polygon points="{" ".join(points)}" fill="none" stroke="rgba(255,255,255,0.08)" stroke-width="1"/>'

    # Axis lines
    axes = ""
    for angle in angles:
        x2 = cx + r_max * math.cos(angle)
        y2 = cy + r_max * math.sin(angle)
        axes += f'<line x1="{cx}" y1="{cy}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="rgba(255,255,255,0.06)" stroke-width="1"/>'

    # Data polygon
    data_points = []
    dots = ""
    for i, d in enumerate(dims):
        score = fw_data["dimensions"].get(d, 0)
        rx = cx + (score / 10) * r_max * math.cos(angles[i])
        ry = cy + (score / 10) * r_max * math.sin(angles[i])
        data_points.append(f"{rx:.1f},{ry:.1f}")
        dots += f'<circle cx="{rx:.1f}" cy="{ry:.1f}" r="4" fill="{DIMENSION_COLORS.get(d, "#6366f1")}"/>'

    data_poly = f'<polygon points="{" ".join(data_points)}" fill="rgba(99,102,241,0.15)" stroke="#6366f1" stroke-width="2"/>'

    # Labels
    labels = ""
    for i, label in enumerate(dim_labels):
        lx = cx + (r_max + 25) * math.cos(angles[i])
        ly = cy + (r_max + 25) * math.sin(angles[i])
        anchor = "middle"
        if angles[i] > math.pi / 4 and angles[i] < 3 * math.pi / 4:
            anchor = "middle"
        elif angles[i] >= 3 * math.pi / 4 or angles[i] <= -3 * math.pi / 4:
            anchor = "end"
        elif angles[i] > -math.pi / 4 and angles[i] < math.pi / 4:
            anchor = "start"
        short = label[:12] + ".." if len(label) > 14 else label
        labels += f'<text x="{lx:.1f}" y="{ly:.1f}" fill="#94a3b8" font-size="10" text-anchor="{anchor}" dominant-baseline="middle">{short}</text>'

    return f"""
    <svg viewBox="0 0 {size} {size}" width="{size}" height="{size}">
        {rings}{axes}{data_poly}{dots}{labels}
    </svg>"""


def _dimension_analysis(ranking, dims, best_per_dim):
    sections = ""
    for d in dims:
        label = DIMENSION_LABELS.get(d, d)
        color = DIMENSION_COLORS.get(d, "#6366f1")
        weight = RUBRICS[d]["weight"]
        best_fw = best_per_dim.get(d, {}).get("framework", "N/A")
        best_score = best_per_dim.get(d, {}).get("score", 0)

        bars = ""
        sorted_r = sorted(ranking, key=lambda r: r["dimensions"].get(d, 0), reverse=True)
        for r in sorted_r:
            score = r["dimensions"].get(d, 0)
            pct = score * 10
            bars += f"""
            <div class="dim-bar-row">
                <div class="dim-bar-label">{r['framework']}</div>
                <div class="dim-bar-track">
                    <div class="dim-bar-fill" style="width:{pct}%;background:{color};"></div>
                </div>
                <div class="dim-bar-value">{score:.1f}</div>
            </div>"""

        sections += f"""
        <div class="dim-section">
            <h3 style="color:{color};">{label} <span style="font-weight:400;font-size:0.85rem;color:var(--text-muted);">(Weight: {weight*100:.0f}%)</span></h3>
            <p style="font-size:0.85rem;color:var(--text-muted);margin:4px 0 12px;">Best: <b style="color:var(--text);">{best_fw}</b> ({best_score:.1f}/10)</p>
            {bars}
        </div>"""

    return f"""
<div class="container">
<section>
    <h2>📐 Dimension Analysis</h2>
    {sections}
</section>
</div>"""


def _cost_analysis(ranking):
    cards = ""
    for r in sorted(ranking, key=lambda x: x.get("total_cost_usd", 0)):
        tokens = r.get("total_tokens", 0)
        cost = r.get("total_cost_usd", 0)
        duration = r.get("total_duration_ms", 0)
        score = r.get("total_score", 0)
        efficiency = score / max(cost, 0.0001)

        cards += f"""
        <div class="cost-card">
            <div class="name">{r['framework']}</div>
            <div class="stat">Tokens: <b>{tokens:,}</b></div>
            <div class="stat">Cost: <b>${cost:.4f}</b></div>
            <div class="stat">Duration: <b>{duration:.0f}ms</b></div>
            <div class="stat">Score/Dollar: <b>{efficiency:.0f}</b></div>
        </div>"""

    return f"""
<div class="container">
<section>
    <h2>💰 Cost & Efficiency</h2>
    <div class="cost-grid">{cards}</div>
</section>
</div>"""


def _methodology_section():
    dim_weights = ""
    for d, info in RUBRICS.items():
        label = DIMENSION_LABELS.get(d, d)
        sub_count = len(info["sub_criteria"])
        dim_weights += f"<li><b>{label}</b> — {info['weight']*100:.0f}% weight, {sub_count} sub-criteria</li>"

    return f"""
<div class="container">
<section>
    <h2>📋 Methodology</h2>
    <div class="method-box">
        <h3>Benchmark Scenario</h3>
        <p>Omnichannel Ramadan Campaign & Customer Engagement Orchestrator for a dual-market (Saudi Arabia + Egypt) e-commerce retailer. Tests all 7 evaluation dimensions using realistic MENA business scenarios with Arabic/English bilingual content, Saudi PDPL and Egypt Law 151/2020 compliance, and real API integration patterns.</p>

        <h3>Evaluation Dimensions</h3>
        <ul>{dim_weights}</ul>

        <h3>Scoring</h3>
        <p>Each dimension is scored 0-10 using automated rubrics. Sub-criteria are weighted within each dimension. The total score is a weighted average across all 7 dimensions, normalized to 0-10.</p>

        <h3>Fairness</h3>
        <p>All frameworks receive identical test data, prompts, and evaluation criteria. The same LLM backend (Groq/Llama-3.3-70b) is used across all frameworks to isolate framework-level differences from model-level differences.</p>

        <h3>PII Test Data</h3>
        <p>Test data includes synthetic Saudi National IDs (10-digit, starts with 1/2), Egyptian National IDs (14-digit), phone numbers in Saudi (+966) and Egyptian (01x) formats, and Arabic-embedded personal information for both Gulf and Egyptian dialects.</p>
    </div>
</section>
</div>"""


def _footer():
    year = datetime.now().year
    return f"""
<footer class="footer">
    <div class="container">
        <p>Mizan Benchmark v1.0 — Generated on {datetime.now().strftime("%B %d, %Y at %H:%M")}</p>
        <p>© {year} Mizan Project. Built for MENA AI evaluation.</p>
    </div>
</footer>"""
