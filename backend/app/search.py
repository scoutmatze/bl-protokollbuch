"""Volltext-Suche über Items (deutsch). Phase 2: lexikalisch (Postgres tsvector).

Der semantische Teil (pgvector-Embeddings) kommt in einer späteren Phase hinzu;
die API-Form bleibt dann gleich (hybride Suche).
"""
from __future__ import annotations

from sqlalchemy import text


_ORDER = {
    "relevanz": "rank DESC, d.sitzungsdatum DESC NULLS LAST",
    "datum": "d.sitzungsdatum DESC NULLS LAST, rank DESC",
}


def search_items(session, q: str, typ: str | None = None, limit: int = 20,
                 sort: str = "relevanz") -> list[dict]:
    """Sucht Items per deutscher Volltextsuche, optional gefiltert nach Typ.

    sort: 'relevanz' (Standard) oder 'datum' (neueste zuerst).
    """
    order = _ORDER.get(sort, _ORDER["relevanz"])
    sql = text(
        f"""
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
        ORDER BY {order}
        LIMIT :limit
        """  # noqa: S608 — `order` stammt aus fester Allowlist (_ORDER), kein User-Input
    )
    rows = session.execute(sql, {"q": q, "typ": typ, "limit": limit}).mappings().all()
    return [dict(r) for r in rows]
