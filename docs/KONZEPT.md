# Komplettkonzeption — BL-Protokollbuch / Wiki

Stand 2026-06-20. Lebendes Dokument; Entscheidungen werden als
[ADR](adr/) festgehalten.

## 1. Zielbild

Aus 12+ Jahren Sitzungsprotokollen der DPSG-Bundesleitung entsteht ein durchsuchbarer
Bestand mit zwei Kern-Nutzungen:

- **Wiki-Modus** — „Thema *Ausbildung*: was haben wir wann besprochen?" → ein Themenstrang
  über alle Jahre, chronologisch aufeinander aufbauend.
- **Such-Modus** — „Gab es mal einen *Beschluss* zu X?" → gezielte Suche über Beschlüsse/Infos
  mit Filtern.

Dahinter ein Bestand, der **automatisch zerlegt, extrahiert und thematisch gruppiert** wird —
mit **menschlicher Kontrolle über jedes Matching**.

## 2. Leitentscheidungen

| Thema | Entscheidung | ADR |
|---|---|---|
| KI-Verarbeitung | **Lokales LLM (Ollama)**, keine Cloud — DSGVO | [0001](adr/0001-lokales-llm.md) |
| Datenbank | **PostgreSQL + pgvector** (eine DB für alles) | [0002](adr/0002-postgres-pgvector.md) |
| Authentifizierung | **Eigene Benutzerverwaltung**, OIDC-fähig gebaut | [0003](adr/0003-eigene-benutzerverwaltung.md) |
| Ingestion | **Multi-Format** (PDF/DOCX/XLSX/EML), heuristik-first | [0004](adr/0004-multiformat-heuristik-ingestion.md) |
| Betrieb | **Eigener VPS, Docker Compose** | [0005](adr/0005-vps-docker.md) |

## 3. Architektur

```
┌─────────────┐   REST/JSON   ┌──────────────┐
│  Frontend   │ ────────────► │   Backend    │
│  React/Vite │               │   FastAPI    │
└─────────────┘               └──────┬───────┘
                                     │
        ┌────────────────────────────┼─────────────────────┐
        ▼                            ▼                      ▼
┌──────────────┐            ┌─────────────────┐     ┌──────────────┐
│ PostgreSQL   │            │  Worker (RQ)    │     │   Ollama     │
│ + pgvector   │◄───────────│  Ingestion-     │────►│ LLM + Embed. │
│ Daten+Volltext│           │  Pipeline       │     │  (lokal)     │
│ +Vektoren    │            └─────────────────┘     └──────────────┘
└──────────────┘
   alles in Docker Compose, davor Caddy (TLS, Reverse Proxy)
```

Begründung des Stacks: siehe ADRs. Kurz: FastAPI = bestes Ökosystem für PDF/LLM/Embeddings;
Postgres+pgvector spart eine separate Vektor-DB; RQ-Worker, weil PDF-Verarbeitung langläuft.

## 4. Datenmodell (Überblick)

Vollständig in [DATENMODELL.md](DATENMODELL.md). Kernentitäten:

- **Document** — eine Sitzung/ein Protokoll (Datum, Gremium, Sitzungstyp, Quelldatei, Hash).
- **Section** — ein TOP innerhalb einer Sitzung (Nr., Überschrift, Text, Seiten, Embedding).
- **Item** — extrahierte Einheit: `beschluss` / `info` / `aufgabe` / `diskussion` (+ Verantwortliche/Frist).
- **Topic** — verschmolzener Themenstrang über Sitzungen, mit Status
  (`laufend` / `erledigt` / `veranstaltung` / `einmalig` / `nicht_priorisiert`).
- **TopicLink** — Zuordnung Section ↔ Topic **als Objekt mit Status**
  (`vorgeschlagen` / `bestätigt` / `abgelehnt`, `auto` / `manuell`).
- **Tag**, **User**, **AuditLog**.

**Kernidee Matching:** Die Zuordnung ist ein eigenes Objekt mit Status. Damit lässt sich
jedem automatischen Vorschlag **widersprechen** und es lassen sich **manuelle** Zuordnungen
setzen — Sections eines Topics werden per `sitzungsdatum` chronologisch sortiert.

## 5. Ingestion-Pipeline

Vollständig in [PIPELINE.md](PIPELINE.md). Kurz:

1. **Einlesen & Dedup** (SHA-256). 2. **Format-Router** (PDF→PyMuPDF, DOCX→python-docx, …),
OCR-Fallback bei Scans. 3. **Metadaten** (Datum/Gremium/Typ aus Datei-/Ordnername + Kopf).
4. **TOP-Segmentierung** (Heuristik aus Nummerierung/Layout, LLM korrigiert).
5. **Item-Extraktion** (I/B/E-Marker + WER-Spalte heuristisch, LLM glättet → striktes JSON).
6. **Embeddings** (Section & Item → pgvector). 7. **Topic-Matching** (s. u.).

Heuristik-first ist bewusst gewählt (siehe [Bestandsanalyse](BESTANDSANALYSE.md)): Die
I/B/E-Marker und die WER-Spalte sind bereits strukturierte Daten — das LLM muss nur glätten.

## 6. Matching-Logik

Für jede neue Section gegen bestehende Topics:

- **Score** = Embedding-Ähnlichkeit (semantisch) + lexikalische Überschneidung.
- `Score ≥ T_high` → **Auto-Vorschlag** (optional auto-bestätigt).
- `T_low ≤ Score < T_high` → **Matching-Inbox** (manuelle Prüfung).
- `Score < T_low` → Vorschlag **neues Topic** (LLM schlägt Namen vor).

Schwellen konfigurierbar — anfangs konservativ (viel Review), später lockerer. Die
Kontinuitäts-Dokumente (`Themenspeicher`, `Abgeschlossene TOPs`) seed-en Topics + Status und
dienen als Validierung.

## 7. Frontend-Ansichten

1. **Themen/Wiki** — Topic-Seite mit chronologischer Timeline, aggregierten Beschlüssen/Infos,
   „letzter Stand", Filter nach Tag/Status.
2. **Suche** — eine Leiste, **hybrid** (semantisch + Volltext deutsch), Filter: Typ (=Beschluss),
   Gremium, Zeitraum, Tag, Topic.
3. **Sitzungsansicht** — Originalprotokoll je Sitzung, TOPs, Deep-Link zur Quellseite.
4. **Matching-Inbox** — Reviewqueue für vorgeschlagene Zuordnungen.
5. **Tags** — manuell + LLM-Vorschläge, editierbar.
6. **Admin** — Nutzer, Ingestion-Status, Re-Processing.

## 8. Sicherheit & Datenschutz

- Lokales LLM → **keine Daten verlassen die Infrastruktur**.
- Argon2-Hashes, JWT-Sessions, **Rollen** (`admin`/`editor`/`reader`), Admin-Einladungsflow.
- **Audit-Log** für Matching-/Tag-Änderungen, verschlüsselte Backups, TLS via Caddy.
- Repository privat; **keine Protokolle im Git** (siehe `.gitignore`).
- Architektur OIDC-fähig → späterer SSO-Umstieg (Keycloak) ohne Umbau.

## 9. Roadmap {#roadmap}

| Phase | Inhalt | Ergebnis |
|---|---|---|
| **0** | Repo, Doku, Docker-Gerüst, DB-Schema, Inventar-Skript | lauffähiges Gerüst *(dieser Stand)* |
| **1** | Multi-Format-Ingestion + Extraktion | 1 Protokoll end-to-end im System |
| **2** | TOP-Segmentierung + Item-Extraktion (heuristik + LLM) | an echten PDFs/DOCX validiert |
| **3** | Embeddings + hybride Suche | „Beschluss zu…" funktioniert |
| **4** | Topic-Matching + Matching-Inbox | Themenstränge mit Review |
| **5** | Wiki-UI + Tags (Frontend) | beide Kern-Nutzungen nutzbar |
| **6** | Deployment VPS, Backups, Betriebsdoku | produktiv |

## 10. Offene Punkte / Risiken

- **LLM-Modellwahl** hängt von der VPS-Hardware ab (RAM/GPU) — wird vor Phase 1 festgelegt.
- **OCR-Qualität** alter Scans erst an echten Dateien beurteilbar.
- **Human-in-the-Loop** in Phase 2 zwingend: Extraktionen sind reviewbar, nicht blind übernommen.
