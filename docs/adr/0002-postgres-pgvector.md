# ADR 0002 — PostgreSQL + pgvector als einzige Datenbank

**Status:** akzeptiert · **Datum:** 2026-06-20

## Kontext
Es werden drei Zugriffsmuster gebraucht: relationale Daten (Sitzungen/TOPs/Items/Topics),
**Volltextsuche** (deutsch) und **Vektorsuche** (semantisches Matching & Suche).

## Entscheidung
Eine **PostgreSQL**-Instanz mit der Erweiterung **`pgvector`**. Volltext über `tsvector`
(deutsche Konfiguration), Semantik über `vector`-Spalten mit HNSW/IVFFlat-Index.

## Begründung
- Eine DB statt Postgres + separater Vektor-DB (Qdrant/Weaviate) → deutlich weniger Ops,
  Backups und Moving Parts auf einem selbstbetriebenen VPS.
- `pgvector` ist für diese Datenmenge (einige Tausend Sections/Items) mehr als ausreichend.
- Hybride Suche (lexikalisch + semantisch) in einer Query kombinierbar.

## Konsequenzen
- **+** Einfacher Betrieb, transaktionale Konsistenz über alle Daten.
- **−** Bei extremem Wachstum ggf. später dedizierte Vektor-DB — für diesen Anwendungsfall
  unrealistisch. Reversibel, da Embeddings neu berechenbar sind.
