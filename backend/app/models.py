"""ORM-Modelle. Referenz: docs/DATENMODELL.md.

Hinweis: Enums sind als Python-Enums modelliert; konkrete Indizes (GIN auf tsvector,
HNSW/IVFFlat auf den Vektorspalten) werden in den Alembic-Migrationen angelegt.
"""
from __future__ import annotations

import enum
import uuid
from datetime import date, datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    DateTime, Enum, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .config import settings
from .db import Base

EMB = settings.embedding_dim


def _uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


# --- Enums -------------------------------------------------------------------
class Sitzungstyp(str, enum.Enum):
    bl = "bl"; ebl = "ebl"; ring_bl = "ring_bl"; ao_ebl = "ao_ebl"


class Quellformat(str, enum.Enum):
    pdf = "pdf"; docx = "docx"


class DocStatus(str, enum.Enum):
    neu = "neu"; extrahiert = "extrahiert"; segmentiert = "segmentiert"
    fertig = "fertig"; fehler = "fehler"


class Epoche(str, enum.Enum):
    flach_2014_2020 = "flach_2014_2020"; monatsordner_2021ff = "monatsordner_2021ff"


class ItemTyp(str, enum.Enum):
    beschluss = "beschluss"; info = "info"; aufgabe = "aufgabe"; diskussion = "diskussion"


class IbeMarker(str, enum.Enum):
    I = "I"; B = "B"; E = "E"


class TopicStatus(str, enum.Enum):
    laufend = "laufend"; erledigt = "erledigt"; veranstaltung = "veranstaltung"
    einmalig = "einmalig"; nicht_priorisiert = "nicht_priorisiert"


class LinkMethode(str, enum.Enum):
    auto = "auto"; manuell = "manuell"; seed = "seed"


class LinkStatus(str, enum.Enum):
    vorgeschlagen = "vorgeschlagen"; bestaetigt = "bestaetigt"; abgelehnt = "abgelehnt"


class Rolle(str, enum.Enum):
    admin = "admin"; editor = "editor"; reader = "reader"


# --- Kernentitäten -----------------------------------------------------------
class Document(Base):
    __tablename__ = "document"
    id: Mapped[uuid.UUID] = _uuid_pk()
    sitzungsdatum: Mapped[date | None] = mapped_column(index=True)
    gremium: Mapped[str] = mapped_column(String, default="Bundesleitung")
    sitzungstyp: Mapped[Sitzungstyp] = mapped_column(Enum(Sitzungstyp))
    titel: Mapped[str | None] = mapped_column(String)
    quelldatei: Mapped[str] = mapped_column(String)
    quellformat: Mapped[Quellformat] = mapped_column(Enum(Quellformat))
    sha256: Mapped[str] = mapped_column(String, unique=True, index=True)
    seiten: Mapped[int | None] = mapped_column(Integer)
    roh_text: Mapped[str | None] = mapped_column(Text)
    status: Mapped[DocStatus] = mapped_column(Enum(DocStatus), default=DocStatus.neu)
    epoche: Mapped[Epoche] = mapped_column(Enum(Epoche))

    sections: Mapped[list[Section]] = relationship(back_populates="document", cascade="all, delete-orphan")


class Section(Base):
    __tablename__ = "section"
    id: Mapped[uuid.UUID] = _uuid_pk()
    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("document.id", ondelete="CASCADE"))
    top_nr: Mapped[str | None] = mapped_column(String)
    ueberschrift: Mapped[str | None] = mapped_column(String)
    reihenfolge: Mapped[int] = mapped_column(Integer, default=0)
    text: Mapped[str | None] = mapped_column(Text)
    seite_von: Mapped[int | None] = mapped_column(Integer)
    seite_bis: Mapped[int | None] = mapped_column(Integer)
    zeit_geplant_min: Mapped[int | None] = mapped_column(Integer)
    zeit_real_min: Mapped[int | None] = mapped_column(Integer)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMB))

    document: Mapped[Document] = relationship(back_populates="sections")
    items: Mapped[list[Item]] = relationship(back_populates="section", cascade="all, delete-orphan")
    attachments: Mapped[list[Attachment]] = relationship(back_populates="section", cascade="all, delete-orphan")
    links: Mapped[list[TopicLink]] = relationship(back_populates="section", cascade="all, delete-orphan")


class Item(Base):
    __tablename__ = "item"
    id: Mapped[uuid.UUID] = _uuid_pk()
    section_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("section.id", ondelete="CASCADE"))
    typ: Mapped[ItemTyp] = mapped_column(Enum(ItemTyp), index=True)
    text: Mapped[str] = mapped_column(Text)
    verantwortlich: Mapped[str | None] = mapped_column(String)
    frist: Mapped[str | None] = mapped_column(String)
    ibe_marker: Mapped[IbeMarker | None] = mapped_column(Enum(IbeMarker))
    abstimmung: Mapped[dict | None] = mapped_column(JSONB)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMB))

    section: Mapped[Section] = relationship(back_populates="items")


class Attachment(Base):
    __tablename__ = "attachment"
    id: Mapped[uuid.UUID] = _uuid_pk()
    section_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("section.id", ondelete="CASCADE"))
    dateiname: Mapped[str] = mapped_column(String)
    pfad: Mapped[str] = mapped_column(String)
    format: Mapped[str | None] = mapped_column(String)
    roh_text: Mapped[str | None] = mapped_column(Text)

    section: Mapped[Section] = relationship(back_populates="attachments")


class Topic(Base):
    __tablename__ = "topic"
    id: Mapped[uuid.UUID] = _uuid_pk()
    name: Mapped[str] = mapped_column(String, index=True)
    beschreibung: Mapped[str | None] = mapped_column(Text)
    status: Mapped[TopicStatus] = mapped_column(Enum(TopicStatus), default=TopicStatus.laufend)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMB))

    links: Mapped[list[TopicLink]] = relationship(back_populates="topic", cascade="all, delete-orphan")


class TopicLink(Base):
    """Zuordnung Section <-> Topic als Status-behaftetes Objekt.

    Erlaubt Widerspruch gegen Auto-Vorschläge und manuelle Zuordnungen.
    """
    __tablename__ = "topic_link"
    __table_args__ = (UniqueConstraint("section_id", "topic_id", name="uq_section_topic"),)
    id: Mapped[uuid.UUID] = _uuid_pk()
    section_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("section.id", ondelete="CASCADE"))
    topic_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("topic.id", ondelete="CASCADE"))
    match_score: Mapped[float | None] = mapped_column(Float)
    methode: Mapped[LinkMethode] = mapped_column(Enum(LinkMethode))
    status: Mapped[LinkStatus] = mapped_column(Enum(LinkStatus), default=LinkStatus.vorgeschlagen, index=True)
    bestaetigt_von: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("user.id"))
    bestaetigt_am: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    section: Mapped[Section] = relationship(back_populates="links")
    topic: Mapped[Topic] = relationship(back_populates="links")


class Tag(Base):
    __tablename__ = "tag"
    id: Mapped[uuid.UUID] = _uuid_pk()
    name: Mapped[str] = mapped_column(String, unique=True)
    farbe: Mapped[str | None] = mapped_column(String)
    auto: Mapped[bool] = mapped_column(default=False)


class SectionTag(Base):
    __tablename__ = "section_tag"
    section_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("section.id", ondelete="CASCADE"), primary_key=True)
    tag_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tag.id", ondelete="CASCADE"), primary_key=True)


class TopicTag(Base):
    __tablename__ = "topic_tag"
    topic_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("topic.id", ondelete="CASCADE"), primary_key=True)
    tag_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tag.id", ondelete="CASCADE"), primary_key=True)


class User(Base):
    __tablename__ = "user"
    id: Mapped[uuid.UUID] = _uuid_pk()
    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    passwort_hash: Mapped[str] = mapped_column(String)
    rolle: Mapped[Rolle] = mapped_column(Enum(Rolle), default=Rolle.reader)
    aktiv: Mapped[bool] = mapped_column(default=True)


class AuditLog(Base):
    __tablename__ = "audit_log"
    id: Mapped[uuid.UUID] = _uuid_pk()
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("user.id"))
    aktion: Mapped[str] = mapped_column(String)
    objekt_typ: Mapped[str] = mapped_column(String)
    objekt_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    vorher: Mapped[dict | None] = mapped_column(JSONB)
    nachher: Mapped[dict | None] = mapped_column(JSONB)
    zeitpunkt: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
