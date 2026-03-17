#!/usr/bin/env python3
"""
Build an interactive HTML dashboard with scatter plots for Holbrook, AZ climate data.
Each chart groups the same calendar day across 25 years, with mean and ±2σ lines.
"""

import csv
import json
import math
from collections import defaultdict

CSV_FILE = "Holbrook_AZ_Daily_Climate_2001_2026.csv"
OUTPUT_HTML = "Holbrook_AZ_Climate_Dashboard.html"

METRICS = [
    {"key": "max_temp", "col": 1, "label": "Max Temperature (°F)", "color": "#e74c3c", "unit": "°F"},
    {"key": "min_temp", "col": 2, "label": "Min Temperature (°F)", "color": "#3498db", "unit": "°F"},
    {"key": "avg_temp", "col": 3, "label": "Avg Temperature (°F)", "color": "#f39c12", "unit": "°F"},
    {"key": "precip",   "col": 4, "label": "Precipitation (in)",   "color": "#27ae60", "unit": "in"},
]


def parse_val(v):
    if v in ("M", "T", "S", ""):
        return None
    try:
        return float(v)
    except ValueError:
        return None


def mean_std(values):
    n = len(values)
    if n == 0:
        return None, None
    m = sum(values) / n
    if n < 2:
        return m, 0.0
    variance = sum((x - m) ** 2 for x in values) / (n - 1)
    return m, math.sqrt(variance)


def main():
    # Read data grouped by day-of-year (MM-DD)
    # day_data[metric_key][mm-dd] = [(year, value), ...]
    day_data = {m["key"]: defaultdict(list) for m in METRICS}

    with open(CSV_FILE) as f:
        reader = csv.reader(f)
        next(reader)  # skip header
        for row in reader:
            date_str = row[0]
            year = int(date_str[:4])
            mm_dd = date_str[5:]  # "MM-DD"
            # Skip Feb 29 to keep consistent 365-day axis
            if mm_dd == "02-29":
                continue
            for m in METRICS:
                val = parse_val(row[m["col"]])
                if val is not None:
                    day_data[m["key"]][mm_dd].append((year, val))

    # Build sorted day-of-year list (Jan 1 through Dec 31, no Feb 29)
    all_days = sorted(day_data[METRICS[0]["key"]].keys())

    # Pre-compute per-day-of-year averages for cross-metric hover info
    day_avgs = {}  # mm-dd -> {max_temp: x, min_temp: x, precip: x}
    for dd in all_days:
        avgs = {}
        for m in METRICS:
            vals = [v for _, v in day_data[m["key"]][dd]]
            avg, _ = mean_std(vals)
            avgs[m["key"]] = round(avg, 2) if avg is not None else "N/A"
        day_avgs[dd] = avgs

    month_names_full = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
    def format_dd(dd):
        m, d = dd.split("-")
        return f"{month_names_full[int(m)-1]} {int(d)}"

    def hover_summary(dd):
        a = day_avgs[dd]
        return (f"Avg Max Temp: {a['max_temp']}°F<br>"
                f"Avg Min Temp: {a['min_temp']}°F<br>"
                f"Avg Precip: {a['precip']} in")

    # For each metric, build: scatter points, mean line, +2σ line, -2σ line
    chart_data = {}
    for m in METRICS:
        scatter_x = []
        scatter_y = []
        scatter_text = []
        mean_y = []
        mean_text = []
        plus2_y = []
        plus2_text = []
        minus2_y = []
        minus2_text = []
        day_labels = []

        for i, dd in enumerate(all_days):
            entries = day_data[m["key"]][dd]
            vals = [v for _, v in entries]
            avg, std = mean_std(vals)
            pretty = format_dd(dd)
            summary = hover_summary(dd)

            day_labels.append(dd)
            avg_r = round(avg, 2) if avg is not None else "N/A"
            mean_y.append(avg_r if avg is not None else None)
            plus2_val = round(avg + 2 * std, 2) if avg is not None else "N/A"
            plus2_y.append(plus2_val if avg is not None else None)
            minus2_val = round(avg - 2 * std, 2) if avg is not None else "N/A"
            minus2_y.append(minus2_val if avg is not None else None)

            line_hover = (
                f"<b>{pretty}</b><br>"
                f"Mean: {avg_r} {m['unit']}<br>"
                f"+2σ: {plus2_val} {m['unit']}<br>"
                f"−2σ: {minus2_val} {m['unit']}"
            )
            mean_text.append(line_hover)
            plus2_text.append(line_hover)
            minus2_text.append(line_hover)

            for year, val in entries:
                scatter_x.append(i)
                scatter_y.append(val)
                scatter_text.append(
                    f"<b>{year}-{dd}</b><br>"
                    f"{m['label']}: {val} {m['unit']}<br>"
                    f"{summary}"
                )

        chart_data[m["key"]] = {
            "scatter_x": scatter_x,
            "scatter_y": scatter_y,
            "scatter_text": scatter_text,
            "mean_y": mean_y,
            "mean_text": mean_text,
            "plus2_y": plus2_y,
            "plus2_text": plus2_text,
            "minus2_y": minus2_y,
            "minus2_text": minus2_text,
            "day_labels": day_labels,
        }

    # Generate tick marks (1st of each month)
    month_ticks = []
    month_labels = []
    month_names = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
    for i, dd in enumerate(all_days):
        if dd.endswith("-01"):
            month_ticks.append(i)
            month_labels.append(month_names[int(dd[:2]) - 1])

    # Build HTML
    html = generate_html(chart_data, month_ticks, month_labels)
    with open(OUTPUT_HTML, "w") as f:
        f.write(html)
    print(f"Dashboard saved to: {OUTPUT_HTML}")


def generate_html(chart_data, month_ticks, month_labels):
    plots_js = ""
    for m in METRICS:
        cd = chart_data[m["key"]]
        is_precip = m["key"] == "precip"
        traces = f"""
        {{
            x: {json.dumps(cd['scatter_x'])},
            y: {json.dumps(cd['scatter_y'])},
            text: {json.dumps(cd['scatter_text'])},
            mode: 'markers',
            type: 'scatter',
            marker: {{ color: '{m["color"]}', size: 2.5, opacity: 0.35 }},
            hoverinfo: 'text',
            name: 'Daily Obs.'
        }},
        {{
            x: {json.dumps(list(range(len(cd['mean_y']))))},
            y: {json.dumps(cd['mean_y'])},
            text: {json.dumps(cd['mean_text'])},
            mode: 'lines',
            line: {{ color: '#2c3e50', width: 2.5 }},
            hoverinfo: 'text',
            name: 'Mean'
        }},
        {{
            x: {json.dumps(list(range(len(cd['plus2_y']))))},
            y: {json.dumps(cd['plus2_y'])},
            text: {json.dumps(cd['plus2_text'])},
            mode: 'lines',
            line: {{ color: '#e67e22', width: 2, dash: 'solid' }},
            hoverinfo: 'text',
            name: '+2 Std Dev'
        }}"""
        if not is_precip:
            traces += f""",
        {{
            x: {json.dumps(list(range(len(cd['minus2_y']))))},
            y: {json.dumps(cd['minus2_y'])},
            text: {json.dumps(cd['minus2_text'])},
            mode: 'lines',
            line: {{ color: '#8e44ad', width: 2, dash: 'solid' }},
            hoverinfo: 'text',
            name: '−2 Std Dev'
        }}"""
        plots_js += f"""
    // --- {m['label']} ---
    Plotly.newPlot('{m["key"]}_chart', [{traces}
    ], {{
        title: {{ text: '{m["label"]} — Holbrook, AZ (2001–2026)', font: {{ size: 16 }} }},
        xaxis: {{
            tickvals: {json.dumps(month_ticks)},
            ticktext: {json.dumps(month_labels)},
            title: 'Day of Year',
            gridcolor: '#ecf0f1'
        }},
        yaxis: {{ title: '{m["unit"]}', gridcolor: '#ecf0f1' }},
        plot_bgcolor: '#fafafa',
        paper_bgcolor: '#ffffff',
        margin: {{ t: 50, b: 80, l: 60, r: 30 }},
        legend: {{ orientation: 'h', y: -0.25, x: 0.5, xanchor: 'center', font: {{ size: 11 }} }},
        showlegend: true,
        hovermode: 'closest'
    }}, {{ responsive: true }});
"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Holbrook, AZ Climate Dashboard (2001–2026)</title>
<script src="https://cdn.plot.ly/plotly-2.35.0.min.js"></script>
<style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{ font-family: 'Segoe UI', Arial, sans-serif; background: #f5f6fa; padding: 20px; }}
    h1 {{ text-align: center; color: #2c3e50; margin-bottom: 5px; font-size: 24px; }}
    .subtitle {{ text-align: center; color: #7f8c8d; margin-bottom: 20px; font-size: 13px; }}
    .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; max-width: 1600px; margin: 0 auto; }}
    .chart-card {{
        background: #fff; border-radius: 8px; padding: 10px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    }}
    .chart {{ width: 100%; height: 460px; }}
    .legend-info {{
        text-align: center; margin: 15px auto; max-width: 800px;
        padding: 12px; background: #fff; border-radius: 8px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08); font-size: 13px; color: #555;
    }}
    .legend-info span {{ margin: 0 12px; }}
    .swatch {{ display: inline-block; width: 30px; height: 3px; vertical-align: middle; margin-right: 4px; }}
    @media (max-width: 900px) {{ .grid {{ grid-template-columns: 1fr; }} }}
</style>
</head>
<body>
<h1>Holbrook, AZ — Daily Climate Dashboard</h1>
<p class="subtitle">
    Each dot = one day's observation (same calendar day plotted across 25 years, 2001–2026)<br>
    Source: NOAA/NWS Western Region Climate — Holbrook COOP &amp; Winslow Airport (KINW)
</p>
<div class="legend-info">
    <span><span class="swatch" style="background:#2c3e50;"></span> Mean</span>
    <span><span class="swatch" style="background:#e67e22;"></span> +2 Std Dev</span>
    <span><span class="swatch" style="background:#8e44ad;"></span> −2 Std Dev</span>
    <span style="color:#999;">|</span>
    <span style="color:#888;">Dots = individual daily observations (hover for details)</span>
</div>
<div class="grid">
    <div class="chart-card"><div id="max_temp_chart" class="chart"></div></div>
    <div class="chart-card"><div id="min_temp_chart" class="chart"></div></div>
    <div class="chart-card"><div id="avg_temp_chart" class="chart"></div></div>
    <div class="chart-card"><div id="precip_chart" class="chart"></div></div>
</div>
<script>
{plots_js}
</script>
</body>
</html>"""


if __name__ == "__main__":
    main()
