"""Endpunkte zum Browsen der Sitzungen.

  GET /api/sitzungen            -> Liste (Datum, Typ, Titel, #TOPs)
  GET /api/sitzungen/{id}       -> Detail mit TOPs und Items
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from .. import models
from ..db import get_session

router = APIRouter()


@router.get("")
def liste(session: Session = Depends(get_session)) -> dict:
    n_items = func.count(models.Item.id)
    rows = session.execute(
        select(
            models.Document.id, models.Document.sitzungsdatum, models.Document.sitzungstyp,
            models.Document.titel, func.count(func.distinct(models.Section.id)).label("tops"),
        )
        .outerjoin(models.Section, models.Section.document_id == models.Document.id)
        .group_by(models.Document.id)
        .order_by(models.Document.sitzungsdatum.desc().nullslast())
    ).all()
    return {"sitzungen": [
        {"id": str(r.id), "sitzungsdatum": r.sitzungsdatum.isoformat() if r.sitzungsdatum else None,
         "sitzungstyp": r.sitzungstyp.value, "titel": r.titel, "tops": r.tops}
        for r in rows
    ]}


@router.get("/{doc_id}")
def detail(doc_id: uuid.UUID, session: Session = Depends(get_session)) -> dict:
    doc = session.get(models.Document, doc_id)
    if not doc:
        raise HTTPException(404, "Sitzung nicht gefunden")
    secs = session.scalars(
        select(models.Section)
        .where(models.Section.document_id == doc_id)
        .order_by(models.Section.reihenfolge)
        .options(selectinload(models.Section.items))
    ).all()
    return {
        "id": str(doc.id),
        "sitzungsdatum": doc.sitzungsdatum.isoformat() if doc.sitzungsdatum else None,
        "sitzungstyp": doc.sitzungstyp.value,
        "titel": doc.titel,
        "quelldatei": doc.quelldatei,
        "tops": [
            {"nr": s.top_nr, "titel": s.ueberschrift,
             "zeit_real_min": s.zeit_real_min, "zeit_geplant_min": s.zeit_geplant_min,
             "items": [
                 {"typ": it.typ.value, "text": it.text, "verantwortlich": it.verantwortlich,
                  "abstimmung": it.abstimmung}
                 for it in sorted(s.items, key=lambda i: i.id.hex)
             ]}
            for s in secs
        ],
    }
