"""Tests für die Item-Extraktion — synthetisch, ohne echte Protokolle.

Deckt die drei Signale ab: Text-Beschluss-Detektor (+ Abstimmung), I/B/E-Randmarker,
WER-Spalte (Verantwortliche -> Aufgabe).
"""
from app.ingest.extract import Line
from app.ingest.items import extract_items

PW = 595.0


def test_beschluss_per_textdetektor():
    lines = [Line("ENTSCHEIDUNG (einstimmig): Tagesordnung wird festgelegt", page=1, y=10, x0=100, x1=400)]
    items = extract_items(lines, PW)
    assert len(items) == 1
    assert items[0].typ == "beschluss"
    assert items[0].abstimmung == {"modus": "einstimmig", "ergebnis": "festgelegt"}


def test_beschluss_per_randmarker():
    lines = [
        Line("E", page=1, y=10, x0=70, x1=78),
        Line("Die BL entscheidet, das Rahmenkonzept wie vorgelegt anzunehmen.", page=1, y=10, x0=100, x1=420),
    ]
    items = extract_items(lines, PW)
    assert items[0].typ == "beschluss"
    assert items[0].ibe_marker == "E"


def test_aufgabe_per_wer_spalte():
    lines = [
        Line("Annka erstellt einen Entwurf und bespricht ihn in der PL.", page=1, y=10, x0=100, x1=420),
        Line("SB/JH", page=1, y=10, x0=520, x1=540),
    ]
    items = extract_items(lines, PW)
    assert items[0].typ == "aufgabe"
    assert items[0].verantwortlich == "SB/JH"


def test_footer_wird_ignoriert():
    lines = [
        Line("Seite 3 von 13", page=1, y=795, x0=462, x1=520),
        Line("Wir besprechen ausführlich das weitere Vorgehen im Detail.", page=1, y=10, x0=100, x1=420),
    ]
    items = extract_items(lines, PW)
    assert len(items) == 1
    assert items[0].typ == "info"
