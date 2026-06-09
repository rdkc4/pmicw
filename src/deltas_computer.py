from __future__ import annotations

import numpy as np
import pandas as pd

from comparison_config import Direction, ThresholdConfig
from comparison_context import (
    CSVMetadataCols, 
    ComparisonCols,  
    MetricStatus
)

def classify_metric(
    baseline_val:   float,
    contender_val:  float,
    delta_abs:      float,
    delta_pct:      float,
    comparison_cfg: ThresholdConfig
) -> MetricStatus:

    if any(pd.isna([baseline_val, contender_val, delta_abs, delta_pct])) or np.isinf(delta_abs) or np.isinf(delta_pct):
        return MetricStatus.INVALID
    
    if comparison_cfg.direction == Direction.NEUTRAL:
        return MetricStatus.IRRELEVANT

    if abs(delta_pct) <= comparison_cfg.noise_floor_pct:
        return MetricStatus.NOISE
    
    if comparison_cfg.improvement_threshold_pct == 0 and comparison_cfg.regression_threshold_pct == 0:
        return MetricStatus.IRRELEVANT

    if comparison_cfg.direction == Direction.HIGHER_BETTER:
        if delta_pct >=  comparison_cfg.improvement_threshold_pct: return MetricStatus.IMPROVEMENT
        if delta_pct <= -comparison_cfg.regression_threshold_pct:  return MetricStatus.REGRESSION

    if comparison_cfg.direction == Direction.LOWER_BETTER:
        if delta_pct <= -comparison_cfg.improvement_threshold_pct: return MetricStatus.IMPROVEMENT
        if delta_pct >=  comparison_cfg.regression_threshold_pct:  return MetricStatus.REGRESSION

    return MetricStatus.INTERESTING

def compute_deltas(df: pd.DataFrame, contender_id: str, comparison_map: dict[str, ThresholdConfig]) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()

    contender_rows = df.loc[df[CSVMetadataCols.RUN_ID] == contender_id]
    if contender_rows.empty:
        raise ValueError(
            f"Contender run_id '{contender_id}' not found."
        )
    contender_row = contender_rows.iloc[0]

    baselines = (
        df.loc[df[CSVMetadataCols.RUN_ID] != contender_id]
        .sort_values(CSVMetadataCols.TIMESTAMP)
        .reset_index(drop = True)
    )

    if baselines.empty:
        return pd.DataFrame()

    numeric_cols     = baselines.select_dtypes(include = "number").columns
    csv_metric_order = list(numeric_cols)
    contender_vals   = pd.DataFrame(
        [contender_row[numeric_cols].values] * len(baselines),
        columns = numeric_cols,
        index   = baselines.index
    )

    baseline_vals = baselines[numeric_cols]
    delta_abs     = contender_vals - baseline_vals

    with np.errstate(divide = "ignore", invalid = "ignore"):
        delta_pct = (delta_abs / baseline_vals) * 100

    report_meta = pd.DataFrame({
        ComparisonCols.WORKLOAD_NAME:    baselines[CSVMetadataCols.WORKLOAD_NAME],
        ComparisonCols.BASELINE_RUN_ID:  baselines[CSVMetadataCols.RUN_ID],
        ComparisonCols.BASELINE_ARGS:    baselines.get(CSVMetadataCols.WORKLOAD_ARGS, "N/A"),
        ComparisonCols.CONTENDER_RUN_ID: contender_id,
        ComparisonCols.CONTENDER_ARGS:   contender_row.get(CSVMetadataCols.WORKLOAD_ARGS, "N/A"),
        ComparisonCols.TIMESTAMP:        baselines[CSVMetadataCols.TIMESTAMP]
    })

    melt_abs  = delta_abs.melt(ignore_index      = False, var_name = ComparisonCols.METRIC, value_name = ComparisonCols.DELTA_ABS)
    melt_pct  = delta_pct.melt(ignore_index      = False, var_name = ComparisonCols.METRIC, value_name = ComparisonCols.DELTA_PCT)
    melt_base = baseline_vals.melt(ignore_index  = False, var_name = ComparisonCols.METRIC, value_name = ComparisonCols.BASELINE_VAL)
    melt_curr = contender_vals.melt(ignore_index = False, var_name = ComparisonCols.METRIC, value_name = ComparisonCols.CONTENDER_VAL)

    result = pd.concat([
        report_meta.loc[melt_abs.index],
        melt_abs,
        melt_pct[ComparisonCols.DELTA_PCT],
        melt_base[ComparisonCols.BASELINE_VAL],
        melt_curr[ComparisonCols.CONTENDER_VAL]
    ], axis = 1).reset_index(drop = True)

    result[ComparisonCols.CFG] = result[ComparisonCols.METRIC].map(comparison_map)
    result[ComparisonCols.STATUS] = result.apply(
        lambda row: classify_metric(
            baseline_val   = row[ComparisonCols.BASELINE_VAL],
            contender_val  = row[ComparisonCols.CONTENDER_VAL],
            delta_abs      = row[ComparisonCols.DELTA_ABS],
            delta_pct      = row[ComparisonCols.DELTA_PCT],
            comparison_cfg = row[ComparisonCols.CFG] if isinstance(row[ComparisonCols.CFG], ThresholdConfig) else ThresholdConfig()
        ),
        axis = 1
    )

    result = result.drop(columns = [ComparisonCols.CFG])
    result[ComparisonCols.METRIC] = pd.Categorical(
        result[ComparisonCols.METRIC], 
        categories = csv_metric_order, 
        ordered    = True
    )

    return result.sort_values(by = [
        ComparisonCols.TIMESTAMP,
        ComparisonCols.METRIC
    ]).reset_index(drop = True)