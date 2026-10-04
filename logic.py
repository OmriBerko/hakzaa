"""Threshold and walkthrough text taken only from the fetched sources.

Invoice4U (09.05.2026):
  "נכון ל-2026, מדובר על 10,000 ₪, וביוני 2026 הרף צפוי לרדת ל־5,000 ₪."
  FAQ: "5,000 ש\"ח החל מיוני 2026"
  https://www.invoice4u.co.il/blog/חשבונית-ללא-מספר-הקצאה/

Grant Thornton Israel, Asaf Bahar, 25 May 2026:
  "החל מיום 1.6.2026 תורחב החובה לקבל מספר הקצאה לחשבונית מס,
   כך שתחול על עסקאות שסכומן עולה על 5,000 ש\"ח (לפני מע\"מ)."
  https://www.grantthornton.co.il/insights1/tax-insignths/2026/From_June_the_allocation_number/

The Invoice4U article does not link to Grant Thornton. The two pages agree
on the June 2026 figure (above 5,000 NIS before VAT). Grant Thornton gives
the start date as 1.6.2026; Invoice4U says "from June 2026" and, earlier in
the article, that the drop is "expected". Neither page states a threshold
for invoices dated before 1.1.2026, so those are not auto-flagged.
"""

from datetime import date

INVOICE4U_URL = (
    "https://www.invoice4u.co.il/blog/"
    "%D7%97%D7%A9%D7%91%D7%95%D7%A0%D7%99%D7%AA-%D7%9C%D7%9C%D7%90-"
    "%D7%9E%D7%A1%D7%A4%D7%A8-%D7%94%D7%A7%D7%A6%D7%90%D7%94/"
)
GRANT_THORNTON_URL = (
    "https://www.grantthornton.co.il/insights1/tax-insignths/2026/"
    "From_June_the_allocation_number/"
)

# "עולה על 5,000 ש\"ח (לפני מע\"מ)" — strictly above, from 1.6.2026.
JUNE_2026 = date(2026, 6, 1)
THRESHOLD_FROM_JUNE_2026 = 5000
# Invoice4U: during 2026, before the June drop, the figure given is 10,000 NIS.
YEAR_2026 = date(2026, 1, 1)
THRESHOLD_JAN_MAY_2026 = 10000

THRESHOLD_LABEL = 'עולה על 5,000 ש"ח (לפני מע"מ) החל מ-1.6.2026'


def parse_iso_date(value):
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


def threshold_for(invoice_date):
    """Return (amount_must_exceed, label) or (None, reason) if unsourced."""
    d = parse_iso_date(invoice_date)
    if d >= JUNE_2026:
        return (
            THRESHOLD_FROM_JUNE_2026,
            'מ-1.6.2026: עולה על 5,000 ש"ח לפני מע"מ',
        )
    if d >= YEAR_2026:
        return (
            THRESHOLD_JAN_MAY_2026,
            '1.1.2026 עד 31.5.2026: עולה על 10,000 ש"ח לפני מע"מ (Invoice4U: נכון ל-2026, 10,000 ₪)',
        )
    return (
        None,
        "לפני 2026 המקורות שאוחזרו לא מציינים סף, ולכן אין סימון אוטומטי",
    )


def exceeds_threshold(invoice_date, amount_before_vat):
    limit, _label = threshold_for(invoice_date)
    if limit is None:
        return False
    return float(amount_before_vat) > limit


def is_flagged(invoice_date, amount_before_vat, allocation_number):
    number = (allocation_number or "").strip()
    return exceeds_threshold(invoice_date, amount_before_vat) and not number


def retroactive_steps(invoice):
    """Walkthrough quoted from Invoice4U, with this invoice's figures filled in.

    The page describes the path; this app does not perform it.
    """
    number = (invoice.get("invoice_number") or "").strip() or "לא הוזן באפליקציה"
    customer = invoice["customer_name"]
    when = _display_date(invoice["invoice_date"])
    before = _nis(invoice["amount_before_vat"])
    vat = _nis(invoice["vat_amount"])
    return [
        {
            "quote": "יש להיכנס לאזור האישי באתר רשות המיסים ולהתחבר עם פרטי הזיהוי שלכם.",
            "filled": None,
        },
        {
            "quote": 'לאחר מכן, יש לבחור בשירות "חשבוניות ישראל".',
            "filled": None,
        },
        {
            "quote": "בשלב הבא, מזינים את פרטי החשבונית – מספר, תאריך, פרטי לקוח וסכום מדויק.",
            "filled": (
                f"לחשבונית הזו: מספר {number}, תאריך {when}, "
                f"לקוח {customer}, סכום לפני מע״מ {before}, מע״מ {vat}."
            ),
        },
        {
            "quote": "המערכת תבדוק את הנתונים ובמידה והכול תקין, תנפיק מספר הקצאה.",
            "filled": None,
        },
        {
            "quote": "ניתן להגיש בקשה גם רטרואקטיבית, אך זה תלוי בהנחיות רשות המיסים ובחלון הזמן שמוגדר במערכת.",
            "filled": None,
        },
        {
            "quote": "במקרים מסוימים, ייתכן שתידרשו להנפיק חשבונית חדשה או לבצע תיקון במסמך.",
            "filled": None,
        },
        {
            "quote": "אם לא הגדרתם מראש מורשה לקבלת מספרי הקצאה, לא תוכלו לבצע את הפעולה.",
            "filled": None,
        },
    ]


def _display_date(value):
    d = parse_iso_date(value)
    return d.strftime("%d.%m.%Y")


def _nis(amount):
    value = float(amount)
    sign = "-" if value < 0 else ""
    whole, frac = f"{abs(value):.2f}".split(".")
    groups = []
    while whole:
        groups.append(whole[-3:])
        whole = whole[:-3]
    return f"{sign}{','.join(reversed(groups))}.{frac} ₪"
