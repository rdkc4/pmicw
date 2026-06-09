import datetime
from pathlib import Path
import sys
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px

from cli_parser import VisualFormatOptions
from comparison_context import ComparisonCols
from plot_config import PlotGroupConfig

REPORT_DIR = Path.cwd() / "visual"

DARK_BG        = "#0f172a"
PANEL_BG       = "#1e293b"
BORDER_COLOR   = "#334155"
TEXT_MAIN      = "#f8fafc"
TEXT_MUTED     = "#94a3b8"
CONTENDER_ZONE = "#38bdf8"

def visualize_report(
    df:             pd.DataFrame,
    plot_groups:    dict[str, PlotGroupConfig],
    visual_formats: list[VisualFormatOptions],
    report_path:    str
) -> None:
    REPORT_DIR.mkdir(parents = True, exist_ok = True)

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

        group_path = f"{report_path}_{group_name}"

        if VisualFormatOptions.TABLE in visual_formats:
            visualize_table(visual_df, generate_report_path(group_path, VisualFormatOptions.TABLE, "html"))

        if VisualFormatOptions.CHART in visual_formats:
            visualize_chart(visual_df, generate_report_path(group_path, VisualFormatOptions.CHART, "html"))

        if VisualFormatOptions.GRAPH in visual_formats:
            visualize_graph(visual_df, generate_report_path(group_path, VisualFormatOptions.GRAPH, "html"))

def visualize_table(df: pd.DataFrame, report_path: Path) -> None:
    rows = build_timeline_records(df)
    if not rows:
        return
 
    html_rows = ""
    for row in rows:
        status_styles = {
            "regression":    "background:#7f1d1d; color:#fecaca;", 
            "improvement":   "background:#14532d; color:#bbf7d0;", 
            "noise":         "background:#78350f; color:#fef08a;", 
            "interesting":   "background:#1e3a8a; color:#bfdbfe;", 
        }.get(row["status"], "background:#1e293b; color:#f8fafc;")
 
        html_rows += (
            f"<tr style='background:{PANEL_BG}'>"
            f"<td>{row['metric']}</td>"
            f"<td>{row['baseline_id'][:8]}</td>"
            f"<td>{row['baseline_ts']}</td>"
            f"<td>{row['baseline_val']:.4g}</td>"
            f"<td>{row['contender_val']:.4g}</td>"
            f"<td>{row['delta_pct']:+.2f}%</td>"
            f"<td style='{status_styles} font-weight:bold; text-align:center;'>{row['status'].upper()}</td>"
            "</tr>\n"
        )
 
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset='utf-8'>
        <style>
            body{{font-family:sans-serif;font-size:13px;padding:20px;background:{DARK_BG};color:{TEXT_MAIN};}}
            table{{border-collapse:collapse;width:100%;box-shadow:0 4px 6px -1px rgba(0,0,0,0.5);background:{PANEL_BG};}}
            th,td{{border:1px solid {BORDER_COLOR};padding:10px 14px;text-align:left}}
            th{{background:#0f172a;color:{TEXT_MAIN};cursor:pointer}}
            tr:hover{{filter:brightness(1.2);}}
            strong{{color:{CONTENDER_ZONE};}}
        </style>
        <script>
        function sortTable(n) {{
          var table=document.getElementById("diffTable"),rows,i,x,y,dir="asc",switching=true,shouldSwitch;
          while(switching) {{
            switching=false;rows=table.rows;
            for(i=1;i<rows.length-1;i++) {{
              shouldSwitch=false;x=rows[i].getElementsByTagName("TD")[n];
              y=rows[i+1].getElementsByTagName("TD")[n];
              if(dir=="asc" && x.innerHTML.toLowerCase()>y.innerHTML.toLowerCase()){{
                shouldSwitch=true;break;
              }}
              if(dir=="desc" && x.innerHTML.toLowerCase()<y.innerHTML.toLowerCase()){{
                shouldSwitch=true;break;
              }}
            }}
            if(shouldSwitch){{
              rows[i].parentNode.insertBefore(rows[i+1],rows[i]);
              switching=true;
            }} else {{
              if(dir=="asc") dir="desc"; else break;
            }}
          }}
        }}
        </script>
    </head>
    <body>
        <h2 style="margin-bottom:4px;">Metric Comparison Table</h2>
        <p style="color:{TEXT_MUTED}; margin-top:0; margin-bottom:20px;">Contender run: <strong>{get_contender_id(df)[:8]}</strong> &nbsp;|&nbsp;
        Baselines tracked: {len(get_unique_baselines(df))}</p>
        <table id="diffTable">
            <thead>
                <tr>
                    <th onclick="sortTable(0)">Metric</th>
                    <th onclick="sortTable(1)">Baseline ID</th>
                    <th onclick="sortTable(2)">Baseline timestamp</th>
                    <th onclick="sortTable(3)">Baseline value</th>
                    <th onclick="sortTable(4)">Contender value</th>
                    <th onclick="sortTable(5)">Delta %</th>
                    <th onclick="sortTable(6)" style="text-align:center;">Status</th>
                </tr>
            </thead>
            <tbody>
                {html_rows}
            </tbody>
        </table>
    </body>
    </html>
    """
    report_path.write_text(html, encoding = "utf-8")
    print(f"Table saved: {report_path}")
 
def visualize_chart(df: pd.DataFrame, report_path: Path) -> None:
    metrics      = df[ComparisonCols.METRIC].unique()
    contender_id = get_contender_id(df)
    baseline_ids = get_unique_baselines(df)
    
    if len(metrics) == 0:
        return

    xtick_labels = [f"{bid[:8]}" for bid in baseline_ids] + [f"<b>{contender_id[:8]}</b><br><span style='color:{CONTENDER_ZONE}'>Contender</span>"]
    colors       = px.colors.qualitative.Pastel

    fig = go.Figure()

    for idx, metric in enumerate(metrics):
        mdf = df[df[ComparisonCols.METRIC] == metric]

        baseline_vals = [
            mdf[mdf[ComparisonCols.BASELINE_RUN_ID] == bid][ComparisonCols.BASELINE_VAL].iloc[0]
            if not mdf[mdf[ComparisonCols.BASELINE_RUN_ID] == bid].empty else np.nan
            for bid in baseline_ids
        ]
        contender_val = mdf[ComparisonCols.CONTENDER_VAL].dropna().iloc[0] if not mdf.empty else np.nan
        all_vals      = baseline_vals + [contender_val]
        metric_color  = colors[idx % len(colors)]

        fig.add_trace(go.Bar(
            x             = xtick_labels,
            y             = all_vals,
            name          = metric,
            marker_color  = metric_color,
            text          = [f"{v:.3g}" if pd.notna(v) else "" for v in all_vals],
            textposition  = "auto",
            textfont      = dict(color = "#000000"),
            hovertemplate = f"<b>{metric}</b><br>Run: %{{x}}<br>Value: %{{y:.4g}}<extra></extra>"
        ))

    fig.update_layout(
        title = {
            "text": "<b>Time-series chart: Baseline History vs Contender</b>",
            "y": 0.95, "x": 0.5, "xanchor": "center", "yanchor": "top",
            "font": dict(color = TEXT_MAIN, size = 16)
        },
        barmode          = "group",
        paper_bgcolor    = DARK_BG,
        plot_bgcolor     = PANEL_BG,
        font             = dict(color = TEXT_MUTED),
        xaxis            = dict(gridcolor = BORDER_COLOR, linecolor = BORDER_COLOR, title = dict(text = "Run Identifiers", font = dict(color = TEXT_MAIN))),
        yaxis            = dict(gridcolor = BORDER_COLOR, linecolor = BORDER_COLOR, title = dict(text = "Value", font = dict(color = TEXT_MAIN))),
        legend           = dict(font = dict(color = TEXT_MAIN), title_font = dict(color = TEXT_MAIN)),
        template         = "plotly_dark",
        margin           = dict(t = 100, b = 50, l = 60, r = 40),
        height           = 550
    )

    save_plotly_html(fig, report_path)
    print(f"Barchart saved: {report_path}")
 
def visualize_graph(df: pd.DataFrame, report_path: Path) -> None:
    metrics      = df[ComparisonCols.METRIC].unique()
    contender_id = get_contender_id(df)

    if len(metrics) == 0:
        return
 
    fig    = go.Figure()
    colors = px.colors.qualitative.Pastel

    global_xs = global_timestamps = ctdr_idx = None
 
    for idx, metric in enumerate(metrics):
        mdf = df[df[ComparisonCols.METRIC] == metric].copy()
        timeline = build_ordered_timeline(mdf, contender_id)

        if not timeline:
            continue
 
        xs         = list(range(len(timeline)))
        ys         = [t["value"]                     for t in timeline]
        is_ctdr    = [t["is_contender"]              for t in timeline]
        run_ids    = [t["run_id"]                    for t in timeline]
        timestamps = [t["ts_str"].replace("\n", " ") for t in timeline]
        
        if global_xs is None:
            global_xs         = xs
            global_timestamps = timestamps
            ctdr_idx          = next(i for i, t in enumerate(timeline) if t["is_contender"])
 
        metric_color = colors[idx % len(colors)]

        symbols       = ["star" if c else "circle" for c in is_ctdr]
        sizes         = [16 if c else 8 for c in is_ctdr]
        marker_border = ["#000000" if c else metric_color for c in is_ctdr]
        border_widths = [1.5 if c else 0.5 for c in is_ctdr]
        
        text_labels   = [f"<b>CONTENDER</b><br>{y:.3g}" if c else f"{y:.3g}" for y, c in zip(ys, is_ctdr)]
        text_positions = ["top center" if c else "bottom center" for c in is_ctdr]

        fig.add_trace(go.Scatter(
            x             = xs,
            y             = ys,
            mode          = "lines+markers+text",
            name          = metric,
            line          = dict(color=metric_color, width=2),
            marker        = dict(
                symbol    = symbols,
                size      = sizes,
                color     = metric_color,
                line      = dict(width=border_widths, color=marker_border)
            ),
            text          = text_labels,
            textposition  = text_positions,
            textfont      = dict(size=9, color=TEXT_MAIN),
            hovertemplate = "<b>" + metric + "</b><br>" +
                            "Type: %{customdata.type}<br>" +
                            "ID: %{customdata.rid}<br>" +
                            "Time: %{customdata.ts}<br>" +
                            "Value: %{y:.4g}<extra></extra>",
            customdata    = [
                {"type": "Contender" if c else "Baseline", "rid": r[:8], "ts": t} 
                for c, r, t in zip(is_ctdr, run_ids, timestamps)
            ]
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

        fig.update_layout(
            xaxis = dict(
                tickmode  = "array",
                tickvals  = global_xs,
                ticktext  = global_timestamps,
                tickangle = -20,
                gridcolor = BORDER_COLOR,
                linecolor = BORDER_COLOR,
                title     = dict(text="Timeline Runs", font=dict(color=TEXT_MAIN))
            )
        )
    else:
        print("Warning: No valid timeline data found to build graph axis layout.", file = sys.stderr)
        return

    fig.update_layout(
        title = {
            "text": "<b>Time-series graph: Baseline History vs Contender</b>",
            "y": 0.95, "x": 0.5, "xanchor": "center", "yanchor": "top",
            "font": dict(color = TEXT_MAIN, size = 16)
        },
        paper_bgcolor    = DARK_BG,
        plot_bgcolor     = PANEL_BG,
        font             = dict(color = TEXT_MUTED),
        yaxis            = dict(gridcolor = BORDER_COLOR, linecolor = BORDER_COLOR, title = dict(text = "Value", font = dict(color = TEXT_MAIN))),
        legend           = dict(font = dict(color = TEXT_MAIN), title_font = dict(color = TEXT_MAIN)),
        template         = "plotly_dark",
        margin           = dict(t = 100, b = 80, l = 60, r = 40),
        height           = 550,
        hovermode        = "closest"
    )

    save_plotly_html(fig, report_path)
    print(f"Line graph saved: {report_path}")

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
        first  = mdf.iloc[0]
        ts_raw = first[ComparisonCols.TIMESTAMP]
        ts_obj = pd.to_datetime(ts_raw, errors = "coerce")
        records.append({
            "run_id":       contender_id,
            "ts":           ts_obj,
            "ts_str":       "CONTENDER\n" + (ts_obj.strftime("%Y-%m-%d\n%H:%M:%S") if pd.notna(ts_obj) else ""),
            "value":        first[ComparisonCols.CONTENDER_VAL],
            "is_contender": True,
        })
 
    return records

def build_timeline_records(df: pd.DataFrame) -> list[dict]:
    records      = []
    for _, row in df.iterrows():
        records.append({
            "metric":        row[ComparisonCols.METRIC],
            "baseline_id":   row[ComparisonCols.BASELINE_RUN_ID],
            "baseline_ts":   str(row[ComparisonCols.TIMESTAMP]),
            "baseline_val":  row[ComparisonCols.BASELINE_VAL],
            "contender_val": row[ComparisonCols.CONTENDER_VAL],
            "delta_pct":     row[ComparisonCols.DELTA_PCT] if pd.notna(row[ComparisonCols.DELTA_PCT]) else 0.0,
            "status":        row.get(ComparisonCols.STATUS, ""),
        })
    return records

def get_contender_id(df: pd.DataFrame) -> str:
    col = ComparisonCols.CONTENDER_RUN_ID
    if col in df.columns:
        return str(df[col].iloc[0])
    return "contender"

def get_unique_baselines(df: pd.DataFrame) -> list[str]:
    return list(df[ComparisonCols.BASELINE_RUN_ID].unique())

def save_plotly_html(fig: go.Figure, path: Path) -> None:
    html_content = fig.to_html(include_plotlyjs = "cdn", full_html = True)
    path.write_text(html_content, encoding = "utf-8")

def generate_report_path(relative_path, format: VisualFormatOptions, ext: str) -> Path:
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    return REPORT_DIR / f"{relative_path}_{format}_{timestamp}.{ext}"