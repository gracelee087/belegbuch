"""Receipts folder + ING CSV -> Excel book for the Steuerberater.

  python src/build_book.py receipts/ bank.csv out.xlsx [--zve 38000]

Sheets: Receipts (every receipt, checked), Missing receipts (bank lines with no receipt),
Estimate (what the receipts are worth; --zve = taxable income from last year's Steuerbescheid).
"""
import argparse
import json
import os
import sys
import time

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill

sys.path.insert(0, os.path.dirname(__file__))
from bank_ing import read_ing_csv
from extract import RECEIPT_EXT, check, extract
from match import match
from tax import ARBEITNEHMER_PAUSCHBETRAG, marginal_rate, saving

WERBUNGSKOSTEN = {"Arbeitsmittel", "Fachliteratur", "Fortbildung", "Fahrtkosten", "Gewerkschaft"}

# Hint only: which bank lines probably need a receipt for the tax folder
CATEGORY_EN = {"Arbeitsmittel": "work equipment", "Fachliteratur": "professional books", "Fortbildung": "training",
               "Fahrtkosten": "commuting", "Gewerkschaft": "union fee", "Spende": "donation",
               "Haushaltsnahe Dienstleistung": "household service", "Krankheitskosten": "medical", "Privat": "private"}


def label(cat: str | None) -> str:
    return f"{cat} ({CATEGORY_EN[cat]})" if cat in CATEGORY_EN else (cat or "")


BANK_HINTS = {"gewerkschaft": "Gewerkschaft", "regio-bahn": "Fahrtkosten", "deutschlandticket": "Fahrtkosten",
              "spende": "Spende", "e.v.": "Spende", "haushaltsservice": "Haushaltsnahe Dienstleistung",
              "reinigung": "Haushaltsnahe Dienstleistung", "apotheke": "Krankheitskosten",
              "fachbuch": "Fachliteratur", "kurs": "Fortbildung"}

BOLD, WARN = Font(bold=True), PatternFill("solid", fgColor="FFE699")


def bank_hint(t: dict) -> str:
    text = (t["counterparty"] + " " + t["purpose"]).lower()
    return next((cat for key, cat in BANK_HINTS.items() if key in text), "")


def read_receipts(folder: str, cache_path: str) -> list[dict]:
    cache = json.load(open(cache_path, encoding="utf-8")) if os.path.exists(cache_path) else {}
    out = []
    for name in sorted(os.listdir(folder)):
        if os.path.splitext(name)[1].lower() not in RECEIPT_EXT:
            continue
        path = os.path.join(folder, name)
        key = f"{name}:{os.path.getsize(path)}:{os.path.getmtime(path)}"
        if key not in cache:
            t = time.time()
            r = extract(path)
            r["seconds"] = round(time.time() - t, 1)
            cache[key] = r
            json.dump(cache, open(cache_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
            print(f"{name}: {r.get('vendor')} {r.get('total')} ({r['seconds']} s)")
        out.append(cache[key])
    return out


def sheet(wb, title, header, rows, warn_col=None):
    ws = wb.create_sheet(title)
    ws.append(header)
    for c in ws[1]:
        c.font = BOLD
    for row in rows:
        ws.append(row)
        if warn_col is not None and row[warn_col]:
            for c in ws[ws.max_row]:
                c.fill = WARN
    for col in ws.columns:
        ws.column_dimensions[col[0].column_letter].width = min(max(len(str(c.value or "")) for c in col) + 2, 50)
    ws.freeze_panes = "A2"
    return ws


def build(folder, bank_csv, out, zve=None):
    receipts = read_receipts(folder, os.path.join(folder, ".extracted.json"))
    tx = read_ing_csv(bank_csv)
    m = match(tx, receipts)
    paired = {id(r): t for t, r in m["matched"]}

    wk_total = sum(r.get("total") or 0 for r in receipts if r.get("category") in WERBUNGSKOSTEN)

    wb = Workbook()
    wb.remove(wb.active)
    rows, wk_so_far = [], 0.0
    for r in sorted(receipts, key=lambda r: r.get("date") or ""):
        vat = {v.get("rate"): v.get("amount") for v in r.get("vat") or []}
        t = paired.get(id(r))
        extra = ""
        if zve is not None and r.get("category") in WERBUNGSKOSTEN and r.get("total"):
            extra = saving(zve, wk_so_far + r["total"]) - saving(zve, wk_so_far)
            wk_so_far += r["total"]
        rows.append([r.get("date"), r.get("vendor"), r.get("total"), vat.get(19), vat.get(7), label(r.get("category")),
                     r.get("payment"), ", ".join(r.get("items") or []), r.get("source"), r.get("read_as"),
                     t["date"].isoformat() if t else ("cash" if r.get("payment") == "cash" else "not found"),
                     extra, "; ".join(check(r))])
    sheet(wb, "Receipts", ["Date", "Shop", "Total €", "VAT 19%", "VAT 7%", "Category (suggested)", "Paid by",
                           "Items", "File", "Read as", "Bank line", "≈ tax saved €", "Please check"],
          rows, warn_col=12)

    missing = sorted(m["missing_receipt"], key=lambda t: (bank_hint(t) == "", t["date"]))
    sheet(wb, "Missing receipts", ["Date", "Payee", "Purpose", "Amount €", "Probably tax-relevant"],
          [[t["date"].isoformat(), t["counterparty"], t["purpose"], t["amount"], label(bank_hint(t)) if bank_hint(t) else ""]
           for t in missing], warn_col=4)

    ws = wb.create_sheet("Estimate")
    ws.append(["Rough estimate, not tax advice. Your Steuerberater decides."])
    ws["A1"].font = BOLD
    ws.append(["Work expenses from receipts (Werbungskosten) €", round(wk_total, 2)])
    ws.append(["Employee lump sum (Arbeitnehmer-Pauschbetrag, §9a EStG) €", ARBEITNEHMER_PAUSCHBETRAG])
    ws.append(["Still to go before receipts save any tax €", round(max(ARBEITNEHMER_PAUSCHBETRAG - wk_total, 0), 2)])
    if zve is not None:
        ws.append(["Taxable income (input, e.g. last Steuerbescheid) €", zve])
        ws.append(["Each €100 of work expenses above the lump sum ≈ € less tax", round(100 * marginal_rate(zve), 2)])
        ws.append(["≈ Tax saved by these receipts (§32a EStG 2026) €", saving(zve, wk_total)])
    else:
        ws.append(["For an estimate, pass --zve"])
    ws.append([])
    ws.append(["Not included: solidarity surcharge, church tax, joint assessment, special expenses,"
               " §35a, caps. Only receipts in: " + ", ".join(label(c) for c in sorted(WERBUNGSKOSTEN)) + "."])
    ws.column_dimensions["A"].width = 58
    wb.save(out)
    return {"receipts": len(receipts), "matched": len(m["matched"]), "missing": len(missing),
            "relevant_missing": sum(1 for t in missing if bank_hint(t)), "werbungskosten": round(wk_total, 2)}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("folder"); ap.add_argument("bank_csv"); ap.add_argument("out")
    ap.add_argument("--zve", type=float)
    a = ap.parse_args()
    print(build(a.folder, a.bank_csv, a.out, a.zve))
