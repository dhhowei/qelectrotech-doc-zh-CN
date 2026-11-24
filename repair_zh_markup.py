#!/usr/bin/env python3
"""Retranslate catalog entries cited by Sphinx markup warnings."""

from pathlib import Path
import re

import polib

from translate_fallback import translate_markup_safe
from translate_zh_cn import (
    ArgosBatchTranslator,
    CACHE_PATH,
    LOCALE_DIR,
    load_cache,
    normalize_references,
    postprocess,
    save_cache,
)

ROOT = Path(__file__).resolve().parent
LOG = ROOT / "build" / "sphinx-zh_CN.log"
warning_locations = set()
for line in LOG.read_text(encoding="utf-8").splitlines():
    if "WARNING" not in line:
        continue
    match = re.search(r"source[\\/](.+?\.rst):(\d+)", line)
    if match:
        warning_locations.add((match.group(1).replace("\\", "/"), match.group(2)))

files = sorted(LOCALE_DIR.rglob("*.po"))
catalogs = [polib.pofile(str(path), encoding="utf-8") for path in files]
entries_by_id = {}
messages = set()
for catalog in catalogs:
    for entry in catalog:
        if not entry.msgid or entry.obsolete:
            continue
        entries_by_id.setdefault(entry.msgid, []).append(entry)
        for source, line in entry.occurrences:
            source = source.replace("\\", "/")
            source = source.split("source/", 1)[-1]
            if (source, line) in warning_locations:
                messages.add(entry.msgid)

print(f"Repairing {len(messages)} messages cited by {len(warning_locations)} warning locations.")
if messages:
    ordered = sorted(messages)
    translator = ArgosBatchTranslator()
    translated = translate_markup_safe(ordered, translator, postprocess)
    cache = load_cache()
    for msgid, msgstr in zip(ordered, translated):
        cache[msgid] = normalize_references(msgid, msgstr)
        for entry in entries_by_id[msgid]:
            entry.msgstr = cache[msgid]
    save_cache(cache)
for catalog in catalogs:
    catalog.save()
print("Markup-safe translations written to the Chinese catalogs.")
