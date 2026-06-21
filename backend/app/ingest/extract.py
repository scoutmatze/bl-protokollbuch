"""Format-Router: Protokoll -> Text + (bei PDF) Zeilen mit X-Koordinaten.

Die X-Koordinaten brauchen wir später, um die rechte WER-Spalte vom INHALT zu
trennen (items.py). DOCX hat keine Koordinaten; dort liefern Tabellenzellen die
Spaltenstruktur.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Line:
    text: str
    page: int
    y: float = 0.0
    x0: float | None = None   # linke Kante (None bei DOCX)
    x1: float | None = None   # rechte Kante


@dataclass
class Extracted:
    text: str
    lines: list[Line] = field(default_factory=list)
    page_count: int = 0
    page_width: float | None = None   # für Spalten-Schwelle (PDF)


def extract_pdf(path: Path) -> Extracted:
    import fitz  # PyMuPDF

    doc = fitz.open(path)
    lines: list[Line] = []
    full: list[str] = []
    page_width = None
    for pno, page in enumerate(doc, start=1):
        if page_width is None:
            page_width = page.rect.width
        # Wörter gruppiert nach (block, line) zu Textzeilen mit Bounding-Box.
        words = page.get_text("words")  # (x0,y0,x1,y1,wort,block,line,wordno)
        buckets: dict[tuple[int, int], list[tuple]] = {}
        for w in words:
            buckets.setdefault((w[5], w[6]), []).append(w)
        for key in sorted(buckets, key=lambda k: (min(w[1] for w in buckets[k]), k)):
            ws = sorted(buckets[key], key=lambda w: w[0])
            txt = " ".join(w[4] for w in ws).strip()
            if not txt:
                continue
            x0 = min(w[0] for w in ws)
            x1 = max(w[2] for w in ws)
            y = min(w[1] for w in ws)
            lines.append(Line(text=txt, page=pno, y=y, x0=x0, x1=x1))
            full.append(txt)
    doc.close()
    return Extracted(text="\n".join(full), lines=lines, page_count=pno,
                     page_width=page_width)


def _iter_par_texts(container):
    """Alle Absatztexte in Dokumentreihenfolge, rekursiv in Tabellenzellen hinein.

    Wichtig: Der zweispaltige INHALT|WER-Aufbau ist in Word meist eine Tabelle.
    Jede TOP-Überschrift ist ein eigener Absatz in einer Zelle — den müssen wir
    als eigene Zeile erhalten, damit die Segmentierung greift.
    """
    from docx.table import Table
    from docx.text.paragraph import Paragraph

    for block in container.iter_inner_content():
        if isinstance(block, Paragraph):
            yield block.text
        elif isinstance(block, Table):
            for row in block.rows:
                for cell in row.cells:
                    yield from _iter_par_texts(cell)


def extract_docx(path: Path) -> Extracted:
    import docx  # python-docx

    d = docx.Document(str(path))
    lines: list[Line] = []
    full: list[str] = []
    seen_consecutive = None
    for txt in _iter_par_texts(d):
        txt = txt.strip()
        if not txt or txt == seen_consecutive:  # zusammengeführte Zellen -> Duplikate
            continue
        seen_consecutive = txt
        lines.append(Line(text=txt, page=1))
        full.append(txt)
    return Extracted(text="\n".join(full), lines=lines, page_count=1)


def extract(path: Path) -> Extracted:
    if path.suffix.lower() in {".docx", ".doc"}:
        return extract_docx(path)
    return extract_pdf(path)
