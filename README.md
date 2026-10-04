# Hakzaa (הקצאה)

A local check for Israeli freelancers and businesses whose customers refuse invoices that lack a מספר הקצאה (allocation number). It is for invoices issued in software that is **not** connected to the Tax Authority, plus a walkthrough of the retroactive request **as described by the sources below**.

It is not a billing system.

**This app does not submit anything to the Israel Tax Authority.** It does not call the Authority, does not open a session with it, and does not pretend to request or receive an allocation number. Marking a number as received only stores what you type into the local SQLite file.

## How to run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:5000 . The UI is Hebrew, right-to-left.

Invoices are stored in `data/hakzaa.sqlite` and remain after a restart. Override the path with `HAKZAA_DB=/path/to/file.sqlite` if needed.

Tests (temporary database, not the app file):

```bash
python -m unittest discover -s tests -v
```

## Threshold

Used for invoices dated **on or after 1 June 2026**:

> עולה על 5,000 ש"ח (לפני מע"מ)

An invoice is flagged only when the amount **before VAT is strictly above 5,000 NIS** and no allocation number is stored. 5,000 itself is not above the threshold. 6,000 with no number is flagged. 4,000 is not. 6,000 that already has a number is not flagged.

Sources, which agree with each other and with the research note (from June 2026, above 5,000 NIS before VAT; clients say «אין מספר הקצאה»; without the number the client often will not pay because input VAT cannot be deducted):

- Invoice4U, רו"ח מיכאל גנדלר, 09.05.2026, [חשבונית ללא מספר הקצאה](https://www.invoice4u.co.il/blog/%D7%97%D7%A9%D7%91%D7%95%D7%A0%D7%99%D7%AA-%D7%9C%D7%9C%D7%90-%D7%9E%D7%A1%D7%A4%D7%A8-%D7%94%D7%A7%D7%A6%D7%90%D7%94/): «נכון ל-2026, מדובר על 10,000 ₪, וביוני 2026 הרף צפוי לרדת ל־5,000 ₪.» FAQ: «5,000 ש"ח החל מיוני 2026». The amount is before VAT. The article says the June drop is *expected* («צפוי»).
- Grant Thornton Israel, אסף בהר, 25 May 2026, [מה- 1 ביוני חובת מספר הקצאה מעל 5,000 ש"ח](https://www.grantthornton.co.il/insights1/tax-insignths/2026/From_June_the_allocation_number/): «החל מיום 1.6.2026 תורחב החובה לקבל מספר הקצאה לחשבונית מס, כך שתחול על עסקאות שסכומן עולה על 5,000 ש"ח (לפני מע"מ).» This page states the start date as 1.6.2026 rather than only «June», and it does not use the word «expected».

**The Invoice4U article does not link to Grant Thornton.** The Grant Thornton note was fetched because it is the Israel page that states the same June 2026 figure the article uses. Nothing on either page contradicts the research note.

For invoices dated **1 January 2026 through 31 May 2026**, Invoice4U's «נכון ל-2026 … 10,000 ₪» is applied: flagged only when the amount before VAT is **above 10,000 NIS** and there is no allocation number. Grant Thornton's fetched page does not restate that earlier 2026 figure; it only sets the 5,000 NIS rule from 1.6.2026.

For invoices dated **before 2026**, neither fetched page states a threshold, so those invoices are **not** auto-flagged.

The pages also say a zero-rate invoice, or one that contains only exempt transactions, does not need an allocation number even if the amount is high. Hakzaa still flags on threshold plus a missing number only. If VAT was entered as 0, the flagged card shows that caveat instead of hiding the invoice.

## Retroactive steps shown in the app

Taken from Invoice4U («איך מקבלים מספר הקצאה לחשבונית קיימת?» and the practical section). The invoice's own number, date, customer, amount before VAT, and VAT are filled into the data-entry step. They are not a click-path invented here, and the app does not carry them out:

1. «יש להיכנס לאזור האישי באתר רשות המיסים ולהתחבר עם פרטי הזיהוי שלכם.»
2. «לאחר מכן, יש לבחור בשירות "חשבוניות ישראל".»
3. «בשלב הבא, מזינים את פרטי החשבונית – מספר, תאריך, פרטי לקוח וסכום מדויק.»
4. «המערכת תבדוק את הנתונים ובמידה והכול תקין, תנפיק מספר הקצאה.»
5. «ניתן להגיש בקשה גם רטרואקטיבית, אך זה תלוי בהנחיות רשות המיסים ובחלון הזמן שמוגדר במערכת.»
6. «במקרים מסוימים, ייתכן שתידרשו להנפיק חשבונית חדשה או לבצע תיקון במסמך.»
7. «אם לא הגדרתם מראש מורשה לקבלת מספרי הקצאה, לא תוכלו לבצע את הפעולה.»

Grant Thornton adds that the Authority's own web application asks for the document number, the customer's עוסק/ח.פ number, the amount before VAT, the VAT amount, and the date. Hakzaa does not collect a ח.פ, and it says so on the card. It does not describe the rejection, hearing, or appeal procedure, because that is not the retroactive request for an invoice that simply never received a number.
