import pandas as pd

def write_report(df: pd.DataFrame, report_formats: list[str]) -> None:
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
            run_payload["segments"][str(segment)] = segment_df.to_dict(orient = "records")
            
        report_data["comparisons"].append(run_payload)

    if "csv" in report_formats:
        write_csv_report(df)

    if "json" in report_formats:
        write_json_report(report_data)

    if "md" in report_formats:
        write_md_report(report_data)

def write_csv_report(df: pd.DataFrame) -> None:
    print(df.to_csv(index = False))

def write_json_report(report_data: dict) -> None:
    import json
    print(json.dumps(report_data, indent = 2, default = str))

def write_md_report(report_data: dict) -> None:
    for comparison in report_data["comparisons"]:
            print(f"## Baseline Run ID:  {comparison['baseline_run_id']} \n")
            print(f"## Contender Run ID: {comparison['contender_run_id']} \n")
            print(f"## Timestamp:        {comparison['timestamp']} \n")

            for segment, records in comparison["segments"].items():
                print(f"### {segment}\n")
                
                segment_df     = pd.DataFrame(records)
                display_cols   = ["metric", "baseline_val", "contender_val", "delta_abs", "delta_pct", "unit"]
                available_cols = [col for col in display_cols if col in segment_df.columns]

                print(segment_df[available_cols].to_markdown(index = False))
                print("\n")
