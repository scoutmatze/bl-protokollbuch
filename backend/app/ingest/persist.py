"""Persistiert extrahierte Protokolle in die Datenbank — idempotent über SHA-256.

CLI:
  python -m app.ingest.persist --root /data           # alle Protokolle einlesen
  python -m app.ingest.persist --root /data --reset    # vorher alle Daten löschen
"""
from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

from sqlalchemy import delete, select

from .. import models
from ..db import SessionLocal
from .extract import extract
from .identify import identify
from .items import extract_items
from .pipeline import find_protocols
from .segment import segment

_VALID_MARKER = {"I", "B", "E"}


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def persist_file(session, path: Path, root: Path) -> str:
    meta = identify(path, root)
    if not meta.ist_protokoll:
        return "kein_protokoll"
    digest = _sha256(path)
    if session.scalar(select(models.Document.id).where(models.Document.sha256 == digest)):
        return "duplikat"

    ex = extract(path)
    sections = segment(ex)
    doc = models.Document(
        sitzungsdatum=meta.sitzungsdatum,
        gremium="Bundesleitung",
        sitzungstyp=models.Sitzungstyp(meta.sitzungstyp),
        titel=f"{meta.sitzungstyp.upper()} {meta.sitzungsdatum or ''}".strip(),
        quelldatei=meta.quelldatei,
        quellformat=models.Quellformat(meta.quellformat),
        sha256=digest,
        seiten=ex.page_count,
        roh_text=ex.text,
        status=models.DocStatus.fertig,
        epoche=models.Epoche(meta.epoche),
    )
    session.add(doc)
    session.flush()

    for s in sections:
        sec = models.Section(
            document_id=doc.id, top_nr=str(s.nr), ueberschrift=s.titel, reihenfolge=s.nr,
            text=s.text, seite_von=s.seite_von, seite_bis=s.seite_bis,
            zeit_real_min=s.zeit_real_min, zeit_geplant_min=s.zeit_geplant_min,
        )
        session.add(sec)
        session.flush()
        for it in extract_items(s.lines, ex.page_width):
            marker = it.ibe_marker if it.ibe_marker in _VALID_MARKER else None
            session.add(models.Item(
                section_id=sec.id, typ=models.ItemTyp(it.typ), text=it.text,
                verantwortlich=it.verantwortlich, frist=it.frist,
                ibe_marker=models.IbeMarker(marker) if marker else None,
                abstimmung=it.abstimmung, confidence=1.0,
            ))
    return "ok"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", required=True)
    ap.add_argument("--reset", action="store_true", help="alle Daten vorher löschen")
    args = ap.parse_args(argv)
    root = Path(args.root)

    counts: dict[str, int] = {}
    with SessionLocal() as session:
        if args.reset:
            for m in (models.Item, models.Section, models.Document):
                session.execute(delete(m))
            session.commit()
        for p in find_protocols(root):
            try:
                res = persist_file(session, p, root)
                session.commit()
            except Exception as e:  # noqa: BLE001
                session.rollback()
                res = "fehler"
                print(f"FEHLER {p.relative_to(root)}: {e}", file=sys.stderr)
            counts[res] = counts.get(res, 0) + 1

    docs = sum(counts.get(k, 0) for k in ("ok", "duplikat"))
    print(f"persistiert: {counts}")
    with SessionLocal() as session:
        from sqlalchemy import func
        n_doc = session.scalar(select(func.count()).select_from(models.Document))
        n_sec = session.scalar(select(func.count()).select_from(models.Section))
        n_item = session.scalar(select(func.count()).select_from(models.Item))
        print(f"DB-Bestand: {n_doc} Sitzungen, {n_sec} TOPs, {n_item} Items")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
