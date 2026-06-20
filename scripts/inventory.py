#!/usr/bin/env python3
"""Inventar des Protokollbestands erstellen — read-only, ohne externe Abhängigkeiten.

Durchläuft den BL-Sitzungen-Ordner und schreibt eine CSV mit einer Zeile je Datei:
erkanntes Sitzungsdatum, Sitzungstyp, Format, ob es ein Protokoll ist, Epoche und
zugehöriger Jahres-/Monatsordner. Grundlage für Phase 1 (gezielte Ingestion der
Protokolle) und für eine erste Mengenabschätzung.

Beispiel:
    python scripts/inventory.py --source "<Pfad zu BL-Sitzungen>" --out data/inventar.csv

Es werden KEINE Dateiinhalte gelesen oder verändert.
"""
from __future__ import annotations

import argparse
import csv
import re
from datetime import date
from pathlib import Path

# YYMMDD am Namensanfang, z. B. "240216 BL PK_Final.pdf" oder "190130_ebl_pk.pdf"
RE_DATE = re.compile(r"\b(\d{2})(\d{2})(\d{2})\b")
PROTOKOLL_HINTS = ("pk", "pl", "protokoll")
DOC_FORMATS = {".pdf", ".docx", ".doc"}


def erkenne_datum(name: str) -> date | None:
    m = RE_DATE.search(name)
    if not m:
        return None
    yy, mm, dd = (int(g) for g in m.groups())
    jahr = 2000 + yy
    try:
        return date(jahr, mm, dd)
    except ValueError:
        return None


def erkenne_typ(text: str) -> str:
    t = text.lower()
    if "ring" in t:
        return "ring_bl"
    if "ao" in t.split() or "außerordentlich" in t or "zusätzlich" in t:
        return "ao_ebl"
    if "ebl" in t:
        return "ebl"
    if "bl" in t:
        return "bl"
    return ""


def ist_protokoll(name: str) -> bool:
    low = name.lower()
    # "TO" (Tagesordnung) ausschließen, Protokoll-Hinweise einschließen
    if " to " in f" {low} " or low.endswith(" to.pdf"):
        return False
    return any(h in low for h in PROTOKOLL_HINTS)


def erkenne_epoche(rel: Path) -> str:
    # Monatsordner der neueren Epoche heißen z. B. "01 Februar" / "01_Februar"
    for teil in rel.parts:
        if re.match(r"^\d{2}[ _]", teil):
            return "monatsordner_2021ff"
    return "flach_2014_2020"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source", required=True, help="Pfad zum BL-Sitzungen-Ordner")
    ap.add_argument("--out", default="data/inventar.csv", help="Ziel-CSV")
    args = ap.parse_args()

    src = Path(args.source)
    if not src.is_dir():
        raise SystemExit(f"Quelle nicht gefunden: {src}")

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    zeilen = 0
    protokolle = 0
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["pfad", "datei", "format", "jahr", "datum",
                    "sitzungstyp", "ist_protokoll", "epoche"])
        for p in sorted(src.rglob("*")):
            if not p.is_file():
                continue
            ext = p.suffix.lower()
            rel = p.relative_to(src)
            jahr = rel.parts[0] if rel.parts and rel.parts[0].isdigit() else ""
            d = erkenne_datum(p.name)
            kontext = f"{rel.parent.name} {p.name}"
            proto = ext in DOC_FORMATS and ist_protokoll(p.name)
            w.writerow([
                str(rel.parent), p.name, ext.lstrip("."), jahr,
                d.isoformat() if d else "",
                erkenne_typ(kontext), "ja" if proto else "nein",
                erkenne_epoche(rel),
            ])
            zeilen += 1
            protokolle += int(proto)

    print(f"Inventar geschrieben: {out}  ({zeilen} Dateien, davon {protokolle} mutmaßliche Protokolle)")


if __name__ == "__main__":
    main()
