# ADR 0005 — Betrieb auf eigenem VPS mit Docker Compose

**Status:** akzeptiert · **Datum:** 2026-06-20

## Kontext
Die Anwendung soll selbst betrieben werden; das lokale LLM ([ADR 0001](0001-lokales-llm.md))
verlangt ohnehin eigene Rechenkapazität.

## Entscheidung
Deployment als **Docker-Compose-Stack** auf einem **eigenen VPS** (z. B. Hetzner/Netcup).
Dienste: `postgres` (pgvector), `redis`, `ollama`, `backend` (FastAPI), `worker` (RQ),
`frontend`, `caddy` (Reverse Proxy + automatisches TLS).

## Begründung
- Volle Datenhoheit, günstig, flexibel; ein einziger Stack für alle Dienste.
- Caddy liefert TLS „out of the box".

## Konsequenzen
- **+** Reproduzierbares Setup, einfache lokale Entwicklung = Produktion.
- **−** Eigenverantwortung für Updates/Backups → siehe [DEPLOYMENT.md](../DEPLOYMENT.md).
- **−** VPS muss für Ollama dimensioniert sein (RAM/ggf. GPU).
