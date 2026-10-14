"""Where did the money go? Gemma labels bank lines and writes a short summary; code does every number.

The summary is checked: every number Gemma writes must be one the code computed. Anything else is flagged.
"""
import json
import os
import re
from collections import defaultdict

SPEND_CATEGORIES = ["Rent", "Groceries", "Transport", "Phone & internet", "Eating out", "Health",
                    "Education", "Donations", "Household services", "Shopping", "Leisure", "Other"]

LABEL_PROMPT = """You sort German bank statement lines into spending categories for a private person.
Categories: %s.
Return JSON only: {"labels": {"<id>": "<category>", ...}} with one entry per line id.
Lines:
%s"""

SUMMARY_PROMPT = """You write a short, plain-English summary of a person's spending for one quarter.
Use ONLY the numbers in the JSON below, written exactly as they appear there (you may add a € sign or %%).
Do not compute new numbers, do not round differently, do not give advice. 3 to 5 sentences.
Return JSON only: {"summary": "..."}
%s"""


def _chat(prompt: str) -> dict:
    import ollama
    r = ollama.chat(model=os.environ.get("OLLAMA_MODEL", "gemma4:e4b"),
                    messages=[{"role": "user", "content": prompt}],
                    format="json", think=False, options={"temperature": 0})
    return json.loads(r.message.content)


def label(transactions: list[dict], cache_path: str) -> list[str]:
    """One category per spending line (income lines get ''). Labels are cached by line text."""
    cache = json.load(open(cache_path, encoding="utf-8")) if os.path.exists(cache_path) else {}
    key = lambda t: f"{t['counterparty']} | {t['purpose']}"
    todo = sorted({key(t) for t in transactions if t["amount"] < 0} - cache.keys())
    if todo:
        lines = "\n".join(f"{i}: {k}" for i, k in enumerate(todo))
        got = _chat(LABEL_PROMPT % (", ".join(SPEND_CATEGORIES), lines)).get("labels", {})
        for i, k in enumerate(todo):
            c = got.get(str(i))
            cache[k] = c if c in SPEND_CATEGORIES else "Other"
        json.dump(cache, open(cache_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return [cache[key(t)] if t["amount"] < 0 else "" for t in transactions]


def stats(transactions: list[dict], labels: list[str]) -> dict:
    income = round(sum(t["amount"] for t in transactions if t["amount"] > 0), 2)
    spent = round(-sum(t["amount"] for t in transactions if t["amount"] < 0), 2)
    by_cat, by_month, by_payee = defaultdict(float), defaultdict(float), defaultdict(float)
    months_of = defaultdict(set)
    for t, c in zip(transactions, labels):
        if t["amount"] >= 0:
            continue
        m = t["date"].strftime("%Y-%m")
        by_cat[c] -= t["amount"]
        by_month[m] -= t["amount"]
        by_payee[t["counterparty"]] -= t["amount"]
        months_of[(t["counterparty"], -t["amount"])].add(m)
    n_months = len({t["date"].strftime("%Y-%m") for t in transactions})
    cats = sorted(by_cat.items(), key=lambda kv: -kv[1])
    return {
        "months": n_months,
        "income_total": income,
        "spending_total": spent,
        "left_over": round(income - spent, 2),
        "spending_share_of_income_pct": round(100 * spent / income, 1) if income else None,
        "by_category": [{"category": c, "total": round(v, 2), "share_pct": round(100 * v / spent, 1)} for c, v in cats],
        "by_month": [{"month": m, "total": round(v, 2)} for m, v in sorted(by_month.items())],
        "top_payees": [{"payee": p, "total": round(v, 2)} for p, v in sorted(by_payee.items(), key=lambda kv: -kv[1])[:5]],
        "recurring": [{"payee": p, "amount": round(a, 2), "months": len(ms)}
                      for (p, a), ms in sorted(months_of.items(), key=lambda kv: -kv[0][1]) if len(ms) == n_months > 1],
    }


def _pretty(v):
    """Numbers as the summary should print them: 8,550.00 and 55.4."""
    if isinstance(v, bool) or v is None:
        return v
    if isinstance(v, float) or isinstance(v, int):
        return f"{v:,.2f}"
    if isinstance(v, dict):
        return {k: (f"{x:.1f}" if k.endswith("_pct") and isinstance(x, (int, float)) else _pretty(x)) for k, x in v.items()}
    if isinstance(v, list):
        return [_pretty(x) for x in v]
    return v


def summarize(s: dict) -> str:
    return str(_chat(SUMMARY_PROMPT % json.dumps(_pretty(s), ensure_ascii=False, indent=1)).get("summary", "")).strip()


NUMBER = re.compile(r"\d[\d,.]*\d|\d")


def _variants(x: float) -> set[str]:
    out = {f"{x:.2f}", f"{x:,.2f}", f"{x:.1f}", f"{x:,.1f}"}
    if abs(x - round(x)) < 1e-9:
        out |= {f"{x:.0f}", f"{x:,.0f}"}
    return out


def allowed_numbers(s: dict) -> set[str]:
    nums = set()

    def walk(v):
        if isinstance(v, bool):
            return
        if isinstance(v, (int, float)):
            nums.update(_variants(float(v)))
        elif isinstance(v, dict):
            for x in v.values():
                walk(x)
        elif isinstance(v, list):
            for x in v:
                walk(x)
        elif isinstance(v, str):
            nums.update(NUMBER.findall(v))  # e.g. "2026-07"
    walk(s)
    return nums


def unsupported_numbers(summary: str, s: dict) -> list[str]:
    """Numbers in Gemma's summary that the code did not compute."""
    ok = allowed_numbers(s)
    return [n for n in NUMBER.findall(summary) if n.rstrip(".,") not in ok]
