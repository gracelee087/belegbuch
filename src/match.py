"""Match bank transactions to receipts; list what is missing on either side."""
from datetime import date


def match(transactions: list[dict], receipts: list[dict], days: int = 3) -> dict:
    spending = [t for t in transactions if t["amount"] < 0]
    free = list(receipts)
    matched, missing_receipt = [], []
    for t in spending:
        hit = next((r for r in free
                    if r.get("total") is not None and abs(r["total"] + t["amount"]) < 0.01
                    and abs((date.fromisoformat(r["date"]) - t["date"]).days) <= days), None)
        if hit:
            free.remove(hit)
            matched.append((t, hit))
        else:
            missing_receipt.append(t)
    return {"matched": matched, "missing_receipt": missing_receipt, "no_bank_entry": free}
