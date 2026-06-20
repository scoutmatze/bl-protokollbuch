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

Phase 0 (Konzeption & Gerüst). Roadmap siehe [docs/KONZEPT.md](docs/KONZEPT.md#roadmap).

## Schnellstart (Entwicklung)

```bash
cp infra/.env.example infra/.env      # Secrets/Pfad zum Protokollbestand setzen
docker compose -f infra/docker-compose.yml up -d
```

Inventar des Protokollbestands erzeugen (liest die Quelldateien nur lesend):

```bash
python scripts/inventory.py --source "<Pfad zum BL-Sitzungen-Ordner>" --out data/inventar.csv
```
