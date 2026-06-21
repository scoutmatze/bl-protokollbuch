"""Protokoll-Identifikation und Metadaten aus Datei-/Ordnernamen.

Bewusst rein regelbasiert. Grundlage: docs/BESTANDSANALYSE.md (Validierung über
156 echte Protokolle). Wichtig: 'PK'/'PL' wird als abgegrenztes Token erkannt,
nicht als Teilstring (sonst werden Anlagen wie 'Planung' fälschlich erfasst).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

# 'PK' oder 'PL' (Protokoll) als abgegrenztes Token irgendwo im Namen.
RE_PROTO_TOKEN = re.compile(r"(?:^|[ _/.\-])[Pp][KkLl](?:[ _.\-]|$)")
# Datum: YYMMDD am Namensanfang ODER YYYY-MM-DD irgendwo.
RE_YYMMDD = re.compile(r"(?:^|[ _\-])(\d{2})(\d{2})(\d{2})(?:[ _\-]|$)")
RE_ISO = re.compile(r"(20\d{2})-(\d{2})-(\d{2})")

PDF_DOCX = {".pdf", ".docx", ".doc"}


@dataclass
class ProtokollMeta:
    ist_protokoll: bool
    quelldatei: str          # relativer Pfad ab Quellwurzel
    quellformat: str         # 'pdf' | 'docx'
    sitzungsdatum: date | None
    sitzungstyp: str         # 'bl' | 'ebl' | 'ring_bl' | 'ao_ebl'
    epoche: str              # 'flach_2014_2020' | 'monatsordner_2021ff'


def _parse_datum(name: str) -> date | None:
    m = RE_ISO.search(name)
    if m:
        y, mo, d = (int(x) for x in m.groups())
        try:
            return date(y, mo, d)
        except ValueError:
            pass
    m = RE_YYMMDD.search(name)
    if m:
        yy, mo, d = (int(x) for x in m.groups())
        try:
            return date(2000 + yy, mo, d)
        except ValueError:
            return None
    return None


def _parse_typ(kontext: str) -> str:
    t = f" {kontext.lower()} "
    if "ring" in t:
        return "ring_bl"
    if re.search(r"[ _\-]ao[ _\-]", t) or "außerordentlich" in t or "ausserordentlich" in t \
            or "zusätzlich" in t or "zusaetzlich" in t:
        return "ao_ebl"
    if re.search(r"e[ _\-]?bl", t) or "ebl" in t.replace(" ", ""):
        return "ebl"
    return "bl"


def _parse_epoche(rel: Path) -> str:
    # Monatsordner der neueren Epoche: "01 Februar" / "01_Februar".
    for teil in rel.parts:
        if re.match(r"^\d{2}[ _]", teil):
            return "monatsordner_2021ff"
    return "flach_2014_2020"


def identify(path: Path, root: Path) -> ProtokollMeta:
    """Klassifiziert eine Datei. `root` = Wurzel des Protokollbestands."""
    rel = path.relative_to(root)
    name = path.name
    ext = path.suffix.lower()
    # Kontext für Typ-Erkennung: Dateiname + direkter Elternordner (z. B. "eBLs").
    kontext = f"{rel.parent.name} {name}"
    ist = ext in PDF_DOCX and bool(RE_PROTO_TOKEN.search(name))
    return ProtokollMeta(
        ist_protokoll=ist,
        quelldatei=str(rel).replace("\\", "/"),
        quellformat="docx" if ext in {".docx", ".doc"} else "pdf",
        sitzungsdatum=_parse_datum(name) or _parse_datum(rel.parent.name),
        sitzungstyp=_parse_typ(kontext),
        epoche=_parse_epoche(rel),
    )
