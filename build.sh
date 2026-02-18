#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt

pyinstaller --clean --noconfirm receipt_generator.spec

echo "Build complete. Executable in dist/ReceiptGenerator"
