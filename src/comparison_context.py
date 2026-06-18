from dataclasses import dataclass, field
from enum import StrEnum
import plotly.graph_objects as go
import pandas as pd

DARK_BG        = "#0f172a"
PANEL_BG       = "#1e293b"
BORDER_COLOR   = "#334155"
TEXT_MAIN      = "#f8fafc"
TEXT_MUTED     = "#94a3b8"
CONTENDER_ZONE = "#38bdf8"

class MetricStatus(StrEnum):
    """
    Status Entries for the metric after delta computation
    """
    NOISE       = "noise"        # defined in configuration
    IMPROVEMENT = "improvement"  # defined in configuration
    REGRESSION  = "regression"   # defined in configuration
    INTERESTING = "interesting"  # values between noise and improvement/regression
    IRRELEVANT  = "irrelevant"   # metrics that are not defined in configuration
    INVALID     = "invalid"      # deltas resulting in nan / inf / -inf values

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
    """
    Result dataframes from comparison
    """
    cmp_df:  pd.DataFrame | None = None # result of compare <n>,         None if `-cmp` is not defined 
    cmp2_df: pd.DataFrame | None = None # result of compare-two <a> <b>, None if `-cmp2` is not defined
    cmpw_df: pd.DataFrame | None = None # result of compare-with <id>,    None if `-cmpw` is not defined

@dataclass
class ComparisonReports:
    """
    Paths to reports
    """
    csv:  str | None = None # None if -rfmt doesn't include csv
    md:   str | None = None # None if -rfmt doesn't include md
    json: str | None = None # None if -rfmt doesn't include json

@dataclass
class ComparisonReportGroups:
    """
    Reports grouped by comparison type they're related to
    """
    cmp:  ComparisonReports = field(default_factory = ComparisonReports)
    cmp2: ComparisonReports = field(default_factory = ComparisonReports)
    cmpw: ComparisonReports = field(default_factory = ComparisonReports)

@dataclass
class ComparisonVisuals:
    """
    Graphs generated based on the comparison results
    """
    table: str       | None = None # None if -vfmt doesn't include table
    chart: go.Figure | None = None # None if -vfmt doesn't include chart
    graph: go.Figure | None = None # None if -vfmt doesn't include graph

@dataclass
class ComparisonVisualGroups:
    """
    Visualizations grouped by comparison type they're related to
    """
    cmp:  dict[str, ComparisonVisuals] = field(default_factory = dict)
    cmp2: dict[str, ComparisonVisuals] = field(default_factory = dict)
    cmpw: dict[str, ComparisonVisuals] = field(default_factory = dict)