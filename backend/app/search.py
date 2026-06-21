"""Volltext-Suche über Items (deutsch). Phase 2: lexikalisch (Postgres tsvector).

Der semantische Teil (pgvector-Embeddings) kommt in einer späteren Phase hinzu;
die API-Form bleibt dann gleich (hybride Suche).
"""
from __future__ import annotations

from sqlalchemy import text


def search_items(session, q: str, typ: str | None = None, limit: int = 20) -> list[dict]:
    """Sucht Items per deutscher Volltextsuche, optional gefiltert nach Typ."""
    sql = text(
        """
        SELECT i.typ::text         AS typ,
               i.text              AS text,
               i.verantwortlich    AS verantwortlich,
               i.abstimmung        AS abstimmung,
               d.sitzungsdatum     AS sitzungsdatum,
               d.sitzungstyp::text AS sitzungstyp,
               s.top_nr            AS top_nr,
               s.ueberschrift      AS top_titel,
               ts_rank(to_tsvector('german', i.text),
                       plainto_tsquery('german', :q)) AS rank
        FROM item i
        JOIN section s  ON s.id = i.section_id
        JOIN document d ON d.id = s.document_id
        WHERE to_tsvector('german', i.text) @@ plainto_tsquery('german', :q)
          AND (CAST(:typ AS text) IS NULL OR i.typ::text = CAST(:typ AS text))
        ORDER BY rank DESC, d.sitzungsdatum DESC NULLS LAST
        LIMIT :limit
        """
    )
    rows = session.execute(sql, {"q": q, "typ": typ, "limit": limit}).mappings().all()
    return [dict(r) for r in rows]
