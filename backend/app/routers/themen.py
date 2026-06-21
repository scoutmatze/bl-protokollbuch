"""Themen-Endpunkte (Wiki-Stränge).

  GET /api/themen            -> Liste der Themen (Strang-Größe, Zeitraum)
  GET /api/themen/{id}       -> ein Thema: chronologische TOPs mit Items
"""
from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, text
from sqlalchemy.orm import Session, selectinload

from .. import models
from ..db import get_session

router = APIRouter()


@router.get("")
def liste(
    min_sitzungen: int = Query(1, ge=1, description="nur Themen ab N Sitzungen"),
    session: Session = Depends(get_session),
) -> dict:
    sql = text(
        """
        SELECT t.id::text AS id, t.name AS name, t.status::text AS status,
               count(DISTINCT s.document_id) AS sitzungen,
               min(d.sitzungsdatum) AS von, max(d.sitzungsdatum) AS bis
        FROM topic t
        JOIN topic_link tl ON tl.topic_id = t.id AND tl.status::text <> 'abgelehnt'
        JOIN section s      ON s.id = tl.section_id
        JOIN document d     ON d.id = s.document_id
        GROUP BY t.id
        HAVING count(DISTINCT s.document_id) >= :min
        ORDER BY sitzungen DESC, t.name
        """
    )
    rows = session.execute(sql, {"min": min_sitzungen}).mappings().all()
    return {"anzahl": len(rows), "themen": [
        {**dict(r), "von": r["von"].isoformat() if r["von"] else None,
         "bis": r["bis"].isoformat() if r["bis"] else None}
        for r in rows
    ]}


@router.get("/{topic_id}")
def detail(topic_id: uuid.UUID, session: Session = Depends(get_session)) -> dict:
    topic = session.get(models.Topic, topic_id)
    if not topic:
        raise HTTPException(404, "Thema nicht gefunden")
    links = session.scalars(
        select(models.TopicLink)
        .where(models.TopicLink.topic_id == topic_id,
               models.TopicLink.status != models.LinkStatus.abgelehnt)
        .options(
            selectinload(models.TopicLink.section).selectinload(models.Section.items),
            selectinload(models.TopicLink.section).selectinload(models.Section.document),
        )
    ).all()
    secs = [l.section for l in links]
    secs.sort(key=lambda s: s.document.sitzungsdatum or date.min)
    return {
        "id": str(topic.id),
        "name": topic.name,
        "status": topic.status.value,
        "verlauf": [
            {
                "document_id": str(s.document_id),
                "sitzungsdatum": s.document.sitzungsdatum.isoformat() if s.document.sitzungsdatum else None,
                "sitzungstyp": s.document.sitzungstyp.value,
                "top_nr": s.top_nr,
                "top_titel": s.ueberschrift,
                "items": [
                    {"typ": it.typ.value, "text": it.text,
                     "verantwortlich": it.verantwortlich, "abstimmung": it.abstimmung}
                    for it in sorted(s.items, key=lambda i: i.id.hex)
                ],
            }
            for s in secs
        ],
    }
