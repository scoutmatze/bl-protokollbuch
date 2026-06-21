# BL-Protokollbuch / Wiki

Durchsuchbares Protokoll- und Wissens-Wiki für die Protokolle der **DPSG Bundesleitung**.

Aus 12+ Jahren Sitzungsprotokollen (PDF/DOCX) entsteht ein durchsuchbarer Bestand, in dem
sich Tagesordnungspunkte sitzungsübergreifend zu **Themensträngen** zusammenführen lassen.
Zwei Kern-Nutzungen:

- **Wiki** — „Thema *Ausbildung*: was haben wir wann besprochen?" → ein chronologisch
  aufgebauter Themenstrang über alle Sitzungen.
- **Suche** — „Gab es mal einen *Beschluss* zu X?" → gezielte Suche über Beschlüsse & Infos.

> ⚠️ **Datenschutz:** Die Protokolle enthalten personenbezogene Daten. Die KI-Verarbeitung
> läuft daher **vollständig lokal (self-hosted LLM via Ollama)** — es verlassen keine Daten
> die eigene Infrastruktur. Das Repository ist **privat**; es werden **keine Protokolle**
> eingecheckt (siehe [.gitignore](.gitignore)).

## Dokumentation

| Dokument | Inhalt |
|---|---|
| [docs/KONZEPT.md](docs/KONZEPT.md) | Komplettkonzeption: Architektur, Datenmodell, Matching, Suche, Roadmap |
| [docs/BESTANDSANALYSE.md](docs/BESTANDSANALYSE.md) | Befunde aus dem echten Dateibestand (Struktur, Epochen, Formate) |
| [docs/DATENMODELL.md](docs/DATENMODELL.md) | Entitäten & Relationen im Detail |
| [docs/PIPELINE.md](docs/PIPELINE.md) | Ingestion-Pipeline Schritt für Schritt |
| [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) | Betrieb auf eigenem VPS (Docker) |
| [docs/adr/](docs/adr/) | Architecture Decision Records (begründete Entscheidungen) |

## Tech-Stack (Kurzfassung)

- **Backend:** Python / FastAPI · **Worker:** RQ + Redis
- **Datenbank:** PostgreSQL + `pgvector` (Relationaldaten, Volltext *und* Vektorsuche in einer DB)
- **LLM (lokal):** Ollama — Extraktion + Embeddings, keine Cloud
- **Frontend:** React + Vite (SPA) — *folgt in Phase 5*
- **Betrieb:** Docker Compose, Reverse Proxy Caddy (TLS), eigener VPS

## Projektstatus

- **Phase 0** — Konzeption & Gerüst ✅
- **Phase 1** — regelbasierte Ingestion (PDF/DOCX → TOPs → Items), validiert über 157
  Protokolle: 155/157 segmentiert, 22.367 Items (792 Beschlüsse) ✅
- **Phase 2** — DB-Persistenz (PostgreSQL + pgvector) + deutsche Volltextsuche ✅
- **Frontend** — Minimal-UI (React/Vite): Suche mit Typ-Filter + Sitzungs-Browser ✅
- Nächste Phasen: Embeddings/semantische Suche · Themen-Matching · Login · Deployment

### Alles starten (Dev)

```bash
echo 'PROTOKOLL_SOURCE_DIR=<Pfad zum BL-Sitzungen-Ordner>' > infra/.env
docker compose -f infra/docker-compose.dev.yml up        # db + backend + frontend
# einmalig in zweitem Terminal: Schema + Daten laden
docker compose -f infra/docker-compose.dev.yml run --rm backend alembic upgrade head
docker compose -f infra/docker-compose.dev.yml run --rm backend python -m app.ingest.persist --root /data
```
Frontend: http://localhost:5173 · API-Doku: http://localhost:8000/docs

Roadmap-Details siehe [docs/KONZEPT.md](docs/KONZEPT.md#roadmap).

## Lokaler Entwicklungslauf

Phase 1 (Extraktion, ohne DB) — strukturiertes JSON eines Protokolls:

```bash
docker build -t bl-backend-dev backend
docker run --rm -v "$PWD/backend:/app" -v "<BL-Sitzungen>:/data:ro" -w /app \
  bl-backend-dev python -m app.ingest.pipeline --root /data --all
```

Phase 2 (DB + Suche) — Postgres hochfahren, migrieren, persistieren, suchen:

```bash
docker network create blnet
docker run -d --name bldb --network blnet \
  -e POSTGRES_USER=protokoll -e POSTGRES_PASSWORD=protokoll -e POSTGRES_DB=protokollbuch \
  pgvector/pgvector:pg16
export DBURL="postgresql+psycopg://protokoll:protokoll@bldb:5432/protokollbuch"
run() { docker run --rm --network blnet -v "$PWD/backend:/app" -w /app -e DATABASE_URL="$DBURL" "$@"; }
run -v "<BL-Sitzungen>:/data:ro" bl-backend-dev alembic upgrade head
run -v "<BL-Sitzungen>:/data:ro" bl-backend-dev python -m app.ingest.persist --root /data
```

Tests:

```bash
docker run --rm -v "$PWD/backend:/app" -w /app bl-backend-dev python -m pytest -q
```
