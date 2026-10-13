# Belegbuch — your receipts, sorted for the Steuerberater, without leaving your laptop

Every quarter I hand my German tax advisor (Steuerberater) a folder of receipts and a spreadsheet.
Collecting the receipts, typing them in, matching them to the bank statement and finding the ones
that are missing: every one of those steps is tedious. Belegbuch does them on my own computer.

Put photos, PDFs and saved e-mail receipts into one folder, add the CSV export from the bank, and get
an Excel book with three sheets:

| Sheet | What it shows |
|---|---|
| **Belege** | Every receipt: date, shop, total, VAT 19 % / 7 %, a suggested tax category, which bank line it belongs to, and a yellow row when the code thinks the model misread it |
| **Fehlende Belege** | Bank payments with no receipt, the probably tax-relevant ones first |
| **Schaetzung** | What the receipts are worth so far: how far you are from the €1,230 Arbeitnehmer-Pauschbetrag and roughly how much tax each €100 above it saves (German tariff 2026) |

It is a sorting helper, not tax advice. The Steuerberater decides.

## Everything runs locally

| Part | Open-source piece | License |
|---|---|---|
| Reading photos and filling the fields | [Gemma 4](https://ai.google.dev/gemma) `gemma4:e4b` on [Ollama](https://github.com/ollama/ollama) | Apache-2.0 / MIT |
| OCR (optional second path) | [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR) | Apache-2.0 |
| PDF text | [pdfplumber](https://github.com/jsvine/pdfplumber) | MIT |
| Excel | [openpyxl](https://openpyxl.readthedocs.io) | MIT |

Receipts carry names, addresses, card digits and what you bought. None of it is sent anywhere: the model
runs in Ollama on this machine. A cloud path (Gemma 4 through the Gemini API) exists in the code for people
without the disk space, but it is off by default and sends the receipts to Google.

## How it reads a receipt

1. **Photo** → Gemma 4 reads the image (`RECEIPT_MODE=vision`, default), or PaddleOCR reads the text and Gemma fills the fields (`RECEIPT_MODE=ocr`).
2. **PDF with text** and **saved e-mail (.eml)** → the text goes straight to Gemma; no OCR needed. A scanned PDF is rendered and read like a photo.
3. **The code checks what the model read**: required fields, VAT rate 19 % or 7 %, VAT that fits the total, a known category. Anything odd turns the row yellow.
4. **Bank matching**: a receipt matches a bank payment with the same amount within three days.

## Run it

Needs Python 3.11 and [Ollama](https://ollama.com).

```bash
ollama pull gemma4:e4b
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt     # macOS/Linux: .venv/bin/python

# demo with fake data
.venv/Scripts/python scripts/make_demo_receipts.py samples/demo_receipts
.venv/Scripts/python src/build_book.py samples/demo_receipts samples/FAKE_ING_Umsatzanzeige_2026Q3.csv Belegbuch.xlsx --zve 38000

# tests
.venv/Scripts/python -m unittest discover -s tests
```

`--zve` is your taxable income (zu versteuerndes Einkommen), e.g. from last year's Steuerbescheid. Without it
the estimate sheet only shows the distance to the Pauschbetrag. Settings live in `.env` (see `.env.example`).
Results are cached in `<folder>/.extracted.json`, so a second run only reads new receipts.

## Demo results (fake data, one run, 2026-10-13)

Six fake receipts (three photos, two PDFs, one e-mail) and a fake ING quarter with 21 bank lines,
on a laptop with a Ryzen 5 4600H, 15.4 GB RAM and integrated graphics only:

- 5 of 6 receipts read with the right date, shop, total and VAT. The sixth, a café photo, came back with a
  wrong total (17.84 instead of 8.40); the VAT check caught it and marked the row yellow.
- 5 receipts matched their bank line. The café receipt was paid in cash, so there is no bank line.
- 13 bank payments had no receipt; 6 of them were flagged as probably tax-relevant (donation, two train
  tickets, window cleaning, pharmacy, union fee).
- 6.7–16.1 s per receipt once the model was loaded.

These numbers come from fake receipts I generated, not from real ones; real photos are harder.

## Limits

- The ING CSV layout is written from memory and has not been compared to a real export.
- Tax: only the 2026 tariff (§32a EStG) and the €1,230 Pauschbetrag (§9a EStG). No Solidaritätszuschlag,
  Kirchensteuer, joint assessment, Sonderausgaben, §35a or deduction limits. Categories are suggestions.
- Matching needs exact amounts; split payments or refunds are not handled.

## Layout

| Path | What it is |
|---|---|
| `src/extract.py` | Read one receipt with Gemma (photo / PDF / e-mail), code checks |
| `src/bank_ing.py` | Read the ING CSV |
| `src/match.py` | Bank lines ↔ receipts |
| `src/tax.py` | §32a EStG 2026 tariff and the value of extra Werbungskosten |
| `src/build_book.py` | Folder + CSV → Excel |
| `scripts/make_demo_receipts.py` | Makes the fake demo receipts |
| `samples/` | Fake bank CSV, fake receipts, demo Excel |

## License

MIT — see [LICENSE](LICENSE). Gemma 4 is released by Google under Apache-2.0.
