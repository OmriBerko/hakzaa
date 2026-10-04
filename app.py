"""Hakzaa: local check for invoices missing a מספר הקצאה.

Does not call, submit to, or speak for the Israel Tax Authority.
"""

import os
import sqlite3
from datetime import date

from flask import Flask, g, redirect, render_template, request, url_for

from logic import (
    GRANT_THORNTON_URL,
    INVOICE4U_URL,
    THRESHOLD_LABEL,
    _display_date,
    _nis,
    is_flagged,
    retroactive_steps,
    threshold_for,
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DB = os.path.join(BASE_DIR, "data", "hakzaa.sqlite")


def create_app(db_path=None):
    app = Flask(__name__)
    app.config["DATABASE"] = db_path or os.environ.get("HAKZAA_DB") or DEFAULT_DB

    @app.before_request
    def _open_db():
        g.db = _connect(app.config["DATABASE"])

    @app.teardown_request
    def _close_db(_exc):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    @app.get("/")
    def index():
        rows = _all_invoices()
        prepared = [_present(row) for row in rows]
        flagged = [item for item in prepared if item["flagged"]]
        cleared = [item for item in prepared if item["cleared"]]
        summary = {
            "flagged_count": len(flagged),
            "cleared_count": len(cleared),
            "flagged_sum": sum(item["amount_before_vat"] for item in flagged),
        }
        return render_template(
            "index.html",
            invoices=prepared,
            flagged=flagged,
            cleared=cleared,
            summary=summary,
            threshold_label=THRESHOLD_LABEL,
            invoice4u_url=INVOICE4U_URL,
            grant_thornton_url=GRANT_THORNTON_URL,
            today=date.today().isoformat(),
            error=request.args.get("error"),
        )

    @app.post("/invoices")
    def add_invoice():
        try:
            payload = _parse_form(request.form)
        except ValueError as exc:
            return redirect(url_for("index", error=str(exc)))
        g.db.execute(
            """
            INSERT INTO invoices (
                invoice_date, customer_name, amount_before_vat, vat_amount,
                invoice_number, allocation_number
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                payload["invoice_date"],
                payload["customer_name"],
                payload["amount_before_vat"],
                payload["vat_amount"],
                payload["invoice_number"],
                payload["allocation_number"],
            ),
        )
        g.db.commit()
        return redirect(url_for("index"))

    @app.post("/invoices/<int:invoice_id>/received")
    def mark_received(invoice_id):
        number = (request.form.get("allocation_number") or "").strip()
        if not number:
            return redirect(url_for("index", error="חסר מספר הקצאה"))
        row = g.db.execute(
            "SELECT * FROM invoices WHERE id = ?", (invoice_id,)
        ).fetchone()
        if row is None:
            return redirect(url_for("index", error="החשבונית לא נמצאה"))
        if not is_flagged(row["invoice_date"], row["amount_before_vat"], row["allocation_number"]):
            return redirect(url_for("index", error="החשבונית אינה ברשימת החסרים"))
        g.db.execute(
            "UPDATE invoices SET allocation_number = ? WHERE id = ?",
            (number, invoice_id),
        )
        g.db.commit()
        return redirect(url_for("index"))

    with app.app_context():
        db = _connect(app.config["DATABASE"])
        try:
            _init_db(db)
        finally:
            db.close()

    return app


def _connect(path):
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def _init_db(conn):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_date TEXT NOT NULL,
            customer_name TEXT NOT NULL,
            amount_before_vat REAL NOT NULL,
            vat_amount REAL NOT NULL,
            invoice_number TEXT,
            allocation_number TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    conn.commit()


def _all_invoices():
    return g.db.execute(
        "SELECT * FROM invoices ORDER BY invoice_date DESC, id DESC"
    ).fetchall()


def _present(row):
    item = dict(row)
    number = (item.get("allocation_number") or "").strip()
    item["allocation_number"] = number
    item["flagged"] = is_flagged(
        item["invoice_date"], item["amount_before_vat"], number
    )
    _limit, label = threshold_for(item["invoice_date"])
    item["threshold_note"] = label
    item["cleared"] = (not item["flagged"]) and bool(number) and _over_without_number(item)
    item["steps"] = retroactive_steps(item) if item["flagged"] else []
    item["zero_vat_caveat"] = item["flagged"] and float(item["vat_amount"]) == 0
    item["date_display"] = _display_date(item["invoice_date"])
    item["amount_display"] = _nis(item["amount_before_vat"])
    item["vat_display"] = _nis(item["vat_amount"])
    return item


def _over_without_number(item):
    return is_flagged(item["invoice_date"], item["amount_before_vat"], "")


def _parse_form(form):
    invoice_date = (form.get("invoice_date") or "").strip()
    customer = (form.get("customer_name") or "").strip()
    invoice_number = (form.get("invoice_number") or "").strip() or None
    already = form.get("has_allocation") == "yes"
    allocation = (form.get("allocation_number") or "").strip()
    if not invoice_date:
        raise ValueError("חסר תאריך")
    try:
        date.fromisoformat(invoice_date)
    except ValueError as exc:
        raise ValueError("תאריך לא תקין") from exc
    if not customer:
        raise ValueError("חסר שם לקוח")
    try:
        amount = float(form.get("amount_before_vat") or "")
        vat = float(form.get("vat_amount") or "")
    except ValueError as exc:
        raise ValueError("סכום לא תקין") from exc
    if amount < 0 or vat < 0:
        raise ValueError("סכום לא יכול להיות שלילי")
    if already and not allocation:
        raise ValueError("סומן שיש מספר הקצאה, אבל המספר לא הוזן")
    if not already:
        allocation = ""
    return {
        "invoice_date": invoice_date,
        "customer_name": customer,
        "amount_before_vat": amount,
        "vat_amount": vat,
        "invoice_number": invoice_number,
        "allocation_number": allocation or None,
    }


app = create_app()


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
