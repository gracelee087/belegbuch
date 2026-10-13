"""Render the Excel book as one HTML page (for a demo screenshot)."""
import html
import sys
from openpyxl import load_workbook

wb = load_workbook(sys.argv[1])
parts = ["<meta charset='utf-8'><style>body{font:13px Segoe UI,Arial;margin:20px;background:#fff}"
         "h2{font-size:15px;margin:18px 0 6px}table{border-collapse:collapse}td,th{border:1px solid #ccc;padding:3px 7px}"
         "th{background:#eef1f5;text-align:left}tr.w td{background:#FFE699}</style>"]
for ws in wb:
    parts.append(f"<h2>{html.escape(ws.title)}</h2><table>")
    for i, row in enumerate(ws.iter_rows()):
        warn = any(c.fill and c.fill.fgColor and c.fill.fgColor.rgb in ("00FFE699", "FFFFE699") for c in row)
        tag = "th" if i == 0 and ws.title != "Schaetzung" else "td"
        cells = "".join(f"<{tag}>{html.escape('' if c.value is None else str(c.value))}</{tag}>" for c in row)
        parts.append(f"<tr class='{'w' if warn else ''}'>{cells}</tr>")
    parts.append("</table>")
open(sys.argv[2], "w", encoding="utf-8").write("".join(parts))
