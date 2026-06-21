# Bestandsanalyse

Befunde aus einer Stichproben-Analyse des echten Dateibestands
(`…/Bundesleitung - Dokumente/BL-Sitzungen`), Stand 2026-06-20.
Diese Analyse ist die empirische Grundlage für [DATENMODELL.md](DATENMODELL.md)
und [PIPELINE.md](PIPELINE.md).

## Umfang

- **361 PDF** + **378 DOCX** Dateien.
- Davon ca. **128** eigentliche Sitzungsprotokolle (Dateiname enthält `PK`/`PL` = Protokoll).
- Der große Rest sind **Anlagen** (Synopsen, Strategiepapiere, Tabellen, E-Mails, Bilder).

## Zwei Struktur-Epochen

| Epoche | Ablage | Protokoll-Format | Beispiel |
|---|---|---|---|
| **2014 – ~2020** | flache Jahresordner | PDF | `2014/140214_pk_bl.pdf`, `190130_ebl_pk.pdf` |
| **~2021 – 2026** | Monatsordner + Anlagen | oft **DOCX** „Final", teils PDF | `2024/01_Februar/240216 BL PK_Final.pdf` |

**Konsequenz:** Die Ingestion braucht (a) einen **Format-Router** (PDF *und* DOCX, dazu
XLSX/EML als Anlagen) und (b) zwei kleine **epochenspezifische Namens-/Layout-Parser**.

## Ablagestruktur der neueren Epoche

Pro Monatsordner typischerweise:

```
2025/01 Februar/
├─ 250214_BL_PL_Final.pdf        ← das Protokoll
├─ 250214 TO BL.pdf              ← Tagesordnung (separat)
├─ Organisatorisches.xlsx
├─ BL I Themenspeicher 2025.docx ← Themen-Tracker (siehe unten)
├─ TOP 3 Ausbildung/            ← pro TOP ein Unterordner mit Anlagen
│   ├─ Baustein 2b Synopse_final.docx
│   ├─ Gesprächsprotokoll MF-AGA ZAT.docx
│   └─ Beschlussfassung … Rahmenkonzept Modul 2b.eml
├─ TOP 4 Prisma/
└─ …
```

→ **TOP-Unterordner liefern eine fertige thematische Gruppierung samt Anlagen.**
Ordnername ≈ TOP-Titel; Inhalt → `Section.attachments`.

## Sitzungstypen (aus Datei-/Ordnernamen ableitbar)

| Kürzel | Bedeutung |
|---|---|
| `BL` | Bundesleitung (Präsenzsitzung) |
| `eBL` | erweiterte / digitale Bundesleitung (Telko/Zoom) |
| `Ring-BL` | gemeinsame Sitzung im Ring deutscher Pfadfinderverbände |
| `ao` / `zusätzliche` | außerordentliche Sitzung |

Sitzungsdatum steckt als `YYMMDD` im Dateinamen (`240216` → 16.02.2024).

## Innerer Aufbau der Protokolle — über 12 Jahre konstant

1. **Kopf:** Teilnehmende · Entschuldigt · Gäste · Verteiler · Folgetermin · Dateiname
2. **Feste Legende:** `*) I = Information · B = Beratung · E = Entscheidung`
3. **Tagesordnung** mit nummerierten TOPs (neuere zusätzlich mit Zeitbudget, z. B. „(24 von 20 Min.)")
4. **Zweispaltiger Fließtext:** linke Spalte `INHALT`, rechte Spalte `WER` (Verantwortliche/Frist),
   jede Zeile mit `I`/`B`/`E`-Marker.

### Warum das wichtig ist

Die **I/B/E-Marker** und die **WER-Spalte** sind bereits strukturierte Daten:

- `E` (Entscheidung) ≈ **Beschluss**, `I` ≈ **Information**, `B` ≈ **Beratung/Diskussion**.
- Die WER-Spalte liefert **Verantwortliche und Fristen** direkt.

→ Klassifikation und Verantwortlichkeiten sind **größtenteils heuristisch** aus Layout + Markern
ableitbar. Das **LLM glättet nur**, statt frei zu raten — das senkt die Abhängigkeit von der
(lokal etwas schwächeren) LLM-Qualität deutlich.

## Kontinuitäts-Dokumente = Ground Truth fürs Matching

Es existieren menschgepflegte, sitzungsübergreifende Themen-Tracker:

- `BL Themenspeicher <Jahr>.docx`
- `BL Abgeschlossene TOPs <Jahr>.docx`
- `BL Themen die nicht priorisiert wurden für <Jahr>.docx`

Diese Dateien lassen sich nutzen, um **Topics samt Status** (`laufend` / `erledigt` /
`nicht_priorisiert`) vorzubelegen und das automatische Matching zu **validieren** — ein
erheblicher Beschleuniger.

## Validierung am Gesamtbestand (regelbasiert, ohne LLM)

`scripts/probe_extraction.sh` hat **alle** Protokolle ausgelesen (PDF via `pdftotext`,
DOCX via `docx2txt`) und die Struktursignale gemessen. Ergebnis über **156 echte
Protokolle** (Identifikation: „PK"/„PL" als abgegrenztes Token):

| Signal | Trefferquote |
|---|---|
| I/B/E-Legende erkannt | **96 %** (151/156) |
| Tagesordnung erkannt | **92 %** (144/156) |
| ≥ 3 TOPs erkannt | **97 %** (152/156) |
| Auslesbar ohne OCR | **100 %** (0 Scans) |

→ Die rein regelbasierte Extraktion trägt bei ~95 % der Protokolle. Die Ausreißer sind
v. a. kurze eBL-/Sondersitzungen mit abweichendem Aufbau → Fallback + manuelles Review.
Das rechtfertigt die Strategie „v1 ohne KI" ([KONZEPT.md](KONZEPT.md#10-offene-punkte--risiken)).

### Ergebnis des Python-Parsers (Phase 1)
Der echte Parser (`backend/app/ingest/`, PyMuPDF + python-docx, korrekte Umlaute) wurde
im Container über alle 157 erkannten Protokolle laufen gelassen:

| TOPs erkannt | Protokolle |
|---|---|
| 10+ | 82 |
| 5–9 | 46 |
| 1–4 | 27 |
| 0 | **2** |

→ **155/157 (98,7 %)** sauber segmentiert. Die 2 Reste: eine quasi leere Mini-eBL und
`Anleitung BL-PK.docx` (gar kein Protokoll — Fehl-ID über das Token „BL-**PK**", korrigiert
sich durch 0 TOPs selbst). Beispiele: BL 2024 25/25 TOPs, BL 2014 13/13, eBL 2017 6 TOPs.

Zwei Befunde flossen direkt in den Parser:
- **DOCX-Inhalt steht in Tabellen** → Absätze in Dokumentreihenfolge inkl. Tabellenzellen
  auslesen (sonst nur ~16 Zeilen statt des ganzen Protokolls).
- **Alte eBLs nutzen `TOP 1 Titel`** (ohne Punkt/Klammer) → zweite Überschriften-Form.

### Item-Extraktion (Beschlüsse / Infos / Aufgaben / Diskussion)
Innerhalb der TOPs zieht `items.py` die Nutzlast aus drei Signalen:
1. **Text-Detektor für Beschlüsse** — neuere Protokolle markieren explizit:
   „ENTSCHEIDUNG (einstimmig): …", „Beschluss …: einstimmig angenommen". Verlässlichstes
   Signal; Abstimmungsmodus/-ergebnis wird mitgeparst.
2. **I/B/E-Randmarker** (linke Spalte, ältere Epoche): E→beschluss, B→diskussion, I→info.
3. **WER-Spalte** (rechts, über X-Koordinate): Verantwortliche → `aufgabe`.

Aggregat über alle 157 Protokolle: **22.362 Items** — davon **792 Beschlüsse**,
**1.440 Aufgaben** (mit Verantwortlichen), 575 Diskussionen, 19.555 Infos. Das ist die
durchsuchbare Grundlage für „liste alle Beschlüsse zu …".

### Harte Regel: Protokoll-Identifikation
Welche Datei *das Protokoll* ist, wird über **„PK" oder „PL" als abgegrenztes Token**
erkannt (Regex `(^|[ _/.])(p[kl])([ _.]|$)`), **nicht** als Teilstring — sonst werden
Anhänge wie „**Pl**anung", „Jahres**pl**an", „BL-**PK**" fälschlich als Protokoll gewertet.

## Technische Stolpersteine

- **Encoding/Umlaute:** Mit manchen PDF-Extraktoren werden Umlaute zerstört
  (`Begrüßung` → `Begr��ung`). PyMuPDF liefert hier sauberer; korrektes UTF-8/Umlaut-Handling
  gehört **verpflichtend in die Test-Suite**, sonst leidet die Volltextsuche.
- **Gescannte Altprotokolle** brauchen ggf. OCR (`ocrmypdf`/Tesseract) — Qualität schwankt.
- **DOCX-Protokolle** der neueren Epoche müssen nativ verarbeitet werden (`python-docx`),
  nicht über einen PDF-Umweg.
