"""Such-Endpunkt: GET /api/search?q=...&typ=beschluss&modus=hybrid"""
from __future__ import annotations

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..db import get_session
from ..embeddings import embed_one, to_pgvector
from ..search import hybrid_items, search_items, semantic_items

router = APIRouter()


@router.get("")
def search(
    q: str = Query(..., min_length=2, description="Suchbegriff"),
    typ: str | None = Query(None, description="Filter: beschluss|info|aufgabe|diskussion"),
    sort: str = Query("relevanz", pattern="^(relevanz|datum)$"),
    modus: str = Query("text", pattern="^(text|semantisch|hybrid)$"),
    limit: int = Query(50, ge=1, le=100),
    session: Session = Depends(get_session),
) -> dict:
    if modus == "text":
        res = search_items(session, q, typ, limit, sort)
        hinweis = ("Keine Treffer mit allen Begriffen — zeige Treffer mit mindestens einem."
                   if res["fallback_oder"] else None)
        return {"anzahl": len(res["treffer"]), "treffer": res["treffer"], "hinweis": hinweis}

    try:
        qvec = to_pgvector(embed_one(q))
    except (httpx.HTTPError, KeyError) as e:
        raise HTTPException(503, f"Embedding-Dienst nicht erreichbar: {e}")

    treffer = (semantic_items(session, qvec, typ, limit) if modus == "semantisch"
               else hybrid_items(session, q, qvec, typ, limit))
    return {"anzahl": len(treffer), "treffer": treffer, "hinweis": None}
