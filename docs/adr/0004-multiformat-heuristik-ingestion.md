# ADR 0004 — Multi-Format-Ingestion, heuristik-first

**Status:** akzeptiert · **Datum:** 2026-06-20

## Kontext
Die [Bestandsanalyse](../BESTANDSANALYSE.md) zeigt: Protokolle liegen als **PDF *und* DOCX**
vor, Anlagen zusätzlich als XLSX/EML. Der innere Aufbau ist über 12 Jahre konstant und trägt
**strukturierte Marker** (`I`/`B`/`E`) sowie eine **WER-Spalte** (Verantwortliche/Frist).

## Entscheidung
1. **Format-Router** statt reiner PDF-Pipeline: PyMuPDF (PDF), python-docx (DOCX),
   openpyxl (XLSX), stdlib `email` (EML); OCR-Fallback (`ocrmypdf`) für Scans.
2. **Heuristik zuerst, LLM nur zur Korrektur/Glättung.** Segmentierung aus Nummerierung/Layout,
   Klassifikation aus I/B/E-Markern, Verantwortliche/Frist aus der WER-Spalte. Das LLM fasst
   zusammen und füllt Lücken, ratet aber nicht die Grundstruktur.

## Begründung
- Das lokale LLM ([ADR 0001](0001-lokales-llm.md)) ist schwächer als Cloud-Modelle —
  heuristik-first reduziert die Fehleranfälligkeit dort, wo die Daten ohnehin strukturiert sind.
- Multi-Format ist nicht optional: Die neuesten „Final"-Protokolle sind DOCX.

## Konsequenzen
- **+** Robuste, erklärbare Extraktion mit klarer Provenienz (`ibe_marker` bleibt erhalten).
- **+** LLM-Ausgaben gegen striktes JSON-Schema validiert → weniger Halluzination.
- **−** Zwei epochenspezifische Parser nötig (flach 2014–2020 / Monatsordner 2021ff).
