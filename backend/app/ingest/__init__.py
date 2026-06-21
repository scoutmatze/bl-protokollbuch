"""Regelbasierte Ingestion-Pipeline (Phase 1, ohne LLM).

Module:
- identify : Ist eine Datei ein Protokoll? Metadaten (Datum/Typ/Epoche) aus Pfad/Name.
- extract  : Format-Router PDF/DOCX -> Text (+ Wort-Koordinaten bei PDF).
- segment  : Zerlegung in TOPs (Tagesordnung + Nummerierung).
- items    : I/B/E-Klassifikation + WER-Spalte (folgt).
- pipeline : Orchestrierung; CLI gibt strukturiertes JSON aus.
"""
