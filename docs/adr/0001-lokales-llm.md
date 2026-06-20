# ADR 0001 — Lokales LLM (self-hosted) statt Cloud

**Status:** akzeptiert · **Datum:** 2026-06-20

## Kontext
Die Protokolle enthalten personenbezogene Daten (Namen, Beschlüsse zu Personen) →
DSGVO-relevant. Für PDF-Auslesen, Themen-Matching und Zusammenfassen wird ein LLM benötigt.

## Entscheidung
KI-Verarbeitung läuft **vollständig lokal** über **Ollama** auf eigener Infrastruktur
(LLM für Extraktion/Glättung, Embedding-Modell für Suche/Matching). Keine Cloud-API.

## Begründung
- Daten verlassen die eigene Infrastruktur nicht → kein AVV/Drittlandtransfer nötig.
- Bewusst gewählt vom Auftraggeber gegenüber „Cloud mit AVV" und „Hybrid".

## Konsequenzen
- **+** Datenschutz unkritisch; volle Kontrolle.
- **−** Geringere Modellqualität als Cloud → Architektur **heuristik-first**
  (siehe [ADR 0004](0004-multiformat-heuristik-ingestion.md)) und **Human-in-the-Loop** in Phase 2.
- **−** VPS braucht ausreichend RAM/ggf. GPU; konkrete Modellgröße wird vor Phase 1 anhand der
  Hardware festgelegt.
