import datetime
from pathlib import Path
import numpy as np
import pandas as pd

from cli_parser import ReportFormatOptions
from comparison_context import ComparisonCols, MetricStatus

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
    report_data = {ComparisonCols.COMPARISON: []}
    grouped     = df.groupby(["baseline_run_id", "contender_run_id"], sort = False)

    for (baseline, contender), group in grouped:
        clean_group = group.replace([np.nan, np.inf, -np.inf], None)
        first_row   = clean_group.iloc[0] if not clean_group.empty else {}

        run_payload = {
            ComparisonCols.BASELINE_RUN_ID:  baseline,
            ComparisonCols.BASELINE_ARGS:    first_row.get(ComparisonCols.BASELINE_ARGS, "N/A"),
            ComparisonCols.CONTENDER_RUN_ID: contender,
            ComparisonCols.CONTENDER_ARGS:   first_row.get(ComparisonCols.CONTENDER_ARGS, "N/A"),
            ComparisonCols.WORKLOAD_NAME:    first_row.get(ComparisonCols.WORKLOAD_NAME, "N/A"),
            ComparisonCols.TIMESTAMP:        str(group[ComparisonCols.TIMESTAMP].iloc[0]) if ComparisonCols.TIMESTAMP in group.columns else None,
            ComparisonCols.METRIC:           clean_group.to_dict(orient = "records")
        }   
        report_data[ComparisonCols.COMPARISON].append(run_payload)

    REPORT_DIR.mkdir(parents = True, exist_ok = True)

    if ReportFormatOptions.CSV in report_formats:
        write_csv_report(df, generate_report_path(report_path, ReportFormatOptions.CSV))

    if ReportFormatOptions.JSON in report_formats:
        write_json_report(report_data, generate_report_path(report_path, ReportFormatOptions.JSON))

    if ReportFormatOptions.MD in report_formats:
        write_md_report(report_data, generate_report_path(report_path, ReportFormatOptions.MD))

def write_csv_report(df: pd.DataFrame, output_path: Path) -> None:
    df.to_csv(output_path, index = False)

def write_json_report(report_data: dict, output_path: Path) -> None:
    import json
    with open(output_path, "w", encoding = "utf-8") as f:
        json.dump(report_data, f, indent = 2, default = str)

def write_md_report(report_data: dict, output_path: Path) -> None:
    lines = []
    for comparison in report_data[ComparisonCols.COMPARISON]:
        lines.append("## Report:")
        lines.append(f"### Workload:         {comparison[ComparisonCols.WORKLOAD_NAME]}")
        lines.append(f"### Timestamp:        {comparison[ComparisonCols.TIMESTAMP]}")
        lines.append(f"### Baseline Run ID:  {comparison[ComparisonCols.BASELINE_RUN_ID]}")
        lines.append(f"#### Baseline Args:   {comparison[ComparisonCols.BASELINE_ARGS]}")
        lines.append(f"### Contender Run ID: {comparison[ComparisonCols.CONTENDER_RUN_ID]}")
        lines.append(f"#### Contender Args:  {comparison[ComparisonCols.CONTENDER_ARGS]}")
        lines.append("")

        metrics_df = pd.DataFrame(comparison[ComparisonCols.METRIC])
        
        if not metrics_df.empty:
            display_cols   = [
                ComparisonCols.METRIC, 
                ComparisonCols.BASELINE_VAL, 
                ComparisonCols.CONTENDER_VAL, 
                ComparisonCols.DELTA_ABS, 
                ComparisonCols.DELTA_PCT, 
                ComparisonCols.UNIT, 
                ComparisonCols.STATUS
            ]
            available_cols = [col for col in display_cols if col in metrics_df.columns]
            
            html = ["<table style='width:100%; border-collapse: collapse; font-family: monospace;'>"]
            
            html.append("  <thead><tr style='border-bottom: 2px solid #888; background-color: #f3f4f6;'>")
            for col in available_cols:
                html.append(f"    <th style='text-align: left; padding: 6px 12px; font-weight: bold;'>{col}</th>")

            html.append("  </tr></thead>")
            
            html.append("  <tbody>")
            for _, row in metrics_df.iterrows():
                status = row.get(ComparisonCols.STATUS, MetricStatus.IRRELEVANT).lower()
                row_style = MD_REPORT_ROW_COLORS.get(status, "")
                
                html.append(f"    <tr style='border-bottom: 1px solid #e5e7eb; {row_style}'>")
                for col in available_cols:
                    val = row[col] if pd.notna(row[col]) else ""
                    
                    if col == ComparisonCols.STATUS and status in [MetricStatus.REGRESSION, MetricStatus.IMPROVEMENT]:
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
        
    output_path.write_text("\n".join(lines), encoding = "utf-8")

def generate_report_path(relative_path, format: str) -> Path:
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    return REPORT_DIR / f"{relative_path}_{timestamp}.{format}"