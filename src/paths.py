from pathlib import Path

DIR     = Path(__file__).resolve().parents[1]
WEB     = "web"
DATA    = "data"
REPORTS = "reports"

WEB_DIR    = DIR     / WEB
DATA_DIR   = WEB_DIR / DATA
REPORT_DIR = WEB_DIR / REPORTS
INDEX_HTML = WEB_DIR / "index.html"