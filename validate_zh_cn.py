#!/usr/bin/env python3
"""Check Chinese catalog coverage and generated HTML completeness."""

from pathlib import Path
import polib

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "source"
HTML = ROOT / "build" / "html" / "zh_CN"
LOG = ROOT / "build" / "sphinx-zh_CN.log"

source_pages = sorted(SOURCE.rglob("*.rst"))
po_files = sorted((SOURCE / "locale" / "zh_CN" / "LC_MESSAGES").rglob("*.po"))
entries = [entry for path in po_files for entry in polib.pofile(str(path)) if entry.msgid]
untranslated = [entry for entry in entries if not entry.msgstr.strip()]
missing_pages = [
    str(path.relative_to(SOURCE).with_suffix(".html"))
    for path in source_pages
    if not (HTML / path.relative_to(SOURCE).with_suffix(".html")).is_file()
]
log = LOG.read_text(encoding="utf-8")
warning_count = sum(" WARNING:" in line for line in log.splitlines())
error_count = sum(" ERROR:" in line for line in log.splitlines())

print(f"Source pages: {len(source_pages)}")
print(f"Chinese catalogs: {len(po_files)}")
print(f"Catalog entries: {len(entries)}")
print(f"Untranslated entries: {len(untranslated)}")
print(f"Missing HTML pages: {len(missing_pages)}")
print(f"Build warnings: {warning_count}")
print(f"Build errors: {error_count}")

if untranslated or missing_pages or warning_count or error_count:
    raise SystemExit(1)
print("Chinese documentation validation passed.")
