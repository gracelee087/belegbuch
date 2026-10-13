"""German income tax (§32a EStG, from Veranlagungszeitraum 2026) — rough effect of receipts only.

We do not estimate the whole refund: that needs social insurance (Vorsorgeaufwendungen) and more,
which a receipt folder does not have. We estimate what extra Werbungskosten are worth at a given
taxable income (zu versteuerndes Einkommen, e.g. from last year's Steuerbescheid).

Not included: Solidaritätszuschlag, Kirchensteuer, joint assessment, deduction limits.
"""
import math

ARBEITNEHMER_PAUSCHBETRAG = 1230  # §9a Satz 1 Nr. 1 a) EStG


def income_tax(taxable_income: float) -> int:
    x = math.floor(taxable_income)
    if x <= 12348:
        tax = 0.0
    elif x <= 17799:
        y = (x - 12348) / 10000
        tax = (914.51 * y + 1400) * y
    elif x <= 69878:
        z = (x - 17799) / 10000
        tax = (173.10 * z + 2397) * z + 1034.87
    elif x <= 277825:
        tax = 0.42 * x - 11135.63
    else:
        tax = 0.45 * x - 19470.38
    return math.floor(tax)


def saving(zve: float, werbungskosten: float) -> float:
    """Tax saved by Werbungskosten above the Pauschbetrag, at taxable income zve (which already includes the Pauschbetrag)."""
    above = max(werbungskosten - ARBEITNEHMER_PAUSCHBETRAG, 0)
    return float(income_tax(zve) - income_tax(zve - above))


def marginal_rate(zve: float) -> float:
    return (income_tax(zve) - income_tax(zve - 1000)) / 1000
