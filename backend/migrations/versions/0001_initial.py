"""Initiales Schema: pgvector-Extension, alle Tabellen, deutsche Volltext-Indizes.

Baseline-Migration: Die Tabellen werden aus dem ORM-Metadata erzeugt (DRY zur
Schema-Definition in app/models.py). Folgemigrationen werden normal geschrieben.

Revision ID: 0001
Revises:
"""
from alembic import op

from app.db import Base
import app.models  # noqa: F401 — registriert die Tabellen

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    Base.metadata.create_all(bind=op.get_bind())
    # Deutsche Volltext-Indizes (GIN) für die hybride Suche (lexikalischer Teil).
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_item_fts ON item "
        "USING gin (to_tsvector('german', text))"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_section_fts ON section "
        "USING gin (to_tsvector('german', coalesce(ueberschrift,'') || ' ' || coalesce(text,'')))"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_item_fts")
    op.execute("DROP INDEX IF EXISTS ix_section_fts")
    Base.metadata.drop_all(bind=op.get_bind())
