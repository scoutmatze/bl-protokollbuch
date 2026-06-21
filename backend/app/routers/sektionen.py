"""TOP-Suche (für das manuelle Zuordnen im Matching-Review).

  GET /api/sektionen?q=...   -> TOPs nach Titel, mit Datum und aktuellem Thema
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..db import get_session

router = APIRouter()


@router.get("")
def suche(q: str = Query(..., min_length=2), limit: int = Query(30, ge=1, le=100),
          session: Session = Depends(get_session)) -> dict:
    sql = text(
        """
        SELECT s.id::text AS id, s.ueberschrift AS top_titel,
               d.sitzungsdatum AS sitzungsdatum, d.sitzungstyp::text AS sitzungstyp,
               (SELECT t.name FROM topic_link tl JOIN topic t ON t.id = tl.topic_id
                 WHERE tl.section_id = s.id AND tl.status::text <> 'abgelehnt'
                 ORDER BY tl.methode::text LIMIT 1) AS aktuelles_thema
        FROM section s
        JOIN document d ON d.id = s.document_id
        WHERE s.ueberschrift ILIKE '%' || :q || '%'
        ORDER BY d.sitzungsdatum DESC NULLS LAST
        LIMIT :limit
        """
    )
    rows = session.execute(sql, {"q": q, "limit": limit}).mappings().all()
    return {"treffer": [
        {**dict(r), "sitzungsdatum": r["sitzungsdatum"].isoformat() if r["sitzungsdatum"] else None}
        for r in rows
    ]}
