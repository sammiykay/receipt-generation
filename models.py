from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Setting(Base):
    __tablename__ = "settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    school_name: Mapped[str] = mapped_column(String(200), default="My School")
    school_address: Mapped[str] = mapped_column(String(300), default="")
    school_contact: Mapped[str] = mapped_column(String(200), default="")
    currency_symbol: Mapped[str] = mapped_column(String(3), default="₦")
    footer_text: Mapped[str] = mapped_column(
        String(250), default="Thank you for your payment."
    )
    default_pdf_folder: Mapped[str] = mapped_column(String(500), default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ReceiptCounter(Base):
    __tablename__ = "receipt_counters"

    year: Mapped[int] = mapped_column(Integer, primary_key=True)
    last_number: Mapped[int] = mapped_column(Integer, default=0)


class Receipt(Base):
    __tablename__ = "receipts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    receipt_number: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    student_name: Mapped[str] = mapped_column(String(200), index=True)
    student_class: Mapped[str] = mapped_column(String(120), index=True)
    department: Mapped[str] = mapped_column(String(200), default="")
    total_cents: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    pdf_path: Mapped[str] = mapped_column(Text, default="")

    items: Mapped[list[ReceiptItem]] = relationship(
        "ReceiptItem", back_populates="receipt", cascade="all, delete-orphan"
    )


class ReceiptItem(Base):
    __tablename__ = "receipt_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    receipt_id: Mapped[int] = mapped_column(ForeignKey("receipts.id", ondelete="CASCADE"))
    item_name: Mapped[str] = mapped_column(String(200))
    amount_cents: Mapped[int] = mapped_column(Integer)

    receipt: Mapped[Receipt] = relationship("Receipt", back_populates="items")
