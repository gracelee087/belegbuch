"""Make FAKE demo receipts (photos, a text PDF, a saved e-mail) that match samples/FAKE_ING_Umsatzanzeige_2026Q3.csv."""
import os
import random
import sys
from PIL import Image, ImageDraw, ImageFilter, ImageFont

out = sys.argv[1]
os.makedirs(out, exist_ok=True)
random.seed(7)
MONO = "C:/Windows/Fonts/consola.ttf"


def photo(name, lines, angle):
    f = ImageFont.truetype(MONO, 24)
    im = Image.new("RGB", (560, 60 + 36 * len(lines)), (250, 248, 240))
    d = ImageDraw.Draw(im)
    for i, l in enumerate(lines):
        d.text((25, 30 + 36 * i), l, fill=(30, 30, 30), font=f)
    bg = Image.new("RGB", (im.width + 120, im.height + 120), (120, 110, 100))
    bg.paste(im, (60, 60))
    bg = bg.rotate(angle, expand=False, fillcolor=(120, 110, 100)).filter(ImageFilter.GaussianBlur(0.6))
    bg.save(os.path.join(out, name), quality=85)


photo("thalia_2026-07-08.jpg", ["THALIA Buchhandlung", "Zeil 1, 60313 Frankfurt", "St.-Nr. 045/123/45678", "",
      "08.07.2026  14:12", "", "Machine Learning Grundl.  49,99 B", "", "SUMME EUR               49,99",
      "Kartenzahlung girocard   49,99", "", "MwSt   Netto   Steuer   Brutto", "B 7%   46,72   3,27     49,99"], 2.5)
photo("mediamarkt_2026-09-11.jpg", ["MediaMarkt Frankfurt", "Hanauer Landstr. 1", "", "11.09.2026 17:40",
      "USB Headset Pro         79,00 A", "", "SUMME EUR               79,00", "EC-Karte                79,00", "",
      "A 19%  Netto 66,39  MwSt 12,61"], -3)
photo("cafe_2026-09-03.jpg", ["Cafe Muster", "Berger Str. 5", "03.09.2026 09:05", "Cappuccino           3,90",
      "Croissant            4,50", "BAR                  8,40", "inkl. 19% MwSt       1,34"], 1.5)

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


def text_pdf(name, title, lines):
    c = canvas.Canvas(os.path.join(out, name), pagesize=A4)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, 790, title)
    c.setFont("Helvetica", 11)
    for i, l in enumerate(lines):
        c.drawString(50, 760 - 18 * i, l)
    c.save()


text_pdf("amazon_rechnung_2026-07-11.pdf", "Amazon EU S.a r.l. - Rechnung",
         ["Rechnungsdatum: 11.07.2026", "Bestellnummer: 302-1234567", "", "Monitor 27 Zoll   189,90 EUR", "",
          "Zwischensumme (netto)   159,58 EUR", "USt. 19%   30,32 EUR", "Gesamtbetrag   189,90 EUR", "Bezahlt mit Visa"])
text_pdf("db_deutschlandticket_2026-07.pdf", "Deutsche Bahn - Deutschlandticket",
         ["Rechnungsdatum: 02.07.2026", "Gueltig: Juli 2026", "Preis 63,00 EUR", "enthaltene MwSt 7%: 4,12 EUR",
          "Zahlung: Lastschrift"])

open(os.path.join(out, "udemy_2026-08-14.eml"), "w", encoding="utf-8").write(
"""From: Udemy <receipts@udemy.example>
To: max@example.com
Date: Fri, 14 Aug 2026 10:02:00 +0200
Subject: Your Udemy receipt
Content-Type: text/plain; charset=utf-8

Receipt - 14 Aug 2026
Python for Data Analysis (course)        19,99 EUR
VAT 19% included                          3,19 EUR
Total                                    19,99 EUR
Paid with Mastercard ending 4242
""")
print(sorted(os.listdir(out)))
