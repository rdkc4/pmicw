from pathlib import Path
import numpy as np
import pandas as pd

from comparison_context import MetricStatus

REPORT_DIR = Path.cwd() / "reports"

MD_REPORT_ROW_COLORS = {
    MetricStatus.REGRESSION:  "background-color: rgba(255, 77, 77, 0.15); border-left: 5px solid #ff4d4d;",
    MetricStatus.IMPROVEMENT: "background-color: rgba(77, 175, 74, 0.15); border-left: 5px solid #4daf4a;",
    MetricStatus.NOISE:       "color: #888888; font-style: italic;",
    MetricStatus.INTERESTING: "background-color: rgba(255, 165, 0, 0.12); border-left: 5px solid #d97706;",
    MetricStatus.INVALID:     "background-color: rgba(200, 200, 200, 0.1); color: #9ca3af; text-decoration: line-through;",
    MetricStatus.IRRELEVANT:  "background-color: transparent; color: #555555;"
}

def write_report(df: pd.DataFrame, report_formats: list[str], report_path: str) -> None:
    report_data = {"comparisons": []}
    grouped     = df.groupby(["baseline_run", "contender_run"], sort = False)

    for (baseline, contender), group in grouped:
        clean_group = group.replace([np.nan, np.inf, -np.inf], None)
        first_row   = clean_group.iloc[0] if not clean_group.empty else {}

        run_payload = {
            "baseline_run_id":  baseline,
            "baseline_args":    first_row.get("baseline_args", "N/A"),
            "contender_run_id": contender,
            "contender_args":   first_row.get("contender_args", "N/A"),
            "workload_name":    first_row.get("workload_name", "N/A"),
            "timestamp":        str(group["timestamp"].iloc[0]) if "timestamp" in group.columns else None,
            "metrics":          clean_group.to_dict(orient = "records")
        }   
        report_data["comparisons"].append(run_payload)

    REPORT_DIR.mkdir(parents = True, exist_ok = True)

    if "csv" in report_formats:
        write_csv_report(df, generate_report_path(report_path, "csv"))

    if "json" in report_formats:
        write_json_report(report_data, generate_report_path(report_path, "json"))

    if "md" in report_formats:
        write_md_report(report_data, generate_report_path(report_path, "md"))

def write_csv_report(df: pd.DataFrame, output_path: Path) -> None:
    df.to_csv(output_path, index = False)

def write_json_report(report_data: dict, output_path: Path) -> None:
    import json
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent = 2, default = str)

def write_md_report(report_data: dict, output_path: Path) -> None:
    lines = []
    for comparison in report_data["comparisons"]:
        lines.append("## Report:")
        lines.append(f"### Workload:         {comparison['workload_name']}")
        lines.append(f"### Timestamp:        {comparison['timestamp']}")
        lines.append(f"### Baseline Run ID:  {comparison['baseline_run_id']} (Args: {comparison['baseline_args']})")
        lines.append(f"### Contender Run ID: {comparison['contender_run_id']} (Args: {comparison['contender_args']})")
        lines.append("")

        metrics_df = pd.DataFrame(comparison["metrics"])
        
        if not metrics_df.empty:
            display_cols   = ["metric", "baseline_val", "contender_val", "delta_abs", "delta_pct", "unit", "status"]
            available_cols = [col for col in display_cols if col in metrics_df.columns]
            
            html = ["<table style='width:100%; border-collapse: collapse; font-family: monospace;'>"]
            
            html.append("  <thead><tr style='border-bottom: 2px solid #888; background-color: #f3f4f6;'>")
            for col in available_cols:
                html.append(f"    <th style='text-align: left; padding: 6px 12px; font-weight: bold;'>{col}</th>")

            html.append("  </tr></thead>")
            
            html.append("  <tbody>")
            for _, row in metrics_df.iterrows():
                status = row.get("status", MetricStatus.IRRELEVANT).lower()
                row_style = MD_REPORT_ROW_COLORS.get(status, "")
                
                html.append(f"    <tr style='border-bottom: 1px solid #e5e7eb; {row_style}'>")
                for col in available_cols:
                    val = row[col] if pd.notna(row[col]) else ""
                    
                    if col == "status" and status in ["regression", "improvement"]:
                        html.append(f"      <td style='padding: 6px 12px; font-weight: bold; text-transform: uppercase;'>{val}</td>")

                    elif isinstance(val, float):
                        html.append(f"      <td style='padding: 6px 12px;'>{val:.6g}</td>")

                    else:
                        html.append(f"      <td style='padding: 6px 12px;'>{val}</td>")

                html.append("    </tr>")
                
            html.append("  </tbody>")
            html.append("</table>")
            
            lines.append("\n".join(html))
            lines.append("")
        
    output_path.write_text("\n".join(lines), encoding="utf-8")

def generate_report_path(relative_path, format: str) -> Path:
    return REPORT_DIR / f"{relative_path}.{format}"