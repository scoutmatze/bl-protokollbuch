"""Themen-Matching (Phase 1, lexikalisch) — fügt TOPs sitzungsübergreifend zu
Themensträngen zusammen.

Idee: Der TOP-Titel ist das stärkste Signal (z. B. „Ausbildung", „Prisma",
„Bundesversammlung"). Wir normalisieren die Titel zu Bedeutungs-Tokens und
clustern greedy über Jaccard-Ähnlichkeit. Jeder Cluster wird ein Topic, jede
Zuordnung ein TopicLink (methode=auto, status=vorgeschlagen) — damit bleibt das
manuelle Widersprechen/Bestätigen später möglich.

Semantisches Matching (Embeddings) kann später ergänzt werden; die Datenstruktur
(Topic/TopicLink) bleibt gleich.
"""
from __future__ import annotations

import re

from sqlalchemy import delete, func, select

from . import models

# Generische TOP-Titel und Füllwörter, die kein Thema tragen.
STOP = {
    "der", "die", "das", "und", "oder", "für", "von", "zur", "zum", "im", "in",
    "auf", "mit", "des", "den", "dem", "ein", "eine", "einer", "eines", "zu",
    "ag", "bak", "baks", "top", "tops", "bv", "dpsg", "bl", "ebl", "buvo",
    "sonstiges", "organisatorisches", "orga", "begrüßung", "begruessung",
    "ankommensrunde", "reflexion", "bericht", "berichte", "themenspeicher",
    "protokoll", "verschiedenes", "sonstige", "infos", "info", "thema", "themen",
    "neues", "aktuelles", "rückblick", "ausblick", "abschluss",
    "zeit", "min", "uhr", "von", "minuten",
}


def norm_tokens(titel: str | None) -> frozenset[str]:
    if not titel:
        return frozenset()
    # Unicode-\w, damit Umlaute/ß zusammenbleiben (sonst zerfällt "Begrüßung").
    toks = re.findall(r"\w+", titel.lower())
    return frozenset(
        t for t in toks if t not in STOP and not t.isdigit() and len(t) >= 3
    )


def _jaccard(a: frozenset[str], b: frozenset[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def build_topics(session, threshold: float = 0.5) -> dict:
    """Baut alle Topics neu aus den Sections (idempotent: löscht vorherige).

    Konservativ: Cluster-Tokens = Seed-Titel (kein Wachsen) -> weniger Über-Merge.
    """
    rows = session.execute(
        select(models.Section.id, models.Section.ueberschrift, models.Document.sitzungsdatum)
        .join(models.Document, models.Document.id == models.Section.document_id)
        .order_by(models.Document.sitzungsdatum.asc().nullsfirst())
    ).all()

    clusters: list[dict] = []
    ungetaggt = 0
    for sid, titel, _datum in rows:
        toks = norm_tokens(titel)
        if not toks:
            ungetaggt += 1
            continue
        best, best_score = None, 0.0
        for c in clusters:
            sc = _jaccard(toks, c["tokens"])
            if sc > best_score:
                best, best_score = c, sc
        if best and best_score >= threshold:
            best["section_ids"].append(sid)
            best["names"][titel] = best["names"].get(titel, 0) + 1
        else:
            clusters.append({"tokens": toks, "names": {titel: 1}, "section_ids": [sid]})

    # Idempotent neu aufbauen (v1: alle Topics/Links sind auto).
    session.execute(delete(models.TopicLink))
    session.execute(delete(models.Topic))
    session.flush()

    for c in clusters:
        name = max(c["names"].items(), key=lambda kv: (kv[1], -len(kv[0])))[0]
        mehrfach = len(c["section_ids"]) > 1
        topic = models.Topic(
            name=name,
            status=models.TopicStatus.laufend if mehrfach else models.TopicStatus.einmalig,
        )
        session.add(topic)
        session.flush()
        for sid in c["section_ids"]:
            session.add(models.TopicLink(
                section_id=sid, topic_id=topic.id, match_score=1.0,
                methode=models.LinkMethode.auto, status=models.LinkStatus.vorgeschlagen,
            ))
    session.commit()

    mehrteilig = sum(1 for c in clusters if len(c["section_ids"]) > 1)
    return {"topics": len(clusters), "mehrteilig": mehrteilig,
            "einmalig": len(clusters) - mehrteilig, "ungetaggte_tops": ungetaggt}


def main(argv: list[str] | None = None) -> int:
    import argparse

    from .db import SessionLocal

    ap = argparse.ArgumentParser(description="Themen (neu) aufbauen")
    ap.add_argument("--force", action="store_true",
                    help="auch dann neu bauen, wenn manuelle Korrekturen existieren")
    args = ap.parse_args(argv)

    with SessionLocal() as session:
        # Schutz: manuelle Reviews (manuelle Links / Widersprüche) nicht versehentlich verwerfen.
        manuell = session.scalar(select(func.count()).select_from(models.TopicLink).where(
            (models.TopicLink.methode == models.LinkMethode.manuell)
            | (models.TopicLink.status == models.LinkStatus.abgelehnt)))
        if manuell and not args.force:
            print(f"ABBRUCH: {manuell} manuelle Korrektur(en) vorhanden. "
                  f"Mit --force trotzdem neu bauen (überschreibt das Review).")
            return 1
        stats = build_topics(session)
    print(stats)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
