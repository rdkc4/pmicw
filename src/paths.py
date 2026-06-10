from pathlib import Path

DIR     = Path(__file__).resolve().parents[1]
WEB     = "web"
DATA    = "data"
REPORTS = "reports"
VISUAL  = "visual"

DATA_DIR   = DIR / WEB / DATA
REPORT_DIR = DIR / WEB / REPORTS
VISUAL_DIR = DIR / WEB / VISUAL
INDEX_HTML = VISUAL_DIR / "index.html"