"""Read one receipt (photo, PDF or saved e-mail) with Gemma. Everything runs on this computer by default.

  RECEIPT_BACKEND=ollama  OLLAMA_MODEL=gemma4:e4b   (default, local)
  RECEIPT_MODE=vision     Gemma reads photos itself (default)
  RECEIPT_MODE=ocr        PaddleOCR reads photos, Gemma fills the fields
  RECEIPT_BACKEND=gemini  GEMINI_API_KEY=...  GEMMA_MODEL=gemma-4-26b-a4b-it   (optional, sends data to Google)

PDFs with a text layer and e-mails are read as text; no OCR is needed for them.
"""
import base64
import email
import json
import mimetypes
import os
import re
import tempfile
import urllib.request
from email import policy


def _load_dotenv(path=os.path.join(os.path.dirname(__file__), "..", ".env")):
    if os.path.exists(path):
        for line in open(path, encoding="utf-8"):
            k, sep, v = line.strip().partition("=")
            if sep and not k.startswith("#"):
                os.environ.setdefault(k.strip(), v.strip())


_load_dotenv()

CATEGORIES = ["Arbeitsmittel", "Fachliteratur", "Fortbildung", "Fahrtkosten", "Gewerkschaft",
              "Spende", "Haushaltsnahe Dienstleistung", "Krankheitskosten", "Privat"]

PROMPT = """You read German receipts and invoices for a private person's income tax folder. Return JSON only:
{"date":"YYYY-MM-DD","vendor":str,"total":number,
 "vat":[{"rate":19|7,"amount":number}],"payment":"card|cash|transfer|unknown",
 "items":[str],"category":one of %s}
Use the printed values. If a field is not printed, use null.
Category is a suggestion for the person to confirm: work equipment = Arbeitsmittel, books for the job = Fachliteratur,
courses = Fortbildung, tickets for the commute = Fahrtkosten, union fees = Gewerkschaft, donations = Spende,
cleaning/craftsmen at home = Haushaltsnahe Dienstleistung, pharmacy/doctor = Krankheitskosten, everything else = Privat.""" % json.dumps(CATEGORIES, ensure_ascii=False)

IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp"}
RECEIPT_EXT = IMAGE_EXT | {".pdf", ".eml"}

_paddle = None


def ocr_text(image_path: str) -> str:
    global _paddle
    if _paddle is None:
        from paddleocr import PaddleOCR
        # enable_mkldnn=False: oneDNN path fails on Windows CPU with paddlepaddle 3.3.1
        _paddle = PaddleOCR(lang="de", use_doc_orientation_classify=False, use_doc_unwarping=False,
                            use_textline_orientation=False, enable_mkldnn=False)
    lines = []
    for r in _paddle.predict(image_path):
        lines += r["rec_texts"]
    return "\n".join(lines)


def _pdf(path: str) -> tuple[str | None, str | None]:
    """Text of a PDF, or a rendered first page if it has no text layer (scan)."""
    import pdfplumber
    with pdfplumber.open(path) as pdf:
        text = "\n".join(page.extract_text() or "" for page in pdf.pages).strip()
        if text:
            return text, None
        png = os.path.join(tempfile.gettempdir(), os.path.basename(path) + ".png")
        pdf.pages[0].to_image(resolution=200).save(png)
        return None, png


def _eml(path: str) -> str:
    msg = email.message_from_binary_file(open(path, "rb"), policy=policy.default)
    part = msg.get_body(preferencelist=("plain", "html"))
    body = part.get_content() if part else ""
    if part is not None and part.get_content_type() == "text/html":
        body = re.sub(r"<[^>]+>", " ", body)
    return f"From: {msg['from']}\nDate: {msg['date']}\nSubject: {msg['subject']}\n\n{body}"


def _gemini(image_path: str | None, text: str | None) -> str:
    model = os.environ.get("GEMMA_MODEL", "gemma-4-26b-a4b-it")
    parts = [{"text": PROMPT + ("\n\nReceipt text:\n" + text if text else "")}]
    if image_path:
        mime = mimetypes.guess_type(image_path)[0] or "image/jpeg"
        parts.append({"inline_data": {"mime_type": mime, "data": base64.b64encode(open(image_path, "rb").read()).decode()}})
    req = urllib.request.Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        data=json.dumps({"contents": [{"parts": parts}], "generationConfig": {"temperature": 0}}).encode(),
        method="POST", headers={"x-goog-api-key": os.environ["GEMINI_API_KEY"], "content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r)["candidates"][0]["content"]["parts"][-1]["text"]


def _ollama(image_path: str | None, text: str | None) -> str:
    import ollama
    msg = {"role": "user", "content": PROMPT + ("\n\nReceipt text:\n" + text if text else "")}
    if image_path:
        msg["images"] = [image_path]
    r = ollama.chat(model=os.environ.get("OLLAMA_MODEL", "gemma4:e4b"), messages=[msg],
                    format="json", think=False, options={"temperature": 0})
    return r.message.content


def _parse(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`").removeprefix("json").strip()
    return json.loads(text[text.find("{"): text.rfind("}") + 1])


def extract(path: str) -> dict:
    backend = os.environ.get("RECEIPT_BACKEND", "ollama")
    mode = os.environ.get("RECEIPT_MODE", "vision")
    ext = os.path.splitext(path)[1].lower()
    image, text, how = None, None, ""
    if ext == ".eml":
        text, how = _eml(path), "email text"
    elif ext == ".pdf":
        text, image = _pdf(path)
        how = "pdf text" if text else "pdf scan"
    else:
        image, how = path, "photo"
    if image and mode == "ocr":
        text, image, how = ocr_text(image), None, how + " + PaddleOCR"
    raw = _gemini(image, text) if backend == "gemini" else _ollama(image, text)
    receipt = _parse(raw)
    receipt.update(source=os.path.basename(path), read_as=how, backend=backend)
    return receipt


def check(receipt: dict) -> list[str]:
    """Code-side checks on what the model read. Returns problems for a person to look at."""
    problems = []
    for field in ("date", "vendor", "total"):
        if not receipt.get(field):
            problems.append(f"missing {field}")
    if receipt.get("date") and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(receipt["date"])):
        problems.append(f"date not YYYY-MM-DD: {receipt['date']}")
    for v in receipt.get("vat") or []:
        if v.get("rate") not in (19, 7):
            problems.append(f"unusual VAT rate {v.get('rate')}")
    total, vat = receipt.get("total"), sum((v.get("amount") or 0) for v in receipt.get("vat") or [])
    if total and vat and vat > total * 0.16 + 0.01:  # 19/119 ≈ 0.1597 is the most VAT a total can hold
        problems.append("VAT larger than possible for this total")
    for v in receipt.get("vat") or []:
        if total and v.get("rate") in (19, 7) and v.get("amount") and len(receipt["vat"]) == 1:
            expected = total * v["rate"] / (100 + v["rate"])
            if abs(v["amount"] - expected) > 0.05:
                problems.append(f"VAT {v['amount']} does not fit {v['rate']}% of {total} (expected {expected:.2f})")
    if receipt.get("category") not in CATEGORIES:
        problems.append(f"unknown category {receipt.get('category')}")
    return problems
