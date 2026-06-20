# Deployment & Betrieb

Bezug: [ADR 0005](adr/0005-vps-docker.md). Der gesamte Stack läuft als Docker-Compose
(`infra/docker-compose.yml`).

## Dienste

| Dienst | Image (Basis) | Zweck |
|---|---|---|
| `db` | `pgvector/pgvector:pg16` | PostgreSQL + Vektor-/Volltextsuche |
| `redis` | `redis:7` | Queue für den Worker |
| `ollama` | `ollama/ollama` | lokales LLM + Embeddings |
| `backend` | eigenes (FastAPI) | API |
| `worker` | eigenes (RQ) | Ingestion-Pipeline |
| `frontend` | eigenes (Vite-Build, statisch) | UI *(Phase 5)* |
| `caddy` | `caddy:2` | Reverse Proxy + automatisches TLS |

## VPS-Anforderungen (Richtwert)

- Für ein kleineres lokales Modell: **≥ 16 GB RAM**, moderne CPU; GPU optional, aber
  beschleunigt Extraktion/Embeddings deutlich. Endgültige Modellwahl vor Phase 1.
- Schneller SSD-Speicher für Postgres-Volume und Ollama-Modelle.

## Erstinbetriebnahme

```bash
git clone git@github.com:scoutmatze/bl-protokollbuch.git
cd bl-protokollbuch
cp infra/.env.example infra/.env        # Secrets, Domain, Pfad zum Protokollbestand
docker compose -f infra/docker-compose.yml up -d
docker compose -f infra/docker-compose.yml exec ollama ollama pull <modellname>
docker compose -f infra/docker-compose.yml exec backend alembic upgrade head
```

## Protokollbestand bereitstellen

Der Bestand wird **nicht** ins Git eingecheckt. Er wird dem `worker` read-only gemountet
(Pfad in `.env`: `PROTOKOLL_SOURCE_DIR`). Ingestion anstoßen über das Admin-UI oder CLI
(`scripts/inventory.py` für das Inventar, Ingestion-Kommando folgt in Phase 1).

## Backups

- **Postgres:** täglicher `pg_dump`, verschlüsselt, off-site. Volume `pgdata` zusätzlich sichern.
- **Originaldateien** liegen ohnehin in SharePoint/lokal — die DB ist aus ihnen reproduzierbar
  (Embeddings/Extraktionen neu berechenbar), **außer** manuelle Matchings/Tags → diese sind
  Teil des Postgres-Backups und damit geschützt.

## Sicherheit

- Nur Caddy ist öffentlich (443); alle anderen Dienste im internen Compose-Netz.
- TLS automatisch via Caddy/Let's Encrypt. Starke Secrets in `.env` (nie committen).
- Rollen-/Audit-Konzept siehe [KONZEPT.md](KONZEPT.md#8-sicherheit--datenschutz).
