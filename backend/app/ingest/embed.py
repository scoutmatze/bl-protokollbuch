"""Berechnet und speichert Embeddings für alle Items (für die semantische Suche).

CLI:
  python -m app.ingest.embed            # nur fehlende Embeddings
  python -m app.ingest.embed --alle     # alle neu berechnen
"""
from __future__ import annotations

import argparse

from sqlalchemy import select, update

from .. import models
from ..db import SessionLocal
from ..embeddings import embed_texts


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--alle", action="store_true", help="auch vorhandene neu berechnen")
    ap.add_argument("--batch", type=int, default=64)
    args = ap.parse_args(argv)

    with SessionLocal() as session:
        q = select(models.Item.id, models.Item.text)
        if not args.alle:
            q = q.where(models.Item.embedding.is_(None))
        rows = session.execute(q).all()
        total = len(rows)
        print(f"{total} Items zu embedden …")
        done = 0
        for i in range(0, total, args.batch):
            chunk = rows[i:i + args.batch]
            vecs = embed_texts([t for _, t in chunk])
            for (item_id, _), vec in zip(chunk, vecs):
                session.execute(
                    update(models.Item).where(models.Item.id == item_id).values(embedding=vec)
                )
            session.commit()
            done += len(chunk)
            print(f"  {done}/{total}", flush=True)
    print("fertig")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
