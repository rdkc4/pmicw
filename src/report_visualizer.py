import datetime
from pathlib import Path
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

BASELINE_COLOR   = "#5B8DB8"
CONTENDER_COLOR  = "#E8614B"
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
    for r in rows:
        status_color = {
            "regression":  "#ffd6d6",
            "improvement": "#d6ffd6",
            "noise":       "#fffbe6",
            "interesting": "#e6f0ff",
        }.get(r["status"], "#ffffff")
 
        html_rows += (
            f"<tr style='background:{status_color}'>"
            f"<td>{r['metric']}</td>"
            f"<td>{r['baseline_id'][:8]}</td>"
            f"<td>{r['baseline_ts']}</td>"
            f"<td>{r['baseline_val']:.4g}</td>"
            f"<td>{r['contender_val']:.4g}</td>"
            f"<td>{r['delta_pct']:+.2f}%</td>"
            f"<td>{r['status']}</td>"
            "</tr>\n"
        )
 
    html = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset='utf-8'>
        <style>
            body{{font-family:sans-serif;font-size:13px}}
            table{{border-collapse:collapse;width:100%}}
            th,td{{border:1px solid #ccc;padding:6px 10px;text-align:left}}
            th{{background:#2d3e50;color:#fff}}
            tr:hover{{filter:brightness(0.95)}}
        </style>
    </head>
    <body>
        <h2>Metric comparison table</h2>
        <p>Contender run: <strong>{get_contender_id(df)[:8]}</strong> &nbsp;|&nbsp;
        Baselines: {len(get_unique_baselines(df))}</p>
        <table>
            <thead>
                <tr>
                    <th>Metric</th>
                    <th>Baseline ID</th>
                    <th>Baseline timestamp</th>
                    <th>Baseline value</th>
                    <th>Contender value</th>
                    <th>Delta %</th>
                    <th>Status</th>
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
    print(f"Table saved => {report_path}")
 
 
def visualize_chart(df: pd.DataFrame, report_path: Path) -> None:
    metrics         = df[ComparisonCols.METRIC].unique()
    contender_id    = get_contender_id(df)
    baseline_ids    = get_unique_baselines(df)
    n_metrics       = len(metrics)
 
    fig, axes = plt.subplots(
        n_metrics, 1,
        figsize=(max(10, 2 * len(baseline_ids) + 4), 4 * n_metrics),
        squeeze=False,
    )
    fig.suptitle("Metric values — baselines vs contender", fontsize = 14, fontweight = "bold")
 
    for ax, metric in zip(axes[:, 0], metrics):
        mdf = df[df[ComparisonCols.METRIC] == metric]
 
        labels, values, colors = [], [], []
        for bid in baseline_ids:
            row = mdf[mdf[ComparisonCols.BASELINE_RUN_ID] == bid]
            if row.empty:
                continue
            labels.append(f"baseline\n{bid[:8]}")
            values.append(row.iloc[0][ComparisonCols.BASELINE_VAL])
            colors.append(BASELINE_COLOR)
 
        first = mdf.iloc[0]
        labels.append(f"CONTENDER\n{contender_id[:8]}")
        values.append(first[ComparisonCols.CONTENDER_VAL])
        colors.append(CONTENDER_COLOR)
 
        x    = np.arange(len(labels))
        bars = ax.bar(x, values, color = colors, edgecolor = "white", linewidth = 0.6)
        ax.set_xticks(x)
        ax.set_xticklabels(labels, fontsize = 9)
        ax.set_title(metric, fontsize = 11, fontweight = "bold")
        ax.set_ylabel("value")
        ax.yaxis.grid(True, linestyle = "--", alpha = 0.5)
        ax.set_axisbelow(True)
 
        # Value labels on bars
        for bar, val in zip(bars, values):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() * 1.01,
                f"{val:.3g}",
                ha       = "center", 
                va       = "bottom", 
                fontsize = 8,
            )
 
    add_legend(fig)
    fig.tight_layout(rect = (0, 0, 1, 0.97))
    save_as_html(fig, report_path)
    print(f"Chart saved => {report_path}")
 
 
def visualize_graph(df: pd.DataFrame, report_path: Path) -> None:
    metrics      = df[ComparisonCols.METRIC].unique()
    n_metrics    = len(metrics)
    contender_id = get_contender_id(df)
 
    fig, axes = plt.subplots(
        n_metrics, 1,
        figsize = (max(10, 3 * n_runs(df)), 4 * n_metrics),
        squeeze = False,
    )
    fig.suptitle(
        "Time-series: baseline history => contender",
        fontsize = 14, fontweight = "bold",
    )
 
    for ax, metric in zip(axes[:, 0], metrics):
        mdf = df[df[ComparisonCols.METRIC] == metric].copy()
 
        timeline = build_ordered_timeline(mdf, contender_id)
        if not timeline:
            ax.set_visible(False)
            continue
 
        xs         = list(range(len(timeline)))
        ys         = [t["value"]        for t in timeline]
        is_ctdr    = [t["is_contender"] for t in timeline]
        run_ids    = [t["run_id"]       for t in timeline]
        timestamps = [t["ts_str"]       for t in timeline]
 
        ax.plot(xs, ys, color = "#888", linewidth = 1.2, zorder = 2)
 
        for x, y, contender, rid, ts in zip(xs, ys, is_ctdr, run_ids, timestamps):
            if contender:
                ax.scatter(
                    x, y,
                    s          = 220, 
                    marker     = CONTENDER_MARKER,
                    color      = CONTENDER_COLOR, 
                    edgecolors = "white", 
                    linewidths = 0.8,
                    zorder     = CONTENDER_ZORDER,
                )
                ax.annotate(
                    f"CONTENDER\n{rid[:8]}\n{y:.3g}",
                    xy         = (x, y), 
                    xytext     = (6, 8), 
                    textcoords = "offset points",
                    fontsize   = 7.5, 
                    color      = CONTENDER_COLOR, 
                    fontweight = "bold",
                )

            else:
                ax.scatter(
                    x, y,
                    s          = 70, 
                    marker     = BASELINE_MARKER,
                    color      = BASELINE_COLOR, 
                    edgecolors = "white", 
                    linewidths = 0.6,
                    zorder     = BASELINE_ZORDER,
                )
                ax.annotate(
                    f"{rid[:8]}\n{y:.3g}",
                    xy         = (x, y), 
                    xytext     = (4, 6), 
                    textcoords = "offset points",
                    fontsize   = 7, 
                    color      = "#3a3a3a",
                )

        ctdr_idx = next(i for i, t in enumerate(timeline) if t["is_contender"])
        ax.axvspan(ctdr_idx - 0.4, ctdr_idx + 0.4, color = CONTENDER_COLOR, alpha = 0.07, zorder = 1)
        ax.axvline(ctdr_idx - 0.5, color = "#ccc", linewidth = 0.8, linestyle = "--", zorder = 1)
 
        ax.set_xticks(xs)
        ax.set_xticklabels(timestamps, fontsize = 8, rotation = 20, ha = "right")
        ax.set_title(metric, fontsize = 11, fontweight = "bold")
        ax.set_ylabel("value")
        ax.yaxis.grid(True, linestyle = "--", alpha = 0.4)
        ax.set_axisbelow(True)
        ax.set_xlim(-0.6, len(xs) - 0.4)
 
    add_legend(fig)
    fig.tight_layout(rect = (0, 0, 1, 0.97))
    save_as_html(fig, report_path)
    print(f"Graph saved => {report_path}")

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
    contender_id = get_contender_id(df)
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
    </body></html>
    """

    path.write_text(html, encoding = "utf-8")

def generate_report_path(relative_path, format: VisualFormatOptions, ext: str) -> Path:
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    return REPORT_DIR / f"{relative_path}_{format}_{timestamp}.{ext}"