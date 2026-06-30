"""Suche über Items: lexikalisch (tsvector), semantisch (pgvector) oder hybrid.

- text:       deutsche Volltextsuche mit Operatoren (websearch_to_tsquery) + ODER-Fallback
- semantisch: Vektor-Ähnlichkeit (Cosinus) gegen das Query-Embedding
- hybrid:     Fusion beider Ranglisten per Reciprocal Rank Fusion (RRF)
"""
from __future__ import annotations

from sqlalchemy import text

_COLS = """
    i.id::text          AS id,
    i.typ::text         AS typ,
    i.text              AS text,
    i.verantwortlich    AS verantwortlich,
    i.abstimmung        AS abstimmung,
    d.sitzungsdatum     AS sitzungsdatum,
    d.sitzungstyp::text AS sitzungstyp,
    s.top_nr            AS top_nr,
    s.ueberschrift      AS top_titel
"""

_ORDER = {
    "relevanz": "rank DESC, d.sitzungsdatum DESC NULLS LAST",
    "datum": "d.sitzungsdatum DESC NULLS LAST, rank DESC",
}


def _text_run(session, q: str, typ: str | None, limit: int, sort: str) -> list[dict]:
    order = _ORDER.get(sort, _ORDER["relevanz"])
    sql = text(
        f"""
        SELECT {_COLS},
               ts_rank(to_tsvector('german', i.text),
                       websearch_to_tsquery('german', :q)) AS rank
        FROM item i
        JOIN section s  ON s.id = i.section_id
        JOIN document d ON d.id = s.document_id
        WHERE to_tsvector('german', i.text) @@ websearch_to_tsquery('german', :q)
          AND (CAST(:typ AS text) IS NULL OR i.typ::text = CAST(:typ AS text))
        ORDER BY {order}
        LIMIT :limit
        """  # noqa: S608 — `order` aus fester Allowlist
    )
    return [dict(r) for r in session.execute(
        sql, {"q": q, "typ": typ, "limit": limit}).mappings().all()]


def search_items(session, q: str, typ: str | None = None, limit: int = 50,
                 sort: str = "relevanz") -> dict:
    """Volltextsuche (UND) mit automatischem ODER-Fallback."""
    rows = _text_run(session, q, typ, limit, sort)
    fallback_oder = False
    terme = [t for t in q.split() if t.lower() not in {"or", "and"}]
    if not rows and len(terme) > 1 and '"' not in q:
        rows = _text_run(session, " or ".join(terme), typ, limit, sort)
        fallback_oder = bool(rows)
    return {"treffer": rows, "fallback_oder": fallback_oder}


def semantic_items(session, qvec: str, typ: str | None = None, limit: int = 50) -> list[dict]:
    """Semantische Suche per Cosinus-Ähnlichkeit gegen das Query-Embedding."""
    sql = text(
        f"""
        SELECT {_COLS},
               1 - (i.embedding <=> CAST(:qvec AS vector)) AS rank
        FROM item i
        JOIN section s  ON s.id = i.section_id
        JOIN document d ON d.id = s.document_id
        WHERE i.embedding IS NOT NULL
          AND (CAST(:typ AS text) IS NULL OR i.typ::text = CAST(:typ AS text))
        ORDER BY i.embedding <=> CAST(:qvec AS vector)
        LIMIT :limit
        """
    )
    return [dict(r) for r in session.execute(
        sql, {"qvec": qvec, "typ": typ, "limit": limit}).mappings().all()]


def hybrid_items(session, q: str, qvec: str, typ: str | None = None, limit: int = 50) -> list[dict]:
    """Fusion aus Text- und Vektorsuche (RRF, k=60)."""
    txt = _text_run(session, q, typ, 50, "relevanz")
    sem = semantic_items(session, qvec, typ, 50)
    fused: dict[str, dict] = {}
    for liste in (txt, sem):
        for rang, row in enumerate(liste):
            e = fused.setdefault(row["id"], {"row": row, "score": 0.0})
            e["score"] += 1.0 / (60 + rang)
    ranked = sorted(fused.values(), key=lambda e: -e["score"])[:limit]
    return [e["row"] for e in ranked]
