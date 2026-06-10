from pathlib import Path
import re
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from html import escape

from cli_parser import VisualFormatOptions
from comparison_context import ComparisonCols
from plot_config import PlotGroupConfig

REPORT_DIR = Path.cwd() / "visual"
INDEX_HTML = REPORT_DIR / "index.html"

DARK_BG        = "#0f172a"
PANEL_BG       = "#1e293b"
BORDER_COLOR   = "#334155"
TEXT_MAIN      = "#f8fafc"
TEXT_MUTED     = "#94a3b8"
CONTENDER_ZONE = "#38bdf8"

def visualize_report(
    df:             pd.DataFrame,
    plot_groups:    dict[str, PlotGroupConfig],
    visual_formats: list[VisualFormatOptions]
) -> None:
    REPORT_DIR.mkdir(parents = True, exist_ok = True)

    tabs_data = {}
    for group_name, group_cfg in plot_groups.items():
        metrics   = group_cfg.get_metric_names()
        visual_df = df[df[ComparisonCols.METRIC].isin(metrics)].copy()
    
        visual_df.replace([np.inf, -np.inf], np.nan, inplace = True)
        visual_df.dropna(subset = [
            ComparisonCols.BASELINE_VAL,
            ComparisonCols.CONTENDER_VAL,
            ComparisonCols.DELTA_ABS,
            ComparisonCols.DELTA_PCT
        ], inplace = True)

        if visual_df.empty:
            continue

        table_html = visualize_table(visual_df) if VisualFormatOptions.TABLE in visual_formats else None
        chart_fig  = visualize_chart(visual_df) if VisualFormatOptions.CHART in visual_formats else None
        graph_fig  = visualize_graph(visual_df) if VisualFormatOptions.GRAPH in visual_formats else None

        if table_html or chart_fig or graph_fig:
            tabs_data[group_name] = create_group_panel(table_html, chart_fig, graph_fig)

    if tabs_data:
        build_tabbed_index_html(tabs_data)


def visualize_table(df: pd.DataFrame) -> str | None:
    rows = build_timeline_records(df)
    if not rows:
        return None

    status_bg_map = {"regression": "#7f1d1d", "improvement": "#14532d", "noise": "#78350f", "interesting": "#1e3a8a"}
    status_fg_map = {"regression": "#fecaca", "improvement": "#bbf7d0", "noise": "#fef08a", "interesting": "#bfdbfe"}

    title_html = f"""
    <div class="table-title-area">
        <div class="table-main-title">Metric Comparison Table</div>
        <div class="table-sub-title">Contender: <span style="color:{CONTENDER_ZONE}; font-weight:bold;">{escape(get_contender_id(df)[:8])}</span> | Baselines Tracked: {len(get_unique_baselines(df))}</div>
    </div>
    """

    table_rows = ""
    for row in rows:
        status_style = ""
        status_clean = str(row['status']).strip().lower()
        if status_clean and status_clean in status_bg_map:
            bg = status_bg_map[status_clean]
            fg = status_fg_map[status_clean]
            status_style = f'style="background-color: {bg}; color: {fg}; text-align: center; font-weight: bold;"'
        else:
            status_style = f'style="background-color: {PANEL_BG}; color: {TEXT_MAIN}; text-align: center;"'
        
        table_rows += f"""
        <tr>
            <td style="color: {TEXT_MAIN}; text-align: left;">{escape(str(row['metric']))}</td>
            <td style="color: {TEXT_MUTED}; font-family: monospace;">{escape(str(row['baseline_id'][:8]))}</td>
            <td style="color: {TEXT_MUTED};">{escape(str(row['baseline_ts']))}</td>
            <td style="color: {TEXT_MAIN}; text-align: right;">{row['baseline_val']:.4g}</td>
            <td style="color: {TEXT_MAIN}; text-align: right;">{row['contender_val']:.4g}</td>
            <td style="color: {TEXT_MAIN}; text-align: right; font-weight: 500;">{row['delta_pct']:+.2f}%</td>
            <td {status_style}>{escape(status_clean.upper()) if status_clean else 'UNKNOWN'}</td>
        </tr>
        """

    full_table_html = f"""
    <div class="table-card-wrapper">
        {title_html}
        <div class="table-scroll-container">
            <table class="sortable-dashboard-table">
                <thead>
                    <tr>
                        <th data-col="0" style="text-align: left;">Metric <span class="sort-icon">↕</span></th>
                        <th data-col="1" style="text-align: left;">Baseline ID <span class="sort-icon">↕</span></th>
                        <th data-col="2" style="text-align: left;">Baseline Timestamp <span class="sort-icon">↕</span></th>
                        <th data-col="3" style="text-align: right;">Baseline Value <span class="sort-icon">↕</span></th>
                        <th data-col="4" style="text-align: right;">Contender Value <span class="sort-icon">↕</span></th>
                        <th data-col="5" style="text-align: right;">Delta % <span class="sort-icon">↕</span></th>
                        <th data-col="6" style="text-align: center;">Status <span class="sort-icon">↕</span></th>
                    </tr>
                </thead>
                <tbody>
                    {table_rows}
                </tbody>
            </table>
        </div>
    </div>
    """
    return full_table_html


def visualize_chart(df: pd.DataFrame) -> go.Figure | None:
    metrics      = df[ComparisonCols.METRIC].unique()
    contender_id = get_contender_id(df)
    
    if len(metrics) == 0:
        return None

    sample_mdf = df[df[ComparisonCols.METRIC] == metrics[0]].copy()
    timeline = build_ordered_timeline(sample_mdf, contender_id)
    if not timeline:
        return None

    xs = list(range(len(timeline)))

    xtick_labels = []
    for entry in timeline:
        xtick_labels.append(entry["ts_str"])

    colors = px.colors.qualitative.Pastel
    fig    = go.Figure()

    for idx, metric in enumerate(metrics):
        mdf = df[df[ComparisonCols.METRIC] == metric]
        
        all_vals             = []
        sanitized_customdata = []
        
        for entry in timeline:
            if entry["is_contender"]:
                val = mdf[ComparisonCols.CONTENDER_VAL].dropna().iloc[0] if not mdf.empty else np.nan
                cdata = {
                    "type": "Contender",
                    "rid":  escape(str(contender_id[:8])),
                    "ts":   entry["ts_str"].replace("\n", " ")
                }
            else:
                bid = entry["run_id"]
                match = mdf[mdf[ComparisonCols.BASELINE_RUN_ID] == bid]
                val = match[ComparisonCols.BASELINE_VAL].iloc[0] if not match.empty else np.nan
                cdata = {
                    "type": "Baseline",
                    "rid":  escape(str(bid[:8])),
                    "ts":   entry["ts_str"].replace("\n", " ")
                }
            all_vals.append(val)
            sanitized_customdata.append(cdata)

        metric_color = colors[idx % len(colors)]
        num_bars     = len(all_vals)

        line_widths = [0] * (num_bars - 1) + [2.0]
        line_colors = ["rgba(0,0,0,0)"] * (num_bars - 1) + ["rgba(255, 255, 255, 0.4)"]

        fig.add_trace(go.Bar(
            x             = xs,
            y             = all_vals, 
            name          = escape(str(metric)), 
            legendgroup   = str(metric),
            marker_color  = metric_color,
            marker_line_width = line_widths,
            marker_line_color = line_colors,
            text          = [f"{v:.3g}" if pd.notna(v) else "" for v in all_vals], 
            textposition  = "inside", 
            textfont      = dict(color = "#000000"),
            hovertemplate = "<b>" + escape(str(metric)) + "</b><br>Type: %{customdata.type}<br>ID: %{customdata.rid}<br>Time: %{customdata.ts}<br>Value: %{y:.4g}<extra></extra>",
            customdata    = sanitized_customdata,
            legend        = "legend"
        ))

    title_text = f"<b>Time-series chart: Baseline History vs Contender</b><br><span style='font-size:12px; color:{TEXT_MUTED}; font-weight:normal;'>Contender: <span style='color:{CONTENDER_ZONE}; font-weight:bold;'>{escape(str(contender_id[:8]))}</span> | Baselines Tracked: {len(timeline) - 1}</span>"

    fig.update_layout(
        title         = {"text": title_text, "font": dict(color = TEXT_MAIN, size = 14)},
        barmode       = "group", 
        hovermode     = "closest",
        paper_bgcolor = DARK_BG, 
        plot_bgcolor  = PANEL_BG, 
        font          = dict(color = TEXT_MUTED),
        xaxis         = dict(
            tickmode   = "array",
            tickvals   = xs,
            ticktext   = xtick_labels,
            gridcolor  = BORDER_COLOR, 
            linecolor  = BORDER_COLOR, 
            automargin = True, 
            tickangle  = 0
        ), 
        yaxis         = dict(
            gridcolor  = BORDER_COLOR, 
            linecolor  = BORDER_COLOR, 
            automargin = True, 
            autorange  = True, 
            rangemode  = "normal"
        ),
        template      = "plotly_dark", 
        margin        = dict(t = 80, b = 60, l = 50, r = 140), 
        height        = 400,
        showlegend    = True,
        legend        = dict(x = 1.02, y = 1, xanchor = "left", yanchor = "top", bgcolor = "rgba(0,0,0,0)")
    )
    return fig

def visualize_graph(df: pd.DataFrame) -> go.Figure | None:
    metrics      = df[ComparisonCols.METRIC].unique()
    contender_id = get_contender_id(df)
    baseline_ids = get_unique_baselines(df)

    if len(metrics) == 0:
        return None
 
    fig          = go.Figure()
    colors       = px.colors.qualitative.Pastel
    global_xs    = global_timestamps = ctdr_idx = None
    all_y_values = []
 
    for idx, metric in enumerate(metrics):
        mdf      = df[df[ComparisonCols.METRIC] == metric].copy()
        timeline = build_ordered_timeline(mdf, contender_id)
        if not timeline: 
            continue
 
        xs = list(range(len(timeline)))
        ys = [t["value"] for t in timeline]
        all_y_values.extend([v for v in ys if pd.notna(v)])
        
        is_ctdr    = [t["is_contender"] for t in timeline]
        run_ids    = [t["run_id"] for t in timeline]
        timestamps = [t["ts_str"].replace("\n", " ") for t in timeline]
        
        if global_xs is None:
            global_xs         = xs
            global_timestamps = [escape(str(ts)) for ts in timestamps]
            ctdr_idx          = next(i for i, t in enumerate(timeline) if t["is_contender"])
 
        metric_color = colors[idx % len(colors)]
        
        sanitized_customdata = [{
            "type": "Contender" if c else "Baseline", 
            "rid":  escape(str(r[:8])), 
            "ts":   escape(str(t))
        } for c, r, t in zip(is_ctdr, run_ids, timestamps)]

        fig.add_trace(go.Scatter(
            x      = xs, 
            y      = ys, 
            mode   = "lines+markers", 
            name   = escape(str(metric)), 
            line   = dict(color = metric_color, width = 2),
            marker = dict(
                symbol = ["star" if c else "circle" for c in is_ctdr], 
                size   = [16 if c else 8 for c in is_ctdr], 
                color  = metric_color, 
                line   = dict(width = [1.5 if c else 0.5 for c in is_ctdr], 
                color  = ["#000000" if c else metric_color for c in is_ctdr])
            ),
            hovertemplate = "<b>" + escape(str(metric)) + "</b><br>Type: %{customdata.type}<br>ID: %{customdata.rid}<br>Time: %{customdata.ts}<br>Value: %{y:.4g}<extra></extra>",
            customdata    = sanitized_customdata,
            legend        = "legend",
            cliponaxis    = False 
        ))

    if global_xs is not None and ctdr_idx is not None:
        fig.add_vrect(
            x0         = ctdr_idx - 0.4, 
            x1         = ctdr_idx + 0.4, 
            fillcolor  = CONTENDER_ZONE, 
            opacity    = 0.06, 
            layer      = "below", 
            line_width = 0
        )
        fig.add_vline(x = ctdr_idx - 0.5, line_width = 1, line_dash = "dash", line_color = BORDER_COLOR)
        fig.update_layout(xaxis = dict(
            tickmode   = "array", 
            tickvals   = global_xs, 
            ticktext   = global_timestamps, 
            tickangle  = -15, 
            gridcolor  = BORDER_COLOR, 
            linecolor  = BORDER_COLOR, 
            automargin = True
        ))

    yaxis_config: dict = dict(
        gridcolor  = BORDER_COLOR, 
        linecolor  = BORDER_COLOR,
        autorange  = True,
        rangemode  = "normal"
    )

    title_text = f"<b>Time-series graph: Baseline History vs Contender</b><br><span style='font-size:12px; color:{TEXT_MUTED}; font-weight:normal;'>Contender: <span style='color:{CONTENDER_ZONE}; font-weight:bold;'>{escape(str(contender_id[:8]))}</span> | Baselines Tracked: {len(baseline_ids)}</span>"

    fig.update_layout(
        title         = {"text": title_text, "font": dict(color = TEXT_MAIN, size = 14)},
        paper_bgcolor = DARK_BG, 
        plot_bgcolor  = PANEL_BG, 
        font          = dict(color = TEXT_MUTED),
        yaxis         = yaxis_config, 
        template      = "plotly_dark",
        margin        = dict(t = 100, b = 60, l = 50, r = 140), 
        height        = 400, 
        hovermode     = "closest", 
        showlegend    = True,
        legend        = dict(x = 1.02, y = 1, xanchor = "left", yanchor = "top", bgcolor = "rgba(0,0,0,0)")
    )
    return fig


def create_group_panel(table_html: str | None, chart_fig: go.Figure | None, graph_fig: go.Figure | None) -> str:
    panel_html = '<div class="dashboard-grid">'
    if table_html:
        panel_html += f'<div class="grid-row-full">{table_html}</div>'
    if chart_fig:
        chart_raw   = chart_fig.to_html(include_plotlyjs = False, full_html = False, config = {"responsive": True})
        panel_html += f'<div class="grid-row-full style-card-gap">{chart_raw}</div>'
    if graph_fig:
        graph_raw   = graph_fig.to_html(include_plotlyjs = False, full_html = False, config = {"responsive": True})
        panel_html += f'<div class="grid-row-full style-card-gap">{graph_raw}</div>'
    panel_html += '</div>'
    return panel_html


def build_tabbed_index_html(tabs_data: dict[str, str]) -> None:
    tab_buttons  = ""
    tab_contents = ""
    
    for idx, (group_name, grid_html) in enumerate(tabs_data.items()):
        active_class  = "active" if idx == 0 else ""
        display_style = "block"  if idx == 0 else "none"
        
        tab_id = safe_id(group_name)
        tab_buttons  += f'<button class="tab-btn {active_class}" data-target="{tab_id}">{escape(str(group_name)).upper()}</button>\n'
        tab_contents += f'<div id="{tab_id}" class="tab-content" style="display:{display_style};">{grid_html}</div>\n'

    html_payload = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>PMICW Dashboard</title>
        <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background-color: {DARK_BG}; color: {TEXT_MAIN}; margin: 0; padding: 20px; }}
            .header {{ margin-bottom: 25px; border-bottom: 1px solid {BORDER_COLOR}; padding-bottom: 15px; }}
            .header h1 {{ margin: 0 0 5px 0; font-size: 24px; letter-spacing: -0.5px; }}
            .header p {{ margin: 0; color: {TEXT_MUTED}; font-size: 14px; }}
            
            .tab-bar {{ display: flex; gap: 8px; border-bottom: 2px solid {BORDER_COLOR}; padding-bottom: 0px; margin-bottom: 20px; }}
            .tab-btn {{ background: none; border: none; color: {TEXT_MUTED}; padding: 12px 20px; font-size: 14px; font-weight: 600; cursor: pointer; transition: all 0.2s ease; border-bottom: 3px solid transparent; margin-bottom: -2px; }}
            .tab-btn:hover {{ color: {TEXT_MAIN}; background-color: rgba(255,255,255,0.03); }}
            .tab-btn.active {{ color: {CONTENDER_ZONE}; border-bottom-color: {CONTENDER_ZONE}; }}
            
            .dashboard-grid {{ display: flex; flex-direction: column; gap: 24px; width: 100%; }}
            .grid-row-full {{ width: 100%; border-radius: 6px; overflow: hidden; background: {DARK_BG}; }}
            .style-card-gap {{ border: 1px solid {BORDER_COLOR}; padding: 10px; box-sizing: border-box; margin-bottom: 10px; }}
            
            .table-card-wrapper {{ background-color: {DARK_BG}; border-radius: 6px; padding: 10px 10px 0 10px; box-sizing: border-box; }}
            .table-title-area {{ padding-bottom: 15px; font-family: sans-serif; }}
            .table-main-title {{ font-size: 14px; font-weight: bold; color: {TEXT_MAIN}; margin-bottom: 4px; }}
            .table-sub-title {{ font-size: 12px; color: {TEXT_MUTED}; }}
            .table-scroll-container {{ max-height: 260px; overflow-y: auto; border: 1px solid {BORDER_COLOR}; border-radius: 4px; }}
            
            .sortable-dashboard-table {{ width: 100%; border-collapse: collapse; font-size: 12px; font-family: sans-serif; text-align: left; }}
            .sortable-dashboard-table th {{ 
                position: sticky; top: 0; background-color: #111827; color: {TEXT_MAIN}; 
                padding: 8px 10px; font-weight: 600; font-size: 13px; z-index: 10; 
                border-bottom: 2px solid {BORDER_COLOR}; cursor: pointer; user-select: none;
            }}
            .sortable-dashboard-table th:hover {{ background-color: #1f2937; }}
            .sortable-dashboard-table td {{ padding: 6px 10px; border-bottom: 1px solid {BORDER_COLOR}; background-color: {PANEL_BG}; vertical-align: middle; }}
            .sort-icon {{ font-size: 10px; color: {TEXT_MUTED}; margin-left: 3px; }}
            
            .tab-content {{ animation: fadeIn 0.3s ease; }}
            @keyframes fadeIn {{ from {{ opacity: 0; }} to {{ opacity: 1; }} }}
        </style>
        <script>
            document.addEventListener("DOMContentLoaded", function() {{
                
                const tabBar = document.querySelector(".tab-bar");
                if (tabBar) {{
                    tabBar.addEventListener("click", function(e) {{
                        const targetButton = e.target.closest(".tab-btn");
                        if (!targetButton) return;

                        const tabName = targetButton.getAttribute("data-target");
                        const tabContents = document.getElementsByClassName("tab-content");
                        for (let i = 0; i < tabContents.length; i++) {{
                            tabContents[i].style.display = "none";
                        }}

                        const tabButtons = document.getElementsByClassName("tab-btn");
                        for (let i = 0; i < tabButtons.length; i++) {{
                            tabButtons[i].classList.remove("active");
                        }}

                        const currentActiveTab = document.getElementById(tabName);
                        if (currentActiveTab) {{
                            currentActiveTab.style.display = "block";
                            targetButton.classList.add("active");

                            const plots = currentActiveTab.getElementsByClassName("js-plotly-plot");
                            for (let i = 0; i < plots.length; i++) {{
                                Plotly.Plots.resize(plots[i]);
                            }}
                        }}
                    }});
                }}

                document.body.addEventListener("click", function(e) {{
                    const headerCell = e.target.closest(".sortable-dashboard-table th");
                    if (!headerCell) return;

                    const colIndex = parseInt(headerCell.getAttribute("data-col"), 10);
                    const table = headerCell.closest("table");
                    const targetBody = table.querySelector("tbody");
                    const rowsArray = Array.from(targetBody.querySelectorAll("tr"));
                    const sortingAscending = headerCell.getAttribute("data-order") !== "asc";
                    
                    rowsArray.sort(function(rowA, rowB) {{
                        const cellTextA = rowA.children[colIndex].innerText.trim();
                        const cellTextB = rowB.children[colIndex].innerText.trim();
                        
                        const parseDateA = Date.parse(cellTextA);
                        const parseDateB = Date.parse(cellTextB);
                        if (!isNaN(parseDateA) && !isNaN(parseDateB) && isNaN(Number(cellTextA))) {{
                            return sortingAscending ? parseDateA - parseDateB : parseDateB - parseDateA;
                        }}
                        const floatValA = parseFloat(cellTextA.replace(/[^\\d.-]/g, ''));
                        const floatValB = parseFloat(cellTextB.replace(/[^\\d.-]/g, ''));
                        if (!isNaN(floatValA) && !isNaN(floatValB)) {{
                            return sortingAscending ? floatValA - floatValB : floatValB - floatValA;
                        }}

                        return sortingAscending ? cellTextA.localeCompare(cellTextB) : cellTextB.localeCompare(cellTextA);
                    }});
                    
                    headerCell.closest("thead").querySelectorAll("th").forEach(function(th) {{ th.removeAttribute("data-order"); }});
                    headerCell.setAttribute("data-order", sortingAscending ? "asc" : "desc");
                    
                    targetBody.innerHTML = '';
                    rowsArray.forEach(function(row) {{ targetBody.appendChild(row); }});
                }});

                window.addEventListener("resize", function() {{
                    const elements = document.getElementsByClassName("js-plotly-plot");
                    for (let i = 0; i < elements.length; i++) {{
                        Plotly.Plots.resize(elements[i]);
                    }}
                }});
            }});
        </script>
    </head>
    <body>

        <div class="header">
            <h1>PMICW Dashboard</h1>
            <p>Automated CI Evaluation Results Timeline &bull; Static Dashboard Archive Site</p>
        </div>

        <div class="tab-bar">
            {tab_buttons}
        </div>

        {tab_contents}

    </body>
    </html>
    """
    INDEX_HTML.write_text(html_payload, encoding = "utf-8")
    print(f"Dashboard index.html saved to: {INDEX_HTML}")

def build_ordered_timeline(mdf: pd.DataFrame, contender_id: str) -> list[dict]:
    records        = []
    seen_baselines = set()

    for _, row in mdf.iterrows():
        bid = row[ComparisonCols.BASELINE_RUN_ID]
        if bid in seen_baselines: 
            continue

        seen_baselines.add(bid)
        ts_raw = row[ComparisonCols.TIMESTAMP]
        ts_obj = pd.to_datetime(ts_raw, errors = "coerce")
        records.append({
            "run_id":       bid, 
            "ts":           ts_obj,
            "ts_str":       ts_obj.strftime("%Y-%m-%d\n%H:%M:%S") if pd.notna(ts_obj) else str(ts_raw),
            "value":        row[ComparisonCols.BASELINE_VAL], 
            "is_contender": False,
        })

    records.sort(key = lambda r: r["ts"] if pd.notna(r["ts"]) else pd.Timestamp.min)
    
    if not mdf.empty:
        first = mdf.iloc[0]

        ctdr_ts_raw = "Current Run"
        ctdr_ts_obj = pd.to_datetime(ctdr_ts_raw, errors = "coerce")
        
        records.append({
            "run_id":       contender_id, 
            "ts":           ctdr_ts_obj if pd.notna(ctdr_ts_obj) else pd.Timestamp.now(),
            "ts_str":       ctdr_ts_obj.strftime("%Y-%m-%d\n%H:%M:%S") if pd.notna(ctdr_ts_obj) else str(ctdr_ts_raw),
            "value":        first[ComparisonCols.CONTENDER_VAL], 
            "is_contender": True,
        })
        
    return records

def build_timeline_records(df: pd.DataFrame) -> list[dict]:
    return [{
        "metric":        r[ComparisonCols.METRIC],         "baseline_id":  r[ComparisonCols.BASELINE_RUN_ID],
        "baseline_ts":   str(r[ComparisonCols.TIMESTAMP]), "baseline_val": r[ComparisonCols.BASELINE_VAL],
        "contender_val": r[ComparisonCols.CONTENDER_VAL],  "delta_pct":    r[ComparisonCols.DELTA_PCT] if pd.notna(r[ComparisonCols.DELTA_PCT]) else 0.0,
        "status":        r.get(ComparisonCols.STATUS, ""),
    } for _, r in df.iterrows()]

def get_contender_id(df: pd.DataFrame) -> str:
    col = ComparisonCols.CONTENDER_RUN_ID
    return str(df[col].iloc[0]) if col in df.columns else "contender"

def get_unique_baselines(df: pd.DataFrame) -> list[str]:
    return list(df[ComparisonCols.BASELINE_RUN_ID].unique())

def safe_id(value) -> str:
    value = str(value)
    value = value.strip().lower()
    value = re.sub(r'[^a-z0-9_-]+', '-', value)
    value = re.sub(r'-{2,}', '-', value).strip('-')

    if not value or not value[0].isalpha():
        value = f"tab-{value}"

    return value