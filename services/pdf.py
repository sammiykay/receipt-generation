from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from app import models
from app.services.paths import ensure_app_dirs


def _resolve_pdf_folder(settings: models.Setting | None) -> Path:
    paths = ensure_app_dirs()
    if settings and settings.default_pdf_folder:
        folder = Path(settings.default_pdf_folder)
    else:
        folder = paths["pdf_dir"]
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def generate_receipt_pdf(receipt: models.Receipt, settings: models.Setting | None) -> Path:
    folder = _resolve_pdf_folder(settings)
    safe_receipt_no = receipt.receipt_number.replace("/", "-").replace(" ", "")
    filepath = folder / f"{safe_receipt_no}.pdf"

    c = canvas.Canvas(str(filepath), pagesize=A4)
    width, height = A4

    margin_x = 20 * mm
    y = height - 20 * mm

    school_name = settings.school_name if settings else "My School"
    school_address = settings.school_address if settings else ""
    school_contact = settings.school_contact if settings else ""
    currency_symbol = settings.currency_symbol if settings and settings.currency_symbol else "₦"
    footer_text = settings.footer_text if settings else "Thank you for your payment."

    c.setFillColor(colors.HexColor("#0f172a"))
    c.setFont("Helvetica-Bold", 18)
    c.drawString(margin_x, y, school_name)

    y -= 8 * mm
    c.setFont("Helvetica", 10)
    if school_address:
        c.setFillColor(colors.HexColor("#334155"))
        c.drawString(margin_x, y, school_address)
        y -= 5 * mm
    if school_contact:
        c.drawString(margin_x, y, school_contact)
        y -= 7 * mm

    c.setStrokeColor(colors.HexColor("#cbd5e1"))
    c.line(margin_x, y, width - margin_x, y)
    y -= 10 * mm

    c.setFillColor(colors.HexColor("#0f172a"))
    c.setFont("Helvetica-Bold", 14)
    c.drawString(margin_x, y, "Payment Receipt")

    c.setFont("Helvetica", 10)
    issue_date = receipt.created_at.strftime("%Y-%m-%d %H:%M")
    c.drawRightString(width - margin_x, y, f"Receipt No: {receipt.receipt_number}")
    y -= 6 * mm
    c.drawRightString(width - margin_x, y, f"Date: {issue_date}")
    y -= 10 * mm

    c.setFont("Helvetica-Bold", 10)
    c.drawString(margin_x, y, "Student Information")
    y -= 6 * mm

    c.setFont("Helvetica", 10)
    c.drawString(margin_x, y, f"Name: {receipt.student_name}")
    y -= 5.5 * mm
    c.drawString(margin_x, y, f"Class: {receipt.student_class}")
    y -= 5.5 * mm
    c.drawString(margin_x, y, f"Department: {receipt.department or '-'}")
    y -= 10 * mm

    table_left = margin_x
    table_right = width - margin_x
    item_col_end = width - 50 * mm

    c.setFillColor(colors.HexColor("#e2e8f0"))
    c.rect(table_left, y - 6 * mm, table_right - table_left, 8 * mm, fill=1, stroke=0)

    c.setFillColor(colors.HexColor("#0f172a"))
    c.setFont("Helvetica-Bold", 10)
    c.drawString(table_left + 4, y - 2 * mm, "Item")
    c.drawRightString(table_right - 4, y - 2 * mm, "Amount")

    y -= 10 * mm
    c.setFont("Helvetica", 10)

    for item in receipt.items:
        if y <= 35 * mm:
            c.showPage()
            y = height - 20 * mm
        c.setFillColor(colors.HexColor("#111827"))
        c.drawString(table_left + 4, y, item.item_name)
        amount = f"{currency_symbol}{item.amount_cents / 100:,.2f}"
        c.drawRightString(table_right - 4, y, amount)

        c.setStrokeColor(colors.HexColor("#e5e7eb"))
        c.line(table_left, y - 2.5 * mm, table_right, y - 2.5 * mm)
        y -= 7 * mm

    y -= 1 * mm
    c.setFont("Helvetica-Bold", 11)
    c.setFillColor(colors.HexColor("#0f172a"))
    c.drawString(table_left + 4, y, "Total")
    c.drawRightString(table_right - 4, y, f"{currency_symbol}{receipt.total_cents / 100:,.2f}")

    y -= 12 * mm
    c.setFont("Helvetica", 9)
    c.setFillColor(colors.HexColor("#475569"))
    c.drawString(margin_x, y, footer_text)

    c.save()
    return filepath
