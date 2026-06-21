"""Themen-Endpunkte (Wiki-Stränge).

  GET /api/themen            -> Liste der Themen (Strang-Größe, Zeitraum)
  GET /api/themen/{id}       -> ein Thema: chronologische TOPs mit Items
"""
from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, text
from sqlalchemy.orm import Session, selectinload

from .. import models
from ..db import get_session

router = APIRouter()


class TopicPatch(BaseModel):
    name: str | None = None
    status: str | None = None


class MergeBody(BaseModel):
    quelle_id: uuid.UUID  # dieses Thema wird in {topic_id} einsortiert und gelöscht


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
                "section_id": str(s.id),
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


# --- Matching-Review -------------------------------------------------------
@router.patch("/{topic_id}")
def umbenennen(topic_id: uuid.UUID, patch: TopicPatch,
               session: Session = Depends(get_session)) -> dict:
    topic = session.get(models.Topic, topic_id)
    if not topic:
        raise HTTPException(404, "Thema nicht gefunden")
    if patch.name is not None:
        topic.name = patch.name.strip() or topic.name
    if patch.status is not None:
        try:
            topic.status = models.TopicStatus(patch.status)
        except ValueError:
            raise HTTPException(422, "Ungültiger Status")
    session.commit()
    return {"id": str(topic.id), "name": topic.name, "status": topic.status.value}


@router.post("/{topic_id}/sections/{section_id}/ablehnen")
def link_ablehnen(topic_id: uuid.UUID, section_id: uuid.UUID,
                  session: Session = Depends(get_session)) -> dict:
    """Widerspruch: TOP aus dem Thema entfernen (Link -> abgelehnt)."""
    link = session.scalar(select(models.TopicLink).where(
        models.TopicLink.topic_id == topic_id, models.TopicLink.section_id == section_id))
    if not link:
        raise HTTPException(404, "Zuordnung nicht gefunden")
    link.status = models.LinkStatus.abgelehnt
    session.commit()
    return {"ok": True}


@router.post("/{topic_id}/sections/{section_id}")
def link_setzen(topic_id: uuid.UUID, section_id: uuid.UUID,
                session: Session = Depends(get_session)) -> dict:
    """TOP manuell diesem Thema zuordnen (bestätigter manueller Link)."""
    if not session.get(models.Topic, topic_id):
        raise HTTPException(404, "Thema nicht gefunden")
    if not session.get(models.Section, section_id):
        raise HTTPException(404, "TOP nicht gefunden")
    link = session.scalar(select(models.TopicLink).where(
        models.TopicLink.topic_id == topic_id, models.TopicLink.section_id == section_id))
    if link:
        link.status = models.LinkStatus.bestaetigt
        link.methode = models.LinkMethode.manuell
    else:
        session.add(models.TopicLink(
            topic_id=topic_id, section_id=section_id, methode=models.LinkMethode.manuell,
            status=models.LinkStatus.bestaetigt, match_score=None))
    session.commit()
    return {"ok": True}


@router.post("/{topic_id}/merge")
def zusammenfuehren(topic_id: uuid.UUID, body: MergeBody,
                    session: Session = Depends(get_session)) -> dict:
    """Führt das Quell-Thema in {topic_id} (Ziel) zusammen und löscht die Quelle."""
    ziel = session.get(models.Topic, topic_id)
    quelle = session.get(models.Topic, body.quelle_id)
    if not ziel or not quelle:
        raise HTTPException(404, "Thema nicht gefunden")
    if ziel.id == quelle.id:
        raise HTTPException(422, "Quelle und Ziel sind identisch")
    # Sections, die im Ziel schon verlinkt sind -> Quell-Link löschen (kein Duplikat).
    ziel_sections = set(session.scalars(select(models.TopicLink.section_id)
                                        .where(models.TopicLink.topic_id == ziel.id)).all())
    for link in session.scalars(select(models.TopicLink)
                                .where(models.TopicLink.topic_id == quelle.id)).all():
        if link.section_id in ziel_sections:
            session.delete(link)
        else:
            link.topic_id = ziel.id
    session.flush()
    session.delete(quelle)
    if len(session.scalars(select(models.TopicLink.section_id)
                           .where(models.TopicLink.topic_id == ziel.id)).all()) > 1:
        ziel.status = models.TopicStatus.laufend
    session.commit()
    return {"ok": True, "ziel_id": str(ziel.id)}
