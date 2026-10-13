"""Read an ING (Germany) 'Umsatzanzeige' CSV export.

Column layout is assumed (not yet checked against a real export).
"""
import csv
import re
from datetime import datetime


def _num(s: str) -> float:
    return float(s.replace(".", "").replace(",", "."))


def read_ing_csv(path: str) -> list[dict]:
    with open(path, encoding="utf-8-sig") as f:
        lines = f.read().splitlines()
    start = next(i for i, l in enumerate(lines) if l.startswith("Buchung;"))
    rows = []
    for f in csv.reader(lines[start + 1:], delimiter=";"):
        if len(f) < 9 or not re.match(r"\d\d\.\d\d\.\d{4}$", f[0]):
            continue
        rows.append({
            "date": datetime.strptime(f[0], "%d.%m.%Y").date(),
            "counterparty": f[2],
            "type": f[3],
            "purpose": f[4],
            "amount": _num(f[7]),
            "currency": f[8],
        })
    return rows
