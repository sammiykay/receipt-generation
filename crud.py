from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import and_, or_, select, text
from sqlalchemy.orm import Session, joinedload

from app import models, schemas
from app.services.paths import ensure_app_dirs


def init_db_defaults(db: Session) -> None:
    ensure_settings_schema(db)
    setting = db.get(models.Setting, 1)
    if not setting:
        paths = ensure_app_dirs()
        setting = models.Setting(
            id=1,
            default_pdf_folder=str(paths["pdf_dir"]),
            currency_symbol="₦",
        )
        db.add(setting)
        db.commit()
    elif not setting.currency_symbol:
        setting.currency_symbol = "₦"
        db.add(setting)
        db.commit()


def ensure_settings_schema(db: Session) -> None:
    table_info = db.execute(text("PRAGMA table_info(settings)")).mappings().all()
    existing_cols = {row["name"] for row in table_info}
    if "currency_symbol" not in existing_cols:
        db.execute(
            text(
                "ALTER TABLE settings ADD COLUMN currency_symbol VARCHAR(8) DEFAULT '₦'"
            )
        )
        db.commit()


def get_or_create_settings(db: Session) -> models.Setting:
    setting = db.get(models.Setting, 1)
    if setting:
        if not setting.currency_symbol:
            setting.currency_symbol = "₦"
            db.add(setting)
            db.commit()
            db.refresh(setting)
        return setting
    paths = ensure_app_dirs()
    setting = models.Setting(
        id=1,
        default_pdf_folder=str(paths["pdf_dir"]),
        currency_symbol="₦",
    )
    db.add(setting)
    db.commit()
    db.refresh(setting)
    return setting


def update_settings(db: Session, payload: schemas.SettingsIn) -> models.Setting:
    setting = get_or_create_settings(db)
    for field, value in payload.model_dump().items():
        setattr(setting, field, value)
    setting.updated_at = datetime.utcnow()
    db.add(setting)
    db.commit()
    db.refresh(setting)
    return setting


def _next_receipt_number(db: Session, year: int) -> str:
    counter = db.get(models.ReceiptCounter, year)
    if not counter:
        counter = models.ReceiptCounter(year=year, last_number=0)
        db.add(counter)
        db.flush()
    counter.last_number += 1
    db.add(counter)
    db.flush()
    return f"RCPT-{year}-{counter.last_number:04d}"


def create_receipt(db: Session, payload: schemas.ReceiptCreate) -> models.Receipt:
    created_at = datetime.now()
    year = created_at.year

    item_rows: list[dict[str, Any]] = []
    total_cents = 0
    for item in payload.items:
        cents = schemas.normalize_amount_to_cents(item.amount)
        total_cents += cents
        item_rows.append({"item_name": item.item_name.strip(), "amount_cents": cents})

    with db.begin():
        receipt_number = _next_receipt_number(db, year)
        receipt = models.Receipt(
            receipt_number=receipt_number,
            student_name=payload.student_name,
            student_class=payload.student_class,
            department=payload.department,
            total_cents=total_cents,
            created_at=created_at,
        )
        db.add(receipt)
        db.flush()

        for row in item_rows:
            db.add(models.ReceiptItem(receipt_id=receipt.id, **row))

    db.refresh(receipt)
    return get_receipt_or_404(db, receipt.id)


def get_receipt_or_404(db: Session, receipt_id: int) -> models.Receipt:
    stmt = (
        select(models.Receipt)
        .options(joinedload(models.Receipt.items))
        .where(models.Receipt.id == receipt_id)
    )
    receipt = db.execute(stmt).unique().scalar_one_or_none()
    if not receipt:
        raise ValueError("Receipt not found")
    return receipt


def list_receipts(
    db: Session,
    search: str | None,
    date_from: str | None,
    date_to: str | None,
) -> list[models.Receipt]:
    stmt = select(models.Receipt).order_by(models.Receipt.created_at.desc())

    conditions = []
    if search:
        q = f"%{search.strip()}%"
        conditions.append(
            or_(
                models.Receipt.student_name.ilike(q),
                models.Receipt.student_class.ilike(q),
                models.Receipt.receipt_number.ilike(q),
            )
        )

    if date_from:
        from_dt = datetime.fromisoformat(f"{date_from}T00:00:00")
        conditions.append(models.Receipt.created_at >= from_dt)
    if date_to:
        to_dt = datetime.fromisoformat(f"{date_to}T23:59:59")
        conditions.append(models.Receipt.created_at <= to_dt)

    if conditions:
        stmt = stmt.where(and_(*conditions))

    return list(db.scalars(stmt).all())


def delete_receipt(db: Session, receipt_id: int) -> None:
    receipt = db.get(models.Receipt, receipt_id)
    if not receipt:
        raise ValueError("Receipt not found")

    pdf_path = receipt.pdf_path
    db.delete(receipt)
    db.commit()

    if pdf_path:
        path = Path(pdf_path)
        if path.exists():
            path.unlink(missing_ok=True)


def as_receipt_out(receipt: models.Receipt) -> schemas.ReceiptOut:
    items = [
        schemas.ReceiptItemOut(
            id=item.id,
            item_name=item.item_name,
            amount_cents=item.amount_cents,
            amount=schemas.cents_to_currency(item.amount_cents),
        )
        for item in receipt.items
    ]
    return schemas.ReceiptOut(
        id=receipt.id,
        receipt_number=receipt.receipt_number,
        student_name=receipt.student_name,
        student_class=receipt.student_class,
        department=receipt.department,
        total_cents=receipt.total_cents,
        total=schemas.cents_to_currency(receipt.total_cents),
        created_at=receipt.created_at,
        pdf_path=receipt.pdf_path,
        items=items,
    )


def as_receipt_list_out(receipt: models.Receipt) -> schemas.ReceiptListOut:
    pdf_exists = bool(receipt.pdf_path and Path(receipt.pdf_path).exists())
    return schemas.ReceiptListOut(
        id=receipt.id,
        receipt_number=receipt.receipt_number,
        student_name=receipt.student_name,
        student_class=receipt.student_class,
        total_cents=receipt.total_cents,
        total=schemas.cents_to_currency(receipt.total_cents),
        created_at=receipt.created_at,
        pdf_exists=pdf_exists,
    )


def export_receipt_json(receipt: models.Receipt) -> dict[str, Any]:
    return {
        "id": receipt.id,
        "receipt_number": receipt.receipt_number,
        "student_name": receipt.student_name,
        "student_class": receipt.student_class,
        "department": receipt.department,
        "created_at": receipt.created_at.isoformat(),
        "total": schemas.cents_to_currency(receipt.total_cents),
        "items": [
            {
                "item_name": item.item_name,
                "amount": schemas.cents_to_currency(item.amount_cents),
            }
            for item in receipt.items
        ],
    }
