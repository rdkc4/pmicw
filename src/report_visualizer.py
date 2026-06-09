import datetime
from pathlib import Path
import sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.figure import Figure
import numpy as np
import pandas as pd

from cli_parser import VisualFormatOptions
from comparison_context import ComparisonCols
from plot_config import PlotGroupConfig

REPORT_DIR = Path.cwd() / "visual"

BASELINE_COLOR   = "#A0AEC0"
CONTENDER_COLOR  = "#3182CE"
CONTENDER_MARKER = "*"
BASELINE_MARKER  = "o"
 
CONTENDER_ZORDER = 5
BASELINE_ZORDER  = 3

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
        visual_df.replace([np.inf, -np.inf], np.nan, inplace = True).dropna(subset = [
            ComparisonCols.BASELINE_VAL,
            ComparisonCols.CONTENDER_VAL,
            ComparisonCols.DELTA_ABS,
            ComparisonCols.DELTA_PCT
        ])

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
        status_color = {
            "regression":    "#ffd6d6",
            "improvement":   "#d6ffd6",
            "noise":         "#fffbe6",
            "interesting":   "#e6f0ff",
        }.get(row["status"], "#ffffff")
 
        html_rows += (
            f"<tr style='background:{status_color}'>"
            f"<td>{row['metric']}</td>"
            f"<td>{row['baseline_id'][:8]}</td>"
            f"<td>{row['baseline_ts']}</td>"
            f"<td>{row['baseline_val']:.4g}</td>"
            f"<td>{row['contender_val']:.4g}</td>"
            f"<td>{row['delta_pct']:+.2f}%</td>"
            f"<td>{row['status']}</td>"
            "</tr>\n"
        )
 
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset='utf-8'>
        <style>
            body{{font-family:sans-serif;font-size:13px}}
            table{{border-collapse:collapse;width:100%}}
            th,td{{border:1px solid #ccc;padding:6px 10px;text-align:left}}
            th{{background:#2d3e50;color:#fff;cursor:pointer}}
            tr:hover{{filter:brightness(0.95)}}
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
        <h2>Metric comparison table</h2>
        <p>Contender run: <strong>{get_contender_id(df)[:8]}</strong> &nbsp;|&nbsp;
        Baselines: {len(get_unique_baselines(df))}</p>
        <table id="diffTable">
            <thead>
                <tr>
                    <th onclick="sortTable(0)">Metric</th>
                    <th onclick="sortTable(1)">Baseline ID</th>
                    <th onclick="sortTable(2)">Baseline timestamp</th>
                    <th onclick="sortTable(3)">Baseline value</th>
                    <th onclick="sortTable(4)">Contender value</th>
                    <th onclick="sortTable(5)">Delta %</th>
                    <th onclick="sortTable(6)">Status</th>
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
    n_metrics    = len(metrics)

    if n_metrics == 0:
        return

    n_baselines  = len(baseline_ids)
    group_width  = 0.8
    bar_width    = group_width / (n_metrics + 1)

    fig, ax      = plt.subplots(figsize = (max(10, 2 * n_baselines + 4), 5))
    x            = np.arange(n_baselines + 1)
    xtick_labels = [f"{bid[:8]}" for bid in baseline_ids] + [f"{contender_id[:8]} (Contender)"]
    
    cmap          = plt.cm.get_cmap("tab10")
    METRIC_COLORS = {metric: cmap(i) for i, metric in enumerate(metrics)}

    for i, metric in enumerate(metrics):
        mdf = df[df[ComparisonCols.METRIC] == metric]

        baseline_vals = [
            mdf[mdf[ComparisonCols.BASELINE_RUN_ID] == bid][ComparisonCols.BASELINE_VAL].iloc[0]
            if not mdf[mdf[ComparisonCols.BASELINE_RUN_ID] == bid].empty else np.nan
            for bid in baseline_ids
        ]

        contender_val = mdf[ComparisonCols.CONTENDER_VAL].dropna().iloc[0] if not mdf.empty else np.nan
        all_vals      = baseline_vals + [contender_val]
        metric_color  = METRIC_COLORS[metric]
        
        offset = (i - n_metrics / 2) * bar_width + bar_width / 2
        
        ax.bar(
            x[:n_baselines] + offset, 
            baseline_vals, 
            width     = bar_width, 
            color     = metric_color, 
            alpha     = 0.6, 
            edgecolor = "white"
        )
        
        ax.bar(
            x[n_baselines:] + offset, 
            [contender_val], 
            width     = bar_width, 
            color     = metric_color, 
            alpha     = 1.0, 
            edgecolor = "black", 
            linewidth = 1.5, 
            label     = metric
        )

        for bar, val in zip(x + offset, all_vals):
            if pd.notna(val):
                ax.text(bar, val * 1.01, f"{val:.3g}", ha = "center", va = "bottom", fontsize = 8)

    ax.set_xticks(x)
    ax.set_xticklabels(xtick_labels, fontsize = 9)
    ax.set_ylabel("Value")
    
    ax.legend(
        title                = "Time-series chart: Baseline History vs Contender\n", 
        loc                  = "lower center",         
        bbox_to_anchor       = (0.5, 1.02),            
        ncol                 = min(5, n_metrics),      
        fontsize             = 9,
        title_fontproperties = {"weight": "bold", "size": 12},
        frameon              = True,
        facecolor            = "white",
        edgecolor            = "#E2E8F0"
    )
    
    ax.yaxis.grid(True, linestyle = "--", alpha = 0.5)
    ax.set_axisbelow(True)

    fig.tight_layout(rect = (0, 0, 1, 0.88))
    
    save_as_html(fig, report_path)
    print(f"Chart saved: {report_path}")
 
def visualize_graph(df: pd.DataFrame, report_path: Path) -> None:
    metrics      = df[ComparisonCols.METRIC].unique()
    n_metrics    = len(metrics)
    contender_id = get_contender_id(df)

    if n_metrics == 0:
        return
 
    fig, ax = plt.subplots(figsize = (max(10, 3 * n_runs(df)), 6))
    
    cmap          = plt.cm.get_cmap("tab10")
    METRIC_COLORS = {metric: cmap(i) for i, metric in enumerate(metrics)}

    global_xs = global_timestamps = ctdr_idx = None
 
    for metric in metrics:
        mdf      = df[df[ComparisonCols.METRIC] == metric].copy()
        timeline = build_ordered_timeline(mdf, contender_id)

        if not timeline:
            continue
 
        xs         = list(range(len(timeline)))
        ys         = [t["value"]        for t in timeline]
        is_ctdr    = [t["is_contender"] for t in timeline]
        run_ids    = [t["run_id"]       for t in timeline]
        timestamps = [t["ts_str"]       for t in timeline]
        
        if global_xs is None:
            global_xs         = xs
            global_timestamps = timestamps
            ctdr_idx          = next(idx for idx, t in enumerate(timeline) if t["is_contender"])
 
        metric_color          = METRIC_COLORS[metric]
        ax.plot(xs, ys, color = metric_color, linewidth = 1.5, alpha = 0.7, zorder = 2, label = metric)
 
        for x, y, contender, _ in zip(xs, ys, is_ctdr, run_ids):
            if contender:
                ax.scatter(
                    x, y,
                    s          = 220, 
                    marker     = CONTENDER_MARKER,
                    color      = metric_color,          
                    edgecolors = "black",               
                    linewidths = 1.5,
                    zorder     = CONTENDER_ZORDER,
                )
                ax.annotate(
                    f"CONTENDER\n{y:.3g}",
                    xy         = (x, y), 
                    xytext     = (6, 8), 
                    textcoords = "offset points",
                    fontsize   = 7.5, 
                    color      = metric_color, 
                    fontweight = "bold",
                )
            else:
                ax.scatter(
                    x, y,
                    s          = 70, 
                    marker     = BASELINE_MARKER,
                    color      = metric_color, 
                    edgecolors = "white", 
                    linewidths = 0.6,
                    zorder     = BASELINE_ZORDER,
                )
                ax.annotate(
                    f"{y:.3g}",
                    xy         = (x, y), 
                    xytext     = (4, 6), 
                    textcoords = "offset points",
                    fontsize   = 7, 
                    color      = "#3a3a3a",
                )

    if global_xs is not None and global_timestamps is not None and ctdr_idx is not None:
        ax.axvspan(ctdr_idx - 0.4, ctdr_idx + 0.4, color = "#A0AEC0", alpha = 0.08, zorder = 1)
        ax.axvline(ctdr_idx - 0.5, color = "#ccc", linewidth = 0.8, linestyle = "--", zorder = 1)
 
        ax.set_xticks(global_xs)
        ax.set_xticklabels([str(ts) for ts in global_timestamps], fontsize = 8, rotation = 20, ha = "right")
        ax.set_xlim(-0.6, len(global_xs) - 0.4)
    else:
        print("Warning: No valid timeline data found to build graph axis layout.", file = sys.stderr)
        return

    ax.set_ylabel("Value")
    ax.yaxis.grid(True, linestyle = "--", alpha = 0.4)
    ax.set_axisbelow(True)

    ax.legend(
        title                = "Time-series graph: Baseline History vs Contender\n", 
        loc                  = "lower center",         
        bbox_to_anchor       = (0.5, 1.02),            
        ncol                 = min(5, n_metrics),      
        fontsize             = 9,
        title_fontproperties = {"weight": "bold", "size": 12},
        frameon              = True,
        facecolor            = "white",
        edgecolor            = "#E2E8F0"
    )

    fig.tight_layout(rect = (0, 0, 1, 0.93))
    
    save_as_html(fig, report_path)
    print(f"Graph saved: {report_path}")

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

def n_runs(df: pd.DataFrame) -> int:
    return len(get_unique_baselines(df)) + 1

def add_legend(fig: Figure) -> None:
    baseline_patch  = mpatches.Patch(color = BASELINE_COLOR,  label = "Baseline runs")
    contender_patch = mpatches.Patch(color = CONTENDER_COLOR, label = "Contender run")
    fig.legend(
        handles    = [baseline_patch, contender_patch],
        loc        = "upper right", 
        fontsize   = 10, 
        framealpha = 0.9,
    )

def save_as_html(fig: Figure, path: Path) -> None:
    import io

    buf = io.StringIO()
    fig.savefig(buf, format = "svg", bbox_inches = "tight")
    plt.close(fig)
    svg_content = buf.getvalue()

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset='utf-8'>
        <style>
            body{{margin:0;background:#f5f5f5;display:flex;justify-content:center;padding:20px}}
            svg{{max-width:100%;box-shadow:0 2px 12px rgba(0,0,0,.15);background:#fff}}
        </style>
    </head>
    <body>
        {svg_content}
    </body>
    </html>
    """

    path.write_text(html, encoding = "utf-8")

def generate_report_path(relative_path, format: VisualFormatOptions, ext: str) -> Path:
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    return REPORT_DIR / f"{relative_path}_{format}_{timestamp}.{ext}"