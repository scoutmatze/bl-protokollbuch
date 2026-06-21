"""Tests für die Protokoll-Identifikation — synthetisch, ohne echte Protokolle.

Deckt die in BESTANDSANALYSE dokumentierten Namensmuster beider Epochen ab,
inkl. der harten Regel 'PK/PL als Token, nicht Teilstring'.
"""
from datetime import date
from pathlib import Path

from app.ingest.identify import identify

ROOT = Path("/data")


def _id(rel: str):
    return identify(ROOT / rel, ROOT)


def test_alte_epoche_pdf():
    m = _id("2014/140214_pk_bl.pdf")
    assert m.ist_protokoll
    assert m.sitzungsdatum == date(2014, 2, 14)
    assert m.sitzungstyp == "bl"
    assert m.epoche == "flach_2014_2020"
    assert m.quellformat == "pdf"


def test_alte_epoche_ebl():
    m = _id("2019/190130_ebl_pk.pdf")
    assert m.ist_protokoll
    assert m.sitzungsdatum == date(2019, 1, 30)
    assert m.sitzungstyp == "ebl"


def test_iso_datum_im_namen():
    m = _id("2019/2019-12-13 BL PK.pdf")
    assert m.sitzungsdatum == date(2019, 12, 13)
    assert m.sitzungstyp == "bl"


def test_neue_epoche_docx_pl():
    m = _id("2025/01 Februar/250214_BL_PL_Final.pdf")
    assert m.ist_protokoll
    assert m.sitzungsdatum == date(2025, 2, 14)
    assert m.epoche == "monatsordner_2021ff"


def test_neue_epoche_ebl_docx():
    m = _id("2025/eBLs/250122 eBL I/250122 eBL PK.docx")
    assert m.ist_protokoll
    assert m.sitzungstyp == "ebl"
    assert m.quellformat == "docx"


def test_ao_ebl():
    m = _id("2024/eBLs/240704 zusätzliche eBL/240704 eBL zusätzl. PK.docx")
    assert m.ist_protokoll
    assert m.sitzungstyp == "ao_ebl"


def test_anlage_planung_ist_kein_protokoll():
    # 'Planung'/'Plan' enthalten 'pl' nur als Teilstring -> KEIN Protokoll.
    assert not _id("2024/05_November/TOP 07 Jahresplanung/Jahresplanung.docx").ist_protokoll
    assert not _id("2021/1_Februar/Plan PiW Päckchen.docx").ist_protokoll
    assert not _id("2025/01 Februar/TOP 7 BV2025/BV93_Drucksachenplan.pdf").ist_protokoll
