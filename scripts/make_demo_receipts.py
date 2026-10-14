"""Make FAKE German demo receipts and a matching FAKE ING bank CSV.

All shops, people and numbers are invented. Every receipt is stamped MUSTER (sample).
  python scripts/make_demo_receipts.py samples/demo_receipts samples/FAKE_ING_Umsatzanzeige_2026Q3.csv
"""
import os
import random
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

out, bank_csv = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)
random.seed(7)
MONO = "C:/Windows/Fonts/consola.ttf"


def photo(name, lines, angle, paper=(250, 248, 240), ink=(30, 30, 30), blur=0.6):
    f = ImageFont.truetype(MONO, 24)
    im = Image.new("RGB", (580, 90 + 36 * len(lines)), paper)
    d = ImageDraw.Draw(im)
    for i, l in enumerate(lines):
        d.text((25, 30 + 36 * i), l, fill=ink, font=f)
    d.text((25, 40 + 36 * len(lines)), "*** MUSTER - FAKE DEMO ***", fill=(170, 40, 40), font=f)
    for _ in range(1500):  # paper grain
        x, y = random.randrange(im.width), random.randrange(im.height)
        im.putpixel((x, y), tuple(max(0, c - random.randint(10, 40)) for c in paper))
    bg = Image.new("RGB", (im.width + 120, im.height + 120), (120, 110, 100))
    bg.paste(im, (60, 60))
    bg = bg.rotate(angle, expand=False, fillcolor=(120, 110, 100)).filter(ImageFilter.GaussianBlur(blur))
    bg.save(os.path.join(out, name), quality=82)


def text_pdf(name, title, lines):
    c = canvas.Canvas(os.path.join(out, name), pagesize=A4)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, 790, title)
    c.setFont("Helvetica", 11)
    for i, l in enumerate(lines):
        c.drawString(50, 760 - 18 * i, l)
    c.setFillColorRGB(0.7, 0.15, 0.15)
    c.drawString(50, 760 - 18 * (len(lines) + 2), "MUSTER - FAKE DEMO")
    c.save()


# --- photos (paper receipts) ---
photo("lesezeichen_2026-07-08.jpg", ["Buchhandlung Lesezeichen", "Musterstr. 1, 60311 Frankfurt", "St.-Nr. 000/000/00000",
      "", "08.07.2026  14:12", "", "Machine Learning Grundl.  49,99 B", "", "SUMME EUR               49,99",
      "Kartenzahlung girocard   49,99", "", "MwSt   Netto   Steuer   Brutto", "B 7%   46,72   3,27     49,99"], 2.5)
photo("elektro-funke_2026-09-11.jpg", ["Elektro Funke", "Beispielweg 7, 60314 Frankfurt", "", "11.09.2026 17:40",
      "USB Headset Pro         79,00 A", "", "SUMME EUR               79,00", "EC-Karte                79,00", "",
      "A 19%  Netto 66,39  MwSt 12,61"], -3, paper=(244, 242, 236), ink=(90, 90, 95), blur=0.9)  # faded thermal paper
photo("cafe-muster_2026-09-03.jpg", ["Cafe Muster", "Bergweg 5, 60316 Frankfurt", "03.09.2026 09:05",
      "Cappuccino           3,90", "Croissant            4,50", "BAR                  8,40", "inkl. 19% MwSt       1,34"], 1.5)
photo("apotheke-am-markt_2026-08-22.jpg", ["Apotheke am Markt", "Marktplatz 2, 60313 Frankfurt", "22.08.2026 11:31",
      "Ibuprofen 400 20St      6,95 A", "Nasenspray              5,90 A", "Vitamin D3 Tropfen     14,95 A",
      "SUMME EUR               27,80", "Kartenzahlung           27,80", "A 19%  Netto 23,36  MwSt 4,44"], -1.5)
photo("haushaltsservice_rechnung_2026-08.jpg", ["Muster Haushaltsservice", "Rechnung Nr. 2026-081", "Datum: 05.08.2026",
      "Leistung: Fensterreinigung", "Wohnung Musterstr. 3", "", "Arbeitskosten        100,84", "MwSt 19%              19,16",
      "Gesamtbetrag         120,00", "", "Zahlbar per Ueberweisung", "bis 15.08.2026"], 1, blur=0.7)

# --- PDFs with a text layer ---
text_pdf("versandhaus-muster_rechnung_2026-07-11.pdf", "Versandhaus Muster GmbH - Rechnung",
         ["Rechnungsdatum: 11.07.2026", "Bestellnummer: 000-0000000", "", "Monitor 27 Zoll   189,90 EUR", "",
          "Zwischensumme (netto)   159,58 EUR", "USt. 19%   30,32 EUR", "Gesamtbetrag   189,90 EUR", "Bezahlt mit Kreditkarte"])
text_pdf("regio-bahn_deutschlandticket_2026-07.pdf", "Regio-Bahn Muster - Deutschlandticket",
         ["Rechnungsdatum: 02.07.2026", "Gueltig: Juli 2026", "Preis 63,00 EUR", "enthaltene MwSt 7%: 4,12 EUR",
          "Zahlung: Lastschrift"])
text_pdf("musterhilfe_spende_2026-07-20.pdf", "Aktion Musterhilfe e.V. - Zuwendungsbestaetigung",
         ["Bestaetigung ueber Geldzuwendungen", "Name des Zuwendenden: Max Mustermann (fiktiv)",
          "Betrag der Zuwendung: 50,00 EUR", "Tag der Zuwendung: 20.07.2026", "Art: Geldzuwendung, Ueberweisung"])

# --- saved e-mail ---
open(os.path.join(out, "lernplattform_2026-08-14.eml"), "w", encoding="utf-8").write(
"""From: Lernplattform Muster <rechnung@lernplattform.example>
To: max@example.com
Date: Fri, 14 Aug 2026 10:02:00 +0200
Subject: Ihre Rechnung / Your receipt
Content-Type: text/plain; charset=utf-8

Rechnung vom 14.08.2026
Online-Kurs: Python fuer Datenanalyse      19,99 EUR
enthaltene MwSt 19%                         3,19 EUR
Gesamt                                     19,99 EUR
Bezahlt mit Mastercard **** 0000

MUSTER - FAKE DEMO
""")

# --- matching FAKE ING bank CSV ---
rows = [
    ("01.07.2026", "Wohnbau Muster GmbH", "Lastschrift", "Miete Juli 2026", -950.00),
    ("02.07.2026", "Regio-Bahn Muster GmbH", "Lastschrift", "Deutschlandticket Juli", -63.00),
    ("05.07.2026", "Frischmarkt Muster", "Lastschrift", "Kartenzahlung Frischmarkt", -42.37),
    ("08.07.2026", "Buchhandlung Lesezeichen", "Lastschrift", "Kartenzahlung Buchhandlung", -49.99),
    ("12.07.2026", "Versandhaus Muster GmbH", "Lastschrift", "Bestellung 000-0000000 Monitor", -189.90),
    ("15.07.2026", "Beispiel AG", "Gehalt/Rente", "Gehalt Juli 2026", 2850.00),
    ("20.07.2026", "Aktion Musterhilfe e.V.", "Ueberweisung", "Spende", -50.00),
    ("01.08.2026", "Wohnbau Muster GmbH", "Lastschrift", "Miete August 2026", -950.00),
    ("02.08.2026", "Regio-Bahn Muster GmbH", "Lastschrift", "Deutschlandticket August", -63.00),
    ("06.08.2026", "Netz Muster Telekommunikation", "Lastschrift", "Internet August", -39.95),
    ("10.08.2026", "Muster Haushaltsservice", "Ueberweisung", "Rechnung 2026-081 Fensterreinigung", -120.00),
    ("14.08.2026", "Lernplattform Muster", "Lastschrift", "Online-Kurs Python", -19.99),
    ("15.08.2026", "Beispiel AG", "Gehalt/Rente", "Gehalt August 2026", 2850.00),
    ("22.08.2026", "Apotheke am Markt", "Lastschrift", "Kartenzahlung Apotheke", -27.80),
    ("01.09.2026", "Wohnbau Muster GmbH", "Lastschrift", "Miete September 2026", -950.00),
    ("02.09.2026", "Regio-Bahn Muster GmbH", "Lastschrift", "Deutschlandticket September", -63.00),
    ("06.09.2026", "Netz Muster Telekommunikation", "Lastschrift", "Internet September", -39.95),
    ("11.09.2026", "Elektro Funke", "Lastschrift", "Kartenzahlung Elektro", -79.00),
    ("15.09.2026", "Beispiel AG", "Gehalt/Rente", "Gehalt September 2026", 2850.00),
    ("19.09.2026", "Gewerkschaft Muster", "Lastschrift", "Mitgliedsbeitrag Q3", -45.00),
    ("26.09.2026", "Lieferservice Muster", "Lastschrift", "Kartenzahlung Essen", -23.50),
]
fmt = lambda v: f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
saldo = 2500.00
lines = ["Umsatzanzeige;Datei erstellt am: 01.10.2026 09:00", "", "IBAN;DE00 0000 0000 0000 0000 00",
         "Kontoname;Girokonto (FAKE - Testdaten)", "Bank;ING (FAKE - Testdaten)", "Kunde;Max Mustermann (fiktiv)",
         "Zeitraum;01.07.2026 - 30.09.2026", "",
         "Buchung;Wertstellungsdatum;Auftraggeber/Empfänger;Buchungstext;Verwendungszweck;Saldo;Währung;Betrag;Währung"]
for day, who, kind, purpose, amount in rows:
    saldo += amount
    lines.append(";".join([day, day, who, kind, purpose, fmt(saldo), "EUR", fmt(amount), "EUR"]))
open(bank_csv, "w", encoding="utf-8-sig", newline="\r\n").write("\n".join(lines) + "\n")
print(sorted(os.listdir(out)))
