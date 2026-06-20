# Datenmodell

Referenz-Implementierung: [`backend/app/models.py`](../backend/app/models.py).
Grundlage: [BESTANDSANALYSE.md](BESTANDSANALYSE.md).

## ER-Überblick

```
User ──< AuditLog
Document 1──< Section 1──< Item
Section 1──< Attachment
Section >──< Topic   (über TopicLink, Status-behaftet)
Section >──< Tag     (SectionTag)
Topic   >──< Tag     (TopicTag)
```

## Entitäten

### Document — eine Sitzung / ein Protokoll
| Feld | Typ | Anmerkung |
|---|---|---|
| `id` | uuid | |
| `sitzungsdatum` | date | aus Dateiname (`YYMMDD`) bzw. Kopf |
| `gremium` | text | i. d. R. „Bundesleitung" |
| `sitzungstyp` | enum | `bl` / `ebl` / `ring_bl` / `ao_ebl` |
| `titel` | text | z. B. „BL I/2025" |
| `quelldatei` | text | relativer Pfad im Bestand |
| `quellformat` | enum | `pdf` / `docx` |
| `sha256` | text (unique) | Dedup |
| `seiten` | int | |
| `roh_text` | text | extrahierter Volltext |
| `status` | enum | `neu` / `extrahiert` / `segmentiert` / `fertig` / `fehler` |
| `epoche` | enum | `flach_2014_2020` / `monatsordner_2021ff` — steuert den Parser |

### Section — ein TOP innerhalb einer Sitzung
| Feld | Typ | Anmerkung |
|---|---|---|
| `id` | uuid | |
| `document_id` | uuid → Document | |
| `top_nr` | text | „7", „20" — nicht immer rein numerisch |
| `überschrift` | text | TOP-Titel |
| `reihenfolge` | int | Sortierung innerhalb der Sitzung |
| `text` | text | Fließtext des TOP |
| `seite_von` / `seite_bis` | int | für Deep-Link zur Quelle |
| `zeit_geplant_min` / `zeit_real_min` | int? | aus „(24 von 20 Min.)", neuere Epoche |
| `embedding` | vector(768) | semantische Suche/Matching |
| `tsv` | tsvector | Volltext (deutsch) |

### Item — extrahierte Einheit innerhalb eines TOP
| Feld | Typ | Anmerkung |
|---|---|---|
| `id` | uuid | |
| `section_id` | uuid → Section | |
| `typ` | enum | `beschluss` / `info` / `aufgabe` / `diskussion` |
| `text` | text | |
| `verantwortlich` | text? | aus WER-Spalte |
| `frist` | text? | aus WER-Spalte (oft Freitext, daher text) |
| `ibe_marker` | enum? | ursprünglicher `I`/`B`/`E`-Marker (Provenienz) |
| `abstimmung` | jsonb? | z. B. `{dafür, dagegen, enthaltung}` falls vorhanden |
| `confidence` | float | Extraktions-Vertrauen, steuert Review |
| `embedding` | vector(768) | |

> **Mapping:** `E`→`beschluss`, `I`→`info`, `B`→`diskussion`. `aufgabe` entsteht, wenn die
> WER-Spalte eine Verantwortliche/Frist nennt (To-Do), unabhängig vom Marker.

### Attachment — Anlage zu einer Section
| Feld | Typ | Anmerkung |
|---|---|---|
| `id` | uuid | |
| `section_id` | uuid → Section | aus TOP-Unterordner |
| `dateiname` | text | |
| `pfad` | text | relativer Pfad im Bestand |
| `format` | text | docx/xlsx/eml/… |
| `roh_text` | text? | extrahiert, falls textbasiert |

### Topic — verschmolzener Themenstrang
| Feld | Typ | Anmerkung |
|---|---|---|
| `id` | uuid | |
| `name` | text | z. B. „Ausbildung" |
| `beschreibung` | text? | |
| `status` | enum | `laufend` / `erledigt` / `veranstaltung` / `einmalig` / `nicht_priorisiert` |
| `embedding` | vector(768) | Repräsentant (Centroid) fürs Matching |

### TopicLink — Zuordnung Section ↔ Topic (Status-behaftet)
| Feld | Typ | Anmerkung |
|---|---|---|
| `id` | uuid | |
| `section_id` | uuid → Section | |
| `topic_id` | uuid → Topic | |
| `match_score` | float | 0..1 |
| `methode` | enum | `auto` / `manuell` / `seed` (aus Themenspeicher) |
| `status` | enum | `vorgeschlagen` / `bestätigt` / `abgelehnt` |
| `bestätigt_von` | uuid → User? | |
| `bestätigt_am` | timestamptz? | |

> Unique-Constraint auf (`section_id`, `topic_id`). Ein abgelehnter Link bleibt als
> `abgelehnt` erhalten, damit dasselbe Matching nicht erneut vorgeschlagen wird.

### Tag + Verknüpfungen
- `Tag(id, name unique, farbe, auto bool)`
- `SectionTag(section_id, tag_id)`, `TopicTag(topic_id, tag_id)` — n:m.

### User
| Feld | Typ | Anmerkung |
|---|---|---|
| `id` | uuid | |
| `email` | text unique | |
| `passwort_hash` | text | Argon2 |
| `rolle` | enum | `admin` / `editor` / `reader` |
| `aktiv` | bool | Einladungs-/Sperr-Flow |

### AuditLog
`id, user_id, aktion, objekt_typ, objekt_id, vorher jsonb, nachher jsonb, zeitpunkt` —
protokolliert insbesondere Änderungen an `TopicLink` und `Tag`.

## Indizes (Pflicht)

- `Document.sha256` unique · `Document.sitzungsdatum`
- `Section.embedding` → `ivfflat`/`hnsw` (pgvector) · `Section.tsv` → GIN
- `Item.typ` (Filter „nur Beschlüsse") · `Item.embedding` → Vektorindex
- `TopicLink (section_id, topic_id)` unique · `TopicLink.status` (Inbox-Filter)
