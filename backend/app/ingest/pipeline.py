"""Orchestrierung der regelbasierten Ingestion (Phase 1) + CLI.

Beispiele (im Container):
  python -m app.ingest.pipeline --root /data "2014/140214_pk_bl.pdf"   # ein Protokoll -> JSON
  python -m app.ingest.pipeline --root /data --all                      # Aggregat über alle
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from .extract import extract
from .identify import identify
from .segment import segment


def run_file(path: Path, root: Path) -> dict:
    meta = identify(path, root)
    ex = extract(path)
    sections = segment(ex)
    return {
        "meta": {**asdict(meta),
                 "sitzungsdatum": meta.sitzungsdatum.isoformat() if meta.sitzungsdatum else None},
        "seiten": ex.page_count,
        "anzahl_tops": len(sections),
        "tops": [{"nr": s.nr, "titel": s.titel, "seite_von": s.seite_von,
                  "zeit_real_min": s.zeit_real_min, "zeit_geplant_min": s.zeit_geplant_min,
                  "textlen": len(s.text)} for s in sections],
    }


def find_protocols(root: Path) -> list[Path]:
    out = []
    for p in sorted(root.rglob("*")):
        if p.is_file() and identify(p, root).ist_protokoll:
            out.append(p)
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", required=True, help="Wurzel des Protokollbestands")
    ap.add_argument("--all", action="store_true", help="Aggregat über alle Protokolle")
    ap.add_argument("dateien", nargs="*", help="einzelne Protokolle (relativ zu --root)")
    args = ap.parse_args(argv)
    root = Path(args.root)

    if args.all:
        prot = find_protocols(root)
        leer = 0
        verteilung: dict[str, int] = {}
        for p in prot:
            try:
                n = len(segment(extract(p)))
            except Exception as e:  # noqa: BLE001 — robuste Aggregat-Übersicht
                print(f"FEHLER  {p.relative_to(root)}: {e}", file=sys.stderr)
                n = -1
            if n == 0:
                leer += 1
            bucket = "0" if n == 0 else "1-4" if n <= 4 else "5-9" if n <= 9 else "10+"
            verteilung[bucket] = verteilung.get(bucket, 0) + 1
        print(json.dumps({
            "protokolle": len(prot),
            "ohne_tops": leer,
            "verteilung_tops": verteilung,
        }, ensure_ascii=False, indent=2))
        return 0

    for rel in args.dateien:
        print(json.dumps(run_file(root / rel, root), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
