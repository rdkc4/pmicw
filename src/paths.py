from pathlib import Path

DIR        = Path(__file__).resolve().parents[1]
WEB        = "web"
DATA       = "data"
REPORTS    = "reports"
WORKLOADS  = "workloads"
CONFIG     = "config"
THRESHOLDS = "thresholds"

WEB_DIR              = DIR        / WEB
DATA_DIR             = WEB_DIR    / DATA
REPORT_DIR           = WEB_DIR    / REPORTS
WORKLOADS_DIR        = WEB_DIR    / WORKLOADS
INDEX_HTML           = WEB_DIR    / "index.html"

CONFIG_DIR           = DIR        / CONFIG
THRESHOLDS_DIR       = CONFIG_DIR / THRESHOLDS

METRIC_CONFIG        = CONFIG_DIR / "metric_config.yaml"
COMMAND_CONFIG       = CONFIG_DIR / "command_config.yaml"
CMP_THRESHOLD_CONFIG = CONFIG_DIR / "comparison_threshold_config.yaml"
PLOT_CONFIG          = CONFIG_DIR / "plot_config.yaml"
