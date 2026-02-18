# Offline Receipt Generator (FastAPI + SQLite + ReportLab)

Desktop-style offline receipt app built with Python and FastAPI, served locally on `127.0.0.1` and packaged into a single executable with PyInstaller.

## Features

- Fully offline local web app
- Auto-opens default browser when executable starts
- SQLite database in writable app-data folder
- Dynamic expense rows with inline validation and realtime totals
- Sequential yearly receipt numbers (`RCPT-YYYY-0001`)
- A4 PDF generation via ReportLab
- Receipt history with search/filter/date range
- Receipt details, PDF open/re-generate, JSON export, delete
- Editable settings (school header/footer/default PDF folder)
- Modern responsive UI (no external CDN)
- Error logging to local app-data log file

## Project Structure

- `main.py`: FastAPI app, routes, startup, local runner
- `db.py`: SQLAlchemy engine/session/base
- `models.py`: ORM models
- `schemas.py`: Pydantic validation/serialization
- `crud.py`: data access and transactional logic
- `services/pdf.py`: PDF generation
- `services/paths.py`: app-data/resource/static paths
- `static/index.html`: UI shell
- `static/css/styles.css`: styling
- `static/js/app.js`: frontend behavior
- `run.py`: executable entrypoint
- `receipt_generator.spec`: PyInstaller onefile spec
- `build_windows.ps1`, `build.sh`: build scripts

## Local Development

1. Create venv and install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

2. Run app from this directory:

```bash
python run.py
```

Alternative direct run:

```bash
python main.py
```

The app starts on `127.0.0.1` with an available random port and opens your browser.

## Data and Logs Location

- Windows: `%APPDATA%\ReceiptGenerator\`
- Linux: `~/.local/share/ReceiptGenerator/`

Subfolders:
- `data/receipts.db` (SQLite)
- `pdfs/` (default generated PDFs)
- `logs/app.log`

## DB / Migrations Approach

This project uses a simple startup migration strategy:
- `Base.metadata.create_all(engine)` runs on startup.
- Default settings row is auto-created if missing.

For larger projects, move to Alembic later.

## Build Single Executable

### Windows (PowerShell)

```powershell
./build_windows.ps1
```

Output:
- `dist/ReceiptGenerator.exe`

### Linux/macOS

```bash
./build.sh
```

Output:
- `dist/ReceiptGenerator`

## Runtime Behavior in EXE

On double-click:
1. Picks a free local port on `127.0.0.1`
2. Starts uvicorn programmatically
3. Opens default browser automatically
4. Operates fully offline using bundled static assets and local SQLite

## Short Test Plan (Edge Cases)

1. Form validation:
- Empty student name/class blocked.
- Empty item name blocked.
- Negative amount blocked.
- Non-numeric amount blocked.

2. Total correctness:
- Multiple rows with decimals should match PDF total exactly.
- Zero-value items allowed and included.

3. Receipt numbering:
- Generate multiple receipts and verify sequential number increments.
- Verify new year starts at `0001` (simulate by DB counter setup).

4. History/filtering:
- Search by student/class/receipt number.
- Date range includes expected records and excludes others.

5. PDF resilience:
- Delete a PDF file manually, then use `View PDF` or `Re-generate`.

6. Settings:
- Update school header/footer and confirm changes in newly generated PDF.

7. Delete flow:
- Confirm modal appears.
- Record removed from history.
- PDF removed from disk when present.

8. Packaging:
- Run built onefile executable without internet.
- Browser opens automatically and all pages/actions still work.
