"""Item-Extraktion innerhalb eines TOP — Beschlüsse / Infos / Aufgaben / Diskussion.

Drei Signale, robust kombiniert (siehe BESTANDSANALYSE):
1. Text-Detektor für Beschlüsse: "ENTSCHEIDUNG (einstimmig): ...", "Beschluss ...:
   einstimmig angenommen". Verlässlichstes Signal, v. a. in der neueren Epoche.
2. I/B/E-Randmarker (linke Spalte): E->beschluss, B->diskussion, I->info. Ältere Epoche.
3. WER-Spalte (rechts, x-Koordinate): Verantwortliche -> verantwortlich/aufgabe.

PDF liefert X-Koordinaten (Spaltentrennung möglich); DOCX nicht — dort wird jeder
Absatz als eigener Block behandelt und ohne WER-Spalte klassifiziert.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from .extract import Line

RE_MARKER = re.compile(r"^[IBE](?:/[IBE])*$")
RE_BULLET = re.compile(r"^\s*(?:[-•▪◦○*→]|o\s|○)\s*")
RE_NOISE = re.compile(r"^(?:Seite\s+\d+\s+von\s+\d+|WER|BIS|WANN|BIS WANN|INHALT|\*\).*)$", re.I)
RE_DECISION = re.compile(
    r"(?i)^\s*(?:o\s+)?(?:ENTSCHEIDUNG|Beschluss|Entscheidung)\b"
    r"|\((?:einstimmig|mehrheitlich)[^)]*\)\s*:"
    r"|(?:einstimmig|mehrheitlich)\s+(?:angenommen|dafür|abgelehnt)"
)
RE_VOTE = re.compile(r"(?i)\b(einstimmig|mehrheitlich)\b")
RE_RESULT = re.compile(r"(?i)\b(angenommen|abgelehnt|festgelegt|vertagt|beschlossen)\b")
RE_LEAD_BULLET = re.compile(r"^\s*(?:[-•▪◦○*→]|o)\s+")

MARKER_TYP = {"E": "beschluss", "B": "diskussion", "I": "info"}


@dataclass
class Item:
    typ: str                       # beschluss | info | aufgabe | diskussion
    text: str
    verantwortlich: str | None = None
    frist: str | None = None
    ibe_marker: str | None = None
    abstimmung: dict | None = None


def extract_items(lines: list[Line], page_width: float | None) -> list[Item]:
    has_coords = page_width is not None and any(l.x0 is not None for l in lines)
    wer_min = 0.70 * page_width if has_coords else None
    marker_max = 0.18 * page_width if has_coords else None

    markers: list[Line] = []
    wer: list[Line] = []
    inhalt: list[Line] = []
    for l in lines:
        t = l.text.strip()
        if not t or RE_NOISE.match(t):
            continue
        if has_coords and l.x0 is not None and l.x0 >= wer_min:
            wer.append(l)
        elif RE_MARKER.match(t) and (not has_coords or (l.x0 is not None and l.x0 < marker_max)):
            markers.append(l)
        else:
            inhalt.append(l)

    # --- Blöcke bilden -------------------------------------------------------
    blocks: list[list[Line]] = []
    for l in inhalt:
        t = l.text.strip()
        start = not blocks
        if not start:
            if RE_BULLET.match(t) or RE_DECISION.search(t):
                start = True
            elif has_coords:
                prev = blocks[-1][-1]
                if l.page != prev.page or (l.y - prev.y) > 22:  # Absatzabstand
                    start = True
            else:
                start = True  # DOCX: jeder Absatz ein eigener Block
        if start:
            blocks.append([l])
        else:
            blocks[-1].append(l)

    # --- Blöcke zu Items klassifizieren -------------------------------------
    items: list[Item] = []
    for bl in blocks:
        text = " ".join(x.text.strip() for x in bl).strip()
        text = RE_LEAD_BULLET.sub("", text).strip()
        is_decision = bool(RE_DECISION.search(text))
        if len(text) < 25 and not is_decision:
            continue

        typ = "info"
        marker = None
        abst = None
        if is_decision:
            typ = "beschluss"
            mv = RE_VOTE.search(text)
            mr = RE_RESULT.search(text)
            if mv or mr:
                abst = {}
                if mv:
                    abst["modus"] = mv.group(1).lower()
                if mr:
                    abst["ergebnis"] = mr.group(1).lower()
        elif has_coords and markers:
            y0, pg = bl[0].y, bl[0].page
            near = [m for m in markers if m.page == pg and abs(m.y - y0) < 10]
            if near:
                marker = near[0].text.strip()
                typ = MARKER_TYP.get(marker.split("/")[0], "info")

        verantw = None
        if has_coords and wer:
            y0, y1, pg = bl[0].y, bl[-1].y, bl[0].page
            ws = [w.text.strip() for w in wer
                  if w.page == pg and y0 - 6 <= w.y <= y1 + 6 and not RE_NOISE.match(w.text.strip())]
            if ws:
                verantw = " ".join(ws)
        if verantw and typ == "info":
            typ = "aufgabe"

        items.append(Item(typ=typ, text=text, verantwortlich=verantw,
                          ibe_marker=marker, abstimmung=abst))
    return items
