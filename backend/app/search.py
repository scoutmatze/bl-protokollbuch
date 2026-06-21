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


def _run(session, q: str, typ: str | None, limit: int, sort: str) -> list[dict]:
    """Eine Suchanfrage mit websearch_to_tsquery.

    websearch_to_tsquery unterstützt natürliche Operatoren:
      `wbk betrag` -> beide (UND) · `wbk or betrag` -> einer · `"genaue phrase"` · `-wort`
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
                       websearch_to_tsquery('german', :q)) AS rank
        FROM item i
        JOIN section s  ON s.id = i.section_id
        JOIN document d ON d.id = s.document_id
        WHERE to_tsvector('german', i.text) @@ websearch_to_tsquery('german', :q)
          AND (CAST(:typ AS text) IS NULL OR i.typ::text = CAST(:typ AS text))
        ORDER BY {order}
        LIMIT :limit
        """  # noqa: S608 — `order` stammt aus fester Allowlist (_ORDER), kein User-Input
    )
    rows = session.execute(sql, {"q": q, "typ": typ, "limit": limit}).mappings().all()
    return [dict(r) for r in rows]


def search_items(session, q: str, typ: str | None = None, limit: int = 50,
                 sort: str = "relevanz") -> dict:
    """Volltextsuche über Items. Bei mehreren Begriffen gilt UND; liefert das
    keine Treffer, wird automatisch auf ODER zurückgefallen (mit Hinweis).
    """
    rows = _run(session, q, typ, limit, sort)
    fallback_oder = False
    terme = [t for t in q.split() if t.lower() not in {"or", "and"}]
    if not rows and len(terme) > 1 and '"' not in q:
        rows = _run(session, " or ".join(terme), typ, limit, sort)
        fallback_oder = bool(rows)
    return {"treffer": rows, "fallback_oder": fallback_oder}
