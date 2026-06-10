from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
import plotly.graph_objects as go

import pandas as pd

DARK_BG        = "#0f172a"
PANEL_BG       = "#1e293b"
BORDER_COLOR   = "#334155"
TEXT_MAIN      = "#f8fafc"
TEXT_MUTED     = "#94a3b8"
CONTENDER_ZONE = "#38bdf8"

class MetricStatus(StrEnum):
    NOISE       = "noise"
    IMPROVEMENT = "improvement"
    REGRESSION  = "regression"
    INTERESTING = "interesting"
    IRRELEVANT  = "irrelevant"
    INVALID     = "invalid"

class CSVMetadataCols(StrEnum):
    RUN_ID        = "run_id"
    TIMESTAMP     = "timestamp"
    WORKLOAD_NAME = "workload_name"
    WORKLOAD_ARGS = "workload_arguments"

class ComparisonCols(StrEnum):
    # metadata
    BASELINE_RUN_ID  = "baseline_run_id"
    CONTENDER_RUN_ID = "contender_run_id"
    BASELINE_ARGS    = "baseline_args"
    CONTENDER_ARGS   = "contender_args"
    WORKLOAD_NAME    = "workload_name"
    TIMESTAMP        = "timestamp"
    CFG              = "comparison_cfg"

    # data
    COMPARISON       = "comparison"
    METRIC           = "metric"
    BASELINE_VAL     = "baseline_val"
    CONTENDER_VAL    = "contender_val"
    DELTA_ABS        = "delta_abs"
    DELTA_PCT        = "delta_pct"
    UNIT             = "unit"
    STATUS           = "status"

@dataclass
class ComparisonDataFrames:
    cmp_df:  pd.DataFrame | None = None
    cmp2_df: pd.DataFrame | None = None
    cmpw_df: pd.DataFrame | None = None

@dataclass
class ComparisonReports:
    csv:  str | None = None
    md:   str | None = None
    json: str | None = None

@dataclass
class ComparisonReportGroups:
    cmp:  ComparisonReports = field(default_factory = ComparisonReports)
    cmp2: ComparisonReports = field(default_factory = ComparisonReports)
    cmpw: ComparisonReports = field(default_factory = ComparisonReports)

@dataclass
class ComparisonVisuals:
    table: str       | None = None
    chart: go.Figure | None = None
    graph: go.Figure | None = None

@dataclass
class ComparisonVisualGroups:
    cmp:  dict[str, ComparisonVisuals] = field(default_factory = dict)
    cmp2: dict[str, ComparisonVisuals] = field(default_factory = dict)
    cmpw: dict[str, ComparisonVisuals] = field(default_factory = dict)