"""Such-Endpunkt: GET /api/search?q=...&typ=beschluss"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..db import get_session
from ..search import search_items

router = APIRouter()


@router.get("")
def search(
    q: str = Query(..., min_length=2, description="Suchbegriff"),
    typ: str | None = Query(None, description="Filter: beschluss|info|aufgabe|diskussion"),
    limit: int = Query(20, ge=1, le=100),
    session: Session = Depends(get_session),
) -> dict:
    treffer = search_items(session, q, typ, limit)
    return {"anzahl": len(treffer), "treffer": treffer}
