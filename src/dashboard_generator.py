from html import escape
from pathlib import Path
import re
import plotly.graph_objects as go

from comparison_context import (
    BORDER_COLOR, 
    CONTENDER_ZONE, 
    DARK_BG,
    PANEL_BG,
    TEXT_MAIN, 
    TEXT_MUTED,
    ComparisonReportGroups, 
    ComparisonVisualGroups
)
from paths import INDEX_HTML, WORKLOADS_DIR

ICON_MAP = {
    "csv": (
        '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18M9 21V9"/></svg>', 
        "#4ade80"
    ),
    "json": (
        '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg>', 
        "#60a5fa"
    ),
    "md": (
        '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>'
        '<polyline points="14 2 14 8 20 8"/></svg>', 
        "#f472b6"
    ),
}

COMMON_STYLES = f"""
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background-color: {DARK_BG}; color: {TEXT_MAIN}; margin: 0; padding: 20px; }}
    .header {{ margin-bottom: 25px; border-bottom: 1px solid {BORDER_COLOR}; padding-bottom: 15px; display: flex; justify-content: space-between; align-items: flex-end; }}
    .header-titles {{ flex-grow: 1; }}
    .header h1 {{ margin: 0 0 5px 0; font-size: 24px; letter-spacing: -0.5px; }}
    .header p {{ margin: 0; color: {TEXT_MUTED}; font-size: 14px; }}
    .back-btn {{ display: inline-flex; align-items: center; gap: 6px; color: {TEXT_MUTED}; text-decoration: none; font-size: 13px; font-weight: 600; padding: 8px 16px; border: 1px solid {BORDER_COLOR}; border-radius: 4px; background: {PANEL_BG}; transition: all 0.2s; }}
    .back-btn:hover {{ color: {TEXT_MAIN}; border-color: {CONTENDER_ZONE}; }}
"""

def generate_dashboard(
    report_groups: ComparisonReportGroups,
    visual_groups: ComparisonVisualGroups,
    workload_name: str
) -> None:
    WORKLOADS_DIR.mkdir(parents = True, exist_ok = True)
    
    safe_workload = safe_id(workload_name)
    workload_filename = f"{safe_workload}.html"
    workload_path = WORKLOADS_DIR / workload_filename

    cmp_sections = [
        ("cmp",  report_groups.cmp,  visual_groups.cmp),
        ("cmp2", report_groups.cmp2, visual_groups.cmp2),
        ("cmpw", report_groups.cmpw, visual_groups.cmpw)
    ]
    
    outer_tab_buttons  = ""
    outer_tab_contents = ""
    
    for outer_idx, (section_key, reports, visuals_by_group) in enumerate(cmp_sections):
        if not visuals_by_group:
            continue
            
        active_outer  = "active" if outer_idx == 0 else ""
        display_outer = "block"  if outer_idx == 0 else "none"
        outer_id      = f"outer-{section_key}"
        
        outer_tab_buttons += (
            f'<button class="tab-btn {active_outer}" '
            f'data-target="{outer_id}" data-level="outer">'
            f'{escape(section_key).upper()}</button>\n'
        )
        
        inner_tab_buttons  = ""
        inner_tab_contents = ""
        
        for inner_idx, (group_name, visuals) in enumerate(visuals_by_group.items()):
            active_inner  = "active" if inner_idx == 0 else ""
            display_inner = "block"  if inner_idx == 0 else "none"
            inner_id      = f"{section_key}-{safe_id(group_name)}"
            
            inner_tab_buttons += (
                f'<button class="tab-btn tab-btn {active_inner}" '
                f'data-target="{inner_id}" data-level="inner">'
                f'{escape(str(group_name)).upper()}</button>\n'
            )
            
            download_bar = build_download_bar(reports, is_nested=True)
            panel_html   = create_group_panel(visuals.table, visuals.chart, visuals.graph)
            
            inner_tab_contents += (
                f'<div id="{inner_id}" class="tab-content inner-tab-content" '
                f'style="display:{display_inner};">'
                f'{panel_html}{download_bar}</div>\n'
            )
            
        section_html = (
            f'<div class="inner-tab-bar">{inner_tab_buttons}</div>'
            f'{inner_tab_contents}'
        )
        
        outer_tab_contents += (
            f'<div id="{outer_id}" class="tab-content outer-tab-content" '
            f'style="display:{display_outer};">{section_html}</div>\n'
        )
        
    workload_payload = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Performance Profile - {escape(workload_name)}</title>
        <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
        <meta name="workload-display-name" content="{escape(workload_name)}">
        <style>
            {COMMON_STYLES}
            .tab-bar, .inner-tab-bar {{ display: flex; gap: 8px; border-bottom: 2px solid {BORDER_COLOR}; padding-bottom: 0; margin-bottom: 20px; }}
            .inner-tab-bar {{ margin-top: 8px; border-bottom-color: {BORDER_COLOR}; opacity: 0.85; }}
            .tab-btn {{ background: none; border: none; color: {TEXT_MUTED}; padding: 12px 20px; font-size: 14px; font-weight: 600; cursor: pointer; transition: all 0.2s ease; border-bottom: 3px solid transparent; margin-bottom: -2px; }}
            .tab-btn:hover {{ color: {TEXT_MAIN}; background-color: rgba(255,255,255,0.03); }}
            .tab-btn.active {{ color: {CONTENDER_ZONE}; border-bottom-color: {CONTENDER_ZONE}; }}
            .inner-tab-btn.active {{ color: #a78bfa; border-bottom-color: #a78bfa; }}
            .dashboard-grid {{ display: flex; flex-direction: column; gap: 24px; width: 100%; }}
            .grid-row-full {{ width: 100%; border-radius: 6px; overflow: hidden; background: {DARK_BG}; }}
            .style-card-gap {{ border: 1px solid {BORDER_COLOR}; padding: 10px; box-sizing: border-box; margin-bottom: 10px; }}
            .table-card-wrapper {{ background-color: {DARK_BG}; border-radius: 6px; padding: 10px 10px 0 10px; box-sizing: border-box; }}
            .table-title-area {{ padding-bottom: 15px; font-family: sans-serif; }}
            .table-main-title {{ font-size: 14px; font-weight: bold; color: {TEXT_MAIN}; margin-bottom: 4px; }}
            .table-sub-title {{ font-size: 12px; color: {TEXT_MUTED}; }}
            .table-scroll-container {{ max-height: 260px; overflow-y: auto; border: 1px solid {BORDER_COLOR}; border-radius: 4px; }}
            .sortable-dashboard-table {{ width: 100%; border-collapse: collapse; font-size: 12px; font-family: sans-serif; text-align: left; }}
            .sortable-dashboard-table th {{
                position: sticky; top: 0; background-color: #111827; color: {TEXT_MAIN};
                padding: 8px 10px; font-weight: 600; font-size: 13px; z-index: 10;
                border-bottom: 2px solid {BORDER_COLOR}; cursor: pointer; user-select: none;
            }}
            .sortable-dashboard-table th:hover {{ background-color: #1f2937; }}
            .sortable-dashboard-table td {{ padding: 6px 10px; border-bottom: 1px solid {BORDER_COLOR}; background-color: {PANEL_BG}; vertical-align: middle; }}
            .sort-icon {{ font-size: 10px; color: {TEXT_MUTED}; margin-left: 3px; }}
            .download-bar {{ display: flex; gap: 14px; padding: 14px 4px 4px 4px; align-items: center; }}
            .download-btn {{
                display: inline-flex; align-items: center; gap: 7px;
                padding: 7px 16px; border-radius: 6px; font-size: 12px; font-weight: 600;
                text-decoration: none; cursor: pointer; border: 1px solid {BORDER_COLOR};
                color: {TEXT_MUTED}; background: {PANEL_BG}; transition: all 0.18s ease;
            }}
            .download-btn:hover {{ color: {TEXT_MAIN}; border-color: {CONTENDER_ZONE}; background: #0f2131; }}
            .download-btn svg {{ flex-shrink: 0; }}
            .tab-content {{ animation: fadeIn 0.3s ease; }}
            @keyframes fadeIn {{ from {{ opacity: 0; }} to {{ opacity: 1; }} }}
        </style>
        <script>
            document.addEventListener("DOMContentLoaded", function() {{
                function activateTab(btn, level) {{
                    const tabId = btn.getAttribute("data-target");
                    const isOuter = level === "outer";
                    const siblingBtns = btn.closest(isOuter ? ".tab-bar" : ".inner-tab-bar").querySelectorAll(".tab-btn");
                    const contentClass = isOuter ? "outer-tab-content" : "inner-tab-content";
                    const scope = isOuter ? document : btn.closest(".outer-tab-content");
                    const contents = scope.querySelectorAll("." + contentClass);
                    
                    contents.forEach(function(c) {{ c.style.display = "none"; }});
                    siblingBtns.forEach(function(b) {{ b.classList.remove("active"); }});
                    
                    const target = document.getElementById(tabId);
                    if (target) {{
                        target.style.display = "block";
                        btn.classList.add("active");
                        target.querySelectorAll(".js-plotly-plot").forEach(function(p) {{ Plotly.Plots.resize(p); }});
                    }}
                }}

                document.querySelector(".tab-bar") && document.querySelector(".tab-bar").addEventListener("click", function(e) {{
                    const btn = e.target.closest(".tab-btn[data-level='outer']");
                    if (btn) activateTab(btn, "outer");
                }});
                
                document.body.addEventListener("click", function(e) {{
                    const btn = e.target.closest(".tab-btn[data-level='inner']");
                    if (btn) activateTab(btn, "inner");
                }});
                
                document.body.addEventListener("click", function(e) {{
                    const headerCell = e.target.closest(".sortable-dashboard-table th");
                    if (!headerCell) return;
                    
                    const colIndex = parseInt(headerCell.getAttribute("data-col"), 10);
                    const tbody = headerCell.closest("table").querySelector("tbody");
                    const rows = Array.from(tbody.querySelectorAll("tr"));
                    const asc = headerCell.getAttribute("data-order") !== "asc";
                    
                    rows.sort(function(a, b) {{
                        const ta = a.children[colIndex].innerText.trim();
                        const tb = b.children[colIndex].innerText.trim();
                        const da = Date.parse(ta), db = Date.parse(tb);
                        
                        if (!isNaN(da) && !isNaN(db) && isNaN(Number(ta))) return asc ? da - db : db - da;
                        
                        const fa = parseFloat(ta.replace(/[^\\d.-]/g, "")), fb = parseFloat(tb.replace(/[^\\d.-]/g, ""));
                        if (!isNaN(fa) && !isNaN(fb)) return asc ? fa - fb : fb - fa;
                        
                        return asc ? ta.localeCompare(tb) : tb.localeCompare(ta);
                    }});
                    
                    headerCell.closest("thead").querySelectorAll("th").forEach(function(th) {{
                        th.removeAttribute("data-order"); 
                    }});
                    headerCell.setAttribute("data-order", asc ? "asc" : "desc");
                    tbody.innerHTML = "";
                    rows.forEach(function(r) {{ tbody.appendChild(r); }});
                }});
                
                window.addEventListener("resize", function() {{
                    document.querySelectorAll(".js-plotly-plot").forEach(function(p) {{ Plotly.Plots.resize(p); }});
                }});
            }});
        </script>
    </head>
    <body>
        <div class="header">
            <div class="header-titles">
                <h1>Workload Profile: {escape(workload_name)}</h1>
                <p>Automated CI Evaluation Results Metrics &bull; Profile Report</p>
            </div>
            <div>
                <a href="../index.html" class="back-btn">← Back to Dashboard Hub</a>
            </div>
        </div>
        <div class="tab-bar">
            {outer_tab_buttons}
        </div>
        {outer_tab_contents}
    </body>
    </html>
    """
    workload_path.write_text(workload_payload, encoding = "utf-8")
    print(f"Updated workload component: workloads/{workload_path.name}")

    discovered_links = []
    for file in WORKLOADS_DIR.glob("*.html"):
        display_name = file.stem
        try:
            content = file.read_text(encoding="utf-8")
            match = re.search(r'<meta name="workload-display-name" content="([^"]+)">', content)
            if match:
                display_name = match.group(1)
        except Exception:
            pass

        discovered_links.append((file.name, display_name))

    discovered_links.sort(key = lambda item: item[1].lower())

    card_items_html = ""
    for filename, name in discovered_links:
        relative_target_link = f"workloads/{filename}"
        card_items_html += f"""
        <a class="workload-card" href="{relative_target_link}">
            <div>
                <div class="workload-card-badge">WORKLOAD PROFILE</div>
                <div class="workload-card-title">{escape(name)}</div>
                <div class="workload-card-meta">Interactive metrics, regressions, multi-variant trends, and differential raw data tables.</div>
            </div>
            <div class="workload-card-footer">
                <span>Explore Metrics</span>
                <span class="arrow-icon">→</span>
            </div>
        </a>
        """

    index_payload = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>PMICW Master Dashboard Index</title>
        <style>
            {COMMON_STYLES}
            .grid-container {{
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
                gap: 20px;
                margin-top: 25px;
            }}
            .workload-card {{
                background-color: {PANEL_BG};
                border: 1px solid {BORDER_COLOR};
                border-radius: 8px;
                padding: 24px;
                text-decoration: none;
                transition: all 0.2s ease-in-out;
                display: flex;
                flex-direction: column;
                justify-content: space-between;
                min-height: 160px;
                box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2), 0 2px 4px -1px rgba(0, 0, 0, 0.1);
            }}
            .workload-card:hover {{
                border-color: {CONTENDER_ZONE};
                background-color: #0f2131;
                transform: translateY(-3px);
                box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.4), 0 4px 6px -2px rgba(0, 0, 0, 0.2);
            }}
            .workload-card-badge {{
                font-size: 10px;
                text-transform: uppercase;
                letter-spacing: 1px;
                color: {CONTENDER_ZONE};
                font-weight: 700;
                margin-bottom: 8px;
            }}
            .workload-card-title {{
                font-size: 20px;
                font-weight: 700;
                color: {TEXT_MAIN};
                margin-bottom: 12px;
                word-break: break-all;
                letter-spacing: -0.3px;
            }}
            .workload-card-meta {{
                font-size: 13px;
                color: {TEXT_MUTED};
                line-height: 1.5;
                margin-bottom: 16px;
            }}
            .workload-card-footer {{
                display: flex;
                align-items: center;
                justify-content: space-between;
                font-size: 13px;
                font-weight: 600;
                color: {TEXT_MAIN};
                border-top: 1px solid {BORDER_COLOR};
                padding-top: 14px;
                opacity: 0.8;
                transition: opacity 0.2s;
            }}
            .workload-card:hover .workload-card-footer {{
                opacity: 1;
            }}
            .arrow-icon {{
                transition: transform 0.2s;
            }}
            .workload-card:hover .arrow-icon {{
                transform: translateX(4px);
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <div class="header-titles">
                <h1>PMICW Master Dashboard Hub</h1>
                <p>Automated CI Evaluation Results Timeline &bull; Static Dashboard Archive Site</p>
            </div>
        </div>
        
        <h3 style="color: {TEXT_MAIN}; font-size: 15px; margin-bottom: 5px; font-weight: 600;">Tracked Performance Workloads ({len(discovered_links)})</h3>
        <div class="grid-container">
            {card_items_html}
        </div>
    </body>
    </html>
    """
    
    INDEX_HTML.write_text(index_payload, encoding = "utf-8")
    print(f"Regenerated central hub mapping: {INDEX_HTML.name}")

def build_download_bar(reports, is_nested: bool = False) -> str:
    items = [
        ("csv",  reports.csv,  "Download CSV"),
        ("json", reports.json, "Download JSON"),
        ("md",   reports.md,   "Download Markdown"),
    ]

    path_prefix = "../" if is_nested else ""

    buttons = ""
    for fmt, path, label in items:
        if not path:
            continue

        icon, color = ICON_MAP[fmt]
        filename    = Path(path).name
        href        = f"{path_prefix}reports/{filename}"

        buttons += (
            f'<a class="download-btn" href="{href}" download="{filename}" '
            f'style="color:{color};">'
            f'<span style="pointer-events:none; display:inline-flex; align-items:center; gap:7px;">'
            f'{icon}{escape(label)}</span></a>\n'
        )

    return f'<div class="download-bar">{buttons}</div>' if buttons else ""

def create_group_panel(
    table_html: str | None,
    chart_fig: go.Figure | None,
    graph_fig: go.Figure | None,
) -> str:
    panel_html = '<div class="dashboard-grid">'
    if table_html:
        panel_html += f'<div class="grid-row-full">{table_html}</div>'

    if chart_fig:
        chart_raw = chart_fig.to_html(
            include_plotlyjs = False, 
            full_html        = False,
            config           = {"responsive": True}
        )
        panel_html += f'<div class="grid-row-full style-card-gap">{chart_raw}</div>'

    if graph_fig:
        graph_raw = graph_fig.to_html(
            include_plotlyjs = False, 
            full_html        = False,
            config           = {"responsive": True}
        )
        panel_html += f'<div class="grid-row-full style-card-gap">{graph_raw}</div>'

    panel_html += '</div>'
    return panel_html

def safe_id(value) -> str:
    value = str(value).strip().lower()
    value = re.sub(r'[^a-z0-9_]+', '_', value)
    value = re.sub(r'_{2,}', '_', value).strip('_')

    if not value or not value[0].isalpha():
        value = f"tab-{value}"
    return value