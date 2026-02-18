from __future__ import annotations

import os
import sys
from pathlib import Path

APP_NAME = "ReceiptGenerator"


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def app_data_root() -> Path:
    if os.name == "nt":
        base = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
        return Path(base) / APP_NAME
    return Path.home() / ".local" / "share" / APP_NAME


def ensure_app_dirs() -> dict[str, Path]:
    root = app_data_root()
    data_dir = root / "data"
    logs_dir = root / "logs"
    pdf_dir = root / "pdfs"

    for folder in (root, data_dir, logs_dir, pdf_dir):
        folder.mkdir(parents=True, exist_ok=True)

    return {
        "root": root,
        "data_dir": data_dir,
        "logs_dir": logs_dir,
        "pdf_dir": pdf_dir,
        "db_path": data_dir / "receipts.db",
        "log_path": logs_dir / "app.log",
    }


def resource_base_path() -> Path:
    if is_frozen() and hasattr(sys, "_MEIPASS"):
        return Path(getattr(sys, "_MEIPASS"))
    return Path(__file__).resolve().parents[1]


def static_dir() -> Path:
    return resource_base_path() / "static"
