from __future__ import annotations

import logging
import socket
import sys
import threading
import webbrowser
from pathlib import Path

# Allow running directly from the app directory: `cd app && python main.py`
if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parents[1]))

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from app import crud, schemas
from app.db import Base, SessionLocal, engine, get_db
from app.services.paths import ensure_app_dirs, static_dir
from app.services.pdf import generate_receipt_pdf

paths = ensure_app_dirs()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(paths["log_path"], encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("receipt_app")

app = FastAPI(title="Offline Receipt Generator", docs_url=None, redoc_url=None)


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        crud.ensure_settings_schema(db)
        crud.init_db_defaults(db)
    finally:
        db.close()
    logger.info("Application startup complete")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/settings", response_model=schemas.SettingsOut)
def get_settings(db: Session = Depends(get_db)):
    return crud.get_or_create_settings(db)


@app.put("/api/settings", response_model=schemas.SettingsOut)
def update_settings(payload: schemas.SettingsIn, db: Session = Depends(get_db)):
    return crud.update_settings(db, payload)


@app.post("/api/receipts")
def create_receipt(payload: schemas.ReceiptCreate, db: Session = Depends(get_db)):
    try:
        receipt = crud.create_receipt(db, payload)
        settings = crud.get_or_create_settings(db)
        pdf_path = generate_receipt_pdf(receipt, settings)
        receipt.pdf_path = str(pdf_path)
        db.add(receipt)
        db.commit()
        db.refresh(receipt)
        return {
            "message": "Receipt generated successfully",
            "receipt": crud.as_receipt_out(receipt),
            "pdf_url": f"/api/receipts/{receipt.id}/pdf",
        }
    except ValueError as exc:
        logger.exception("Validation error while creating receipt")
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Failed to create receipt")
        raise HTTPException(status_code=500, detail="Could not generate receipt") from exc


@app.get("/api/receipts")
def list_receipts(
    search: str | None = Query(default=None),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    try:
        receipts = crud.list_receipts(db, search=search, date_from=date_from, date_to=date_to)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return [crud.as_receipt_list_out(receipt) for receipt in receipts]


@app.get("/api/receipts/{receipt_id}")
def get_receipt(receipt_id: int, db: Session = Depends(get_db)):
    try:
        receipt = crud.get_receipt_or_404(db, receipt_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return crud.as_receipt_out(receipt)


@app.delete("/api/receipts/{receipt_id}")
def delete_receipt(receipt_id: int, db: Session = Depends(get_db)):
    try:
        crud.delete_receipt(db, receipt_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Failed to delete receipt %s", receipt_id)
        raise HTTPException(status_code=500, detail="Failed to delete receipt") from exc
    return {"message": "Receipt deleted"}


@app.post("/api/receipts/{receipt_id}/regenerate")
def regenerate_pdf(receipt_id: int, db: Session = Depends(get_db)):
    try:
        receipt = crud.get_receipt_or_404(db, receipt_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    settings = crud.get_or_create_settings(db)
    pdf_path = generate_receipt_pdf(receipt, settings)
    receipt.pdf_path = str(pdf_path)
    db.add(receipt)
    db.commit()
    return {"message": "PDF regenerated", "pdf_url": f"/api/receipts/{receipt.id}/pdf"}


@app.get("/api/receipts/{receipt_id}/pdf")
def get_pdf(receipt_id: int, db: Session = Depends(get_db)):
    try:
        receipt = crud.get_receipt_or_404(db, receipt_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    pdf_path = Path(receipt.pdf_path) if receipt.pdf_path else None
    if not pdf_path or not pdf_path.exists():
        settings = crud.get_or_create_settings(db)
        pdf_path = generate_receipt_pdf(receipt, settings)
        receipt.pdf_path = str(pdf_path)
        db.add(receipt)
        db.commit()

    return FileResponse(
        path=pdf_path,
        media_type="application/pdf",
        filename=f"{receipt.receipt_number}.pdf",
    )


@app.get("/api/receipts/{receipt_id}/export")
def export_receipt(receipt_id: int, db: Session = Depends(get_db)):
    try:
        receipt = crud.get_receipt_or_404(db, receipt_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return JSONResponse(content=crud.export_receipt_json(receipt))


def find_free_port(host: str = "127.0.0.1") -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((host, 0))
        return int(sock.getsockname()[1])


def launch_browser(url: str) -> None:
    def _open():
        try:
            webbrowser.open(url)
        except Exception:
            logger.exception("Failed to open browser")

    threading.Timer(1.0, _open).start()


def run_app() -> None:
    host = "127.0.0.1"
    port = find_free_port(host)
    url = f"http://{host}:{port}"
    logger.info("Starting server at %s", url)
    launch_browser(url)

    config = uvicorn.Config(app=app, host=host, port=port, log_level="info")
    server = uvicorn.Server(config)

    try:
        server.run()
    except KeyboardInterrupt:
        logger.info("Server shutdown requested")
    except Exception:
        logger.exception("Fatal server error")


app.mount("/", StaticFiles(directory=static_dir(), html=True), name="static")


if __name__ == "__main__":
    run_app()
