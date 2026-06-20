# Ingestion-Pipeline

Verarbeitet eine Quelldatei vom Rohformat bis zum gematchten Themenstrang.
Läuft im **Worker** (RQ), nicht im Request. Jeder Schritt schreibt
`Document.status`; Fehler landen sichtbar in der Admin-Ingestion-Übersicht.

```
Quelldatei
   │  (1) Einlesen & Dedup (SHA-256)
   ▼
Rohdatei + Document(status=neu)
   │  (2) Format-Router  →  Text (+OCR-Fallback)
   ▼
Document.roh_text (status=extrahiert)
   │  (3) Metadaten: Datum / Gremium / Typ / Epoche
   ▼
   │  (4) TOP-Segmentierung (Heuristik → LLM-Korrektur)
   ▼
Sections (status=segmentiert)
   │  (5) Item-Extraktion (I/B/E + WER heuristisch → LLM glättet → JSON-Schema)
   ▼
Items
   │  (6) Embeddings (Section & Item → pgvector)
   ▼
   │  (7) Topic-Matching → TopicLink(vorgeschlagen/…)
   ▼
Document.status = fertig
```

## (1) Einlesen & Dedup
- SHA-256 über den Dateiinhalt → `Document.sha256` (unique). Bereits vorhandene Hashes
  werden übersprungen → **idempotent**, neue Protokolle einfach nachladbar.
- Quellpfad relativ speichern; Originaldatei bleibt am Ort (read-only).

## (2) Format-Router
| Format | Extraktor | Hinweis |
|---|---|---|
| PDF (Text) | **PyMuPDF** (`fitz`) | korrektes UTF-8/Umlaut-Handling (Test-Pflicht) |
| PDF (Scan) | `ocrmypdf`/Tesseract `deu` | Auto-Erkennung: kaum Textlayer → OCR |
| DOCX | **python-docx** | „Final"-Protokolle der neueren Epoche |
| XLSX | openpyxl | Anlagen (`Organisatorisches.xlsx`) |
| EML | stdlib `email` | Anlagen, Body als Text |

## (3) Metadaten
- **Datum/Typ aus Datei-/Ordnername**: `YYMMDD` + Kürzel (`bl`/`ebl`/`ring`/`ao`).
  Beispiel `190130_ebl_pk.pdf` → 2019-01-30, Typ `ebl`.
- **Fallback Kopf**: Zeile „der Sitzung der Bundesleitung I/2014 vom 12.02.2014 …".
- **Epoche** aus Pfadstruktur (flacher Jahresordner vs. Monatsordner) → wählt den Parser.

## (4) TOP-Segmentierung — Heuristik zuerst
- **Tagesordnung** am Anfang parsen → erwartete TOP-Nummern/Titel.
- **Grenzerkennung** im Body über Nummerierungsmuster (`^\d+[\.\)]`, „TOP 7") und
  Layout-Signale (fett/größere Schrift via PyMuPDF-Spans).
- **LLM-Korrektur** nur für unklare Grenzen: „Sind das wirklich getrennte TOPs?".
- Ergebnis: `Section`-Objekte mit `top_nr`, `überschrift`, `text`, Seitenbereich,
  optional `zeit_geplant/real_min` aus „(24 von 20 Min.)".
- **TOP-Unterordner** der neueren Epoche → als `Attachment` an die passende Section hängen
  (Match über TOP-Nummer/Titel im Ordnernamen).

## (5) Item-Extraktion — Marker heuristisch, LLM glättet
- Zeilen tragen `I`/`B`/`E`-Marker in der linken Randspalte und Inhalt in `WER`-Spalte.
- **Heuristik** liest Marker + WER-Spalte direkt (Spalten-Layout aus PyMuPDF-Koordinaten).
- **LLM** fasst zusammengehörige Zeilen zu einem `Item` zusammen, formuliert den Beschluss-/
  Infotext sauber und füllt fehlende Felder — Ausgabe gegen **striktes JSON-Schema** validiert
  (siehe `backend/app/extraction/schema.py`, Phase 2). Bei Schema-Fehler → Retry.
- **Mapping:** `E`→`beschluss`, `I`→`info`, `B`→`diskussion`; WER gefüllt → zusätzlich `aufgabe`.
- Abstimmungsergebnisse (dafür/dagegen/Enthaltung), falls im Text, → `Item.abstimmung` (jsonb).
- `confidence` < Schwelle → Item wird im UI zum Review markiert (**Human-in-the-Loop**).

## (6) Embeddings
- Lokales Embedding-Modell via Ollama (z. B. `multilingual-e5` / `nomic-embed-text`).
- Pro `Section` und pro `Item` ein Vektor → `pgvector` (HNSW/IVFFlat-Index).
- Zusätzlich `tsvector` (deutsch) für lexikalische Treffer → **hybride Suche**.

## (7) Topic-Matching
- Für jede neue Section: Score = Cosinus(Embedding, Topic-Centroid) + lexikalische Überschneidung.
- Schwellen `T_high`/`T_low` (konfigurierbar):
  - `≥ T_high` → `TopicLink(status=vorgeschlagen, methode=auto)` (optional auto-`bestätigt`).
  - dazwischen → in die **Matching-Inbox**.
  - `< T_low` → neues `Topic` vorschlagen (LLM benennt es).
- **Seeding:** `Themenspeicher`/`Abgeschlossene TOPs` einmalig einlesen → Topics + Status
  (`laufend`/`erledigt`/`nicht_priorisiert`) und `TopicLink(methode=seed)` als Startpunkt.
- Topic-Centroid wird bei jeder Bestätigung neu gemittelt.

## Re-Processing
- Einzelne Schritte sind wiederholbar (idempotent über Hash + Status). Bei verbesserten
  Heuristiken/Modellen kann ein Dokument neu ab Schritt 4 verarbeitet werden, ohne bestätigte
  manuelle `TopicLink`s zu verlieren (nur `methode=auto`-Vorschläge werden neu berechnet).
