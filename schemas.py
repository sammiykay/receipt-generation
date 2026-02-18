from __future__ import annotations

from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from pydantic import BaseModel, ConfigDict, Field, field_validator


def cents_to_currency(cents: int) -> str:
    return f"{Decimal(cents) / Decimal(100):,.2f}"


def normalize_amount_to_cents(value: str | float | int | Decimal) -> int:
    try:
        dec = Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError):
        raise ValueError("Amount must be numeric")

    if dec < 0:
        raise ValueError("Amount cannot be negative")
    return int(dec * 100)


class ReceiptItemCreate(BaseModel):
    item_name: str = Field(min_length=1, max_length=200)
    amount: str

    @field_validator("item_name")
    @classmethod
    def validate_item_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Item name is required")
        return value

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, value: str) -> str:
        normalize_amount_to_cents(value)
        return value


class ReceiptCreate(BaseModel):
    student_name: str = Field(min_length=1, max_length=200)
    student_class: str = Field(min_length=1, max_length=120)
    department: str = Field(default="", max_length=200)
    items: list[ReceiptItemCreate] = Field(min_length=1)

    @field_validator("student_name", "student_class", mode="before")
    @classmethod
    def strip_required(cls, value: str) -> str:
        if not isinstance(value, str):
            raise ValueError("Invalid value")
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Required field")
        return cleaned

    @field_validator("department", mode="before")
    @classmethod
    def strip_optional(cls, value: str | None) -> str:
        return (value or "").strip()


class ReceiptItemOut(BaseModel):
    id: int
    item_name: str
    amount_cents: int
    amount: str

    model_config = ConfigDict(from_attributes=True)


class ReceiptOut(BaseModel):
    id: int
    receipt_number: str
    student_name: str
    student_class: str
    department: str
    total_cents: int
    total: str
    created_at: datetime
    pdf_path: str
    items: list[ReceiptItemOut]

    model_config = ConfigDict(from_attributes=True)


class ReceiptListOut(BaseModel):
    id: int
    receipt_number: str
    student_name: str
    student_class: str
    total_cents: int
    total: str
    created_at: datetime
    pdf_exists: bool


class SettingsIn(BaseModel):
    school_name: str = Field(min_length=1, max_length=200)
    school_address: str = Field(default="", max_length=300)
    school_contact: str = Field(default="", max_length=200)
    currency_symbol: str = Field(default="₦", min_length=1, max_length=3)
    footer_text: str = Field(default="", max_length=250)
    default_pdf_folder: str = Field(default="", max_length=500)

    @field_validator("school_name")
    @classmethod
    def validate_school_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("School name is required")
        return value

    @field_validator(
        "school_address",
        "school_contact",
        "currency_symbol",
        "footer_text",
        "default_pdf_folder",
    )
    @classmethod
    def trim_strings(cls, value: str) -> str:
        return value.strip()


class SettingsOut(SettingsIn):
    id: int

    model_config = ConfigDict(from_attributes=True)
