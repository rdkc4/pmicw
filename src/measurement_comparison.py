from __future__ import annotations

import numpy as np
import pandas as pd

pd.set_option("display.max_columns", None)
pd.set_option("display.max_rows", None)
pd.set_option("display.width", 10000)
pd.set_option("display.expand_frame_repr", False)

def compute_deltas(df: pd.DataFrame, baseline_run_id: str) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()

    baseline_rows = df.loc[df["run_id"] == baseline_run_id]
    if baseline_rows.empty:
        raise ValueError(
            f"Baseline run_id '{baseline_run_id}' not found."
        )
    baseline_row = baseline_rows.iloc[0]

    contenders = (
        df.loc[df["run_id"] != baseline_run_id]
        .sort_values("timestamp")
        .reset_index(drop = True)
    )

    if contenders.empty:
        return pd.DataFrame()
    
    numeric_cols     = contenders.select_dtypes(include = "number").columns
    csv_metric_order = list(numeric_cols)
    baseline_vals    = pd.DataFrame(
        [baseline_row[numeric_cols].values] * len(contenders),
        columns = numeric_cols,
        index   = contenders.index
    )

    contender_vals = contenders[numeric_cols]

    delta_abs = contender_vals - baseline_vals
    with np.errstate(divide = "ignore", invalid = "ignore"):
        delta_pct = (delta_abs / baseline_vals) * 100

    report_meta = pd.DataFrame({
        "workload_name":  contenders["workload_name"],
        "baseline_run":   baseline_run_id,
        "baseline_args":  baseline_row.get("workload_arguments", "N/A"),
        "contender_run":  contenders["run_id"],
        "contender_args": contenders.get("workload_arguments", "N/A"),
        "timestamp":      contenders["timestamp"]
    })

    melt_abs  = delta_abs.melt(ignore_index      = False, var_name = "metric", value_name = "delta_abs")
    melt_pct  = delta_pct.melt(ignore_index      = False, var_name = "metric", value_name = "delta_pct")
    melt_base = baseline_vals.melt(ignore_index  = False, var_name = "metric", value_name = "baseline_val")
    melt_curr = contender_vals.melt(ignore_index = False, var_name = "metric", value_name = "contender_val")

    result = pd.concat([
        report_meta.loc[melt_abs.index],
        melt_abs,
        melt_pct["delta_pct"],
        melt_base["baseline_val"],
        melt_curr["contender_val"]
    ], axis = 1).reset_index(drop = True)

    result["metric"] = pd.Categorical(
        result["metric"], 
        categories = csv_metric_order, 
        ordered    = True
    )

    return result.sort_values(by = [
        "timestamp",
        "metric"
    ]).reset_index(drop = True)
