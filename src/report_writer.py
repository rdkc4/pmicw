from pathlib import Path
import numpy as np
import pandas as pd

REPORT_DIR = Path.cwd() / "reports"

def write_report(df: pd.DataFrame, report_formats: list[str], report_path: str) -> None:
    report_data = {"comparisons": []}
    grouped     = df.groupby(["baseline_run", "contender_run"], sort = False)

    for (baseline, contender), group in grouped:
        run_payload = {
            "baseline_run_id":  baseline,
            "contender_run_id": contender,
            "timestamp":        str(group["timestamp"].iloc[0]) if "timestamp" in group.columns else None,
            "segments":         {}
        }
        
        for segment, segment_df in group.groupby("segment", observed = True):
            segment_df = segment_df.replace([np.nan, np.inf, -np.inf], None)
            run_payload["segments"][str(segment)] = segment_df.to_dict(orient = "records")
            
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
            lines.append(f"### Baseline Run ID:  {comparison['baseline_run_id']}")
            lines.append(f"### Contender Run ID: {comparison['contender_run_id']}")
            lines.append(f"### Timestamp:        {comparison['timestamp']}")

            for segment, records in comparison["segments"].items():
                lines.append(f"#### {segment}")
                
                segment_df     = pd.DataFrame(records)
                display_cols   = ["metric", "baseline_val", "contender_val", "delta_abs", "delta_pct", "unit"]
                available_cols = [col for col in display_cols if col in segment_df.columns]

                lines.append(segment_df[available_cols].to_markdown(index = False))
                lines.append("")
        
    output_path.write_text(
        "\n".join(lines),
        encoding="utf-8"
    )

def generate_report_path(relative_path, format: str) -> Path:
    return REPORT_DIR / f"{relative_path}.{format}"