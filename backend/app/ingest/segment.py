"""TOP-Segmentierung — zerlegt ein Protokoll in Tagesordnungspunkte.

Heuristik:
1. Body-Beginn = nach der I/B/E-Legende ("I = Information"); davor steht die
   Tagesordnung (gleiche Nummern als Inhaltsverzeichnis) -> wird so übersprungen.
2. Im Body sind TOP-Überschriften nummerierte Zeilen ("1)", "1.", "TOP 1 ...").
   Inhaltsverzeichnis-Zeilen (mit "....."-Füllpunkten) werden ausgeschlossen.
3. Nur monoton steigende Nummern werden als echte Überschriften akzeptiert
   (verhindert Fehltreffer durch Aufzählungen im Fließtext).

Validiert (awk-Proxy, siehe BESTANDSANALYSE): neue Epoche fehlerfrei (z. B. 25/25
TOPs 2024), alte Epoche ~85–90 %, kurze eBL/DOCX schwächer.
TODO (Robustifizierung): Body-Überschriften gegen die geparste Tagesordnung
abgleichen — eliminiert Fehltreffer (z. B. Satz "5. ...") und findet verpasste
TOPs wieder. Dafür Tagesordnung als erwartete Nummernmenge extrahieren.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from .extract import Extracted, Line

RE_LEGENDE = re.compile(r"I\s*=\s*Information", re.IGNORECASE)
# Zwei Überschriften-Formen:
#  - mit Satzzeichen:  "1) Titel"  /  "1. Titel"  /  "TOP 1. Titel"
#  - mit TOP-Präfix ohne Satzzeichen: "TOP 1 Titel"  (alte eBLs)
RE_TOP_NUM = re.compile(r"^\s*(\d{1,2})[\.\)]\s+(\S.*)$")
RE_TOP_WORD = re.compile(r"^\s*TOP\s*(\d{1,2})[\.\):]?\s+(\S.*)$")


def _match_head(text: str):
    m = RE_TOP_WORD.match(text) or RE_TOP_NUM.match(text)
    return (int(m.group(1)), m.group(2)) if m else None
RE_DOTS = re.compile(r"\.{4,}")                     # Inhaltsverzeichnis-Füllpunkte
RE_ZEIT = re.compile(r"\((?:(\d+)\s*von\s*)?(\d+)?\s*Min\.?\)", re.IGNORECASE)


@dataclass
class Section:
    nr: int
    titel: str
    text: str
    seite_von: int
    seite_bis: int
    zeit_real_min: int | None = None
    zeit_geplant_min: int | None = None
    lines: list[Line] = field(default_factory=list)   # Body-Zeilen (ohne Überschrift)


def _body_start(lines: list[Line]) -> int:
    for i, ln in enumerate(lines):
        if RE_LEGENDE.search(ln.text):
            return i + 1
    return 0  # Fallback: kein Legenden-Marker -> ganzer Text


def _clean_titel(roh: str) -> tuple[str, int | None, int | None]:
    real = geplant = None
    m = RE_ZEIT.search(roh)
    if m:
        if m.group(1):
            real = int(m.group(1))
        if m.group(2):
            geplant = int(m.group(2))
        roh = roh[: m.start()].strip()
    return roh.strip(" .-"), real, geplant


def segment(ex: Extracted) -> list[Section]:
    lines = ex.lines
    start = _body_start(lines)
    body = lines[start:]

    # Überschriften-Kandidaten mit monoton steigender Nummer einsammeln.
    heads: list[tuple[int, int, str]] = []  # (index_in_body, nr, titel_roh)
    last = 0
    for i, ln in enumerate(body):
        if RE_DOTS.search(ln.text):
            continue
        m = _match_head(ln.text)
        if not m:
            continue
        nr, titel_roh = m
        if nr <= last or nr > last + 5:   # nur plausible nächste Nummer
            continue
        heads.append((i, nr, titel_roh))
        last = nr

    sections: list[Section] = []
    for h, (idx, nr, titel_roh) in enumerate(heads):
        end = heads[h + 1][0] if h + 1 < len(heads) else len(body)
        block = body[idx:end]
        titel, real, geplant = _clean_titel(titel_roh)
        txt = "\n".join(l.text for l in block[1:]).strip()
        sections.append(Section(
            nr=nr, titel=titel, text=txt,
            seite_von=block[0].page, seite_bis=block[-1].page,
            zeit_real_min=real, zeit_geplant_min=geplant,
            lines=block[1:],
        ))
    return sections
