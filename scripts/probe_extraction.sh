#!/usr/bin/env bash
# Struktur-Probe über alle Protokolle — rein regelbasiert, ohne Python/LLM.
# Extrahiert jedes Protokoll (PDF via pdftotext, DOCX via docx2txt) und misst
# Signale, an denen sich ablesen lässt, wie gut die Heuristik trägt:
#   - text_len    : Länge des extrahierten Texts (sehr klein => vermutlich Scan/OCR nötig)
#   - hat_legende : enthält die I/B/E-Legende ("I = Information")
#   - hat_to      : Tagesordnung/Inhalt erkannt
#   - top_count   : Anzahl TOP-artiger Überschriften
# Ausgabe: CSV (Pfad als $1, Default data/extraction_probe.csv) + Zusammenfassung.
# Liest die Quelldateien nur lesend; verändert nichts.
set -u

SRC="${SRC:-/c/Users/MathiasFazekas/BUNDESAMT SANKT GEORG E.V. DPSG/Bundesleitung - Dokumente/BL-Sitzungen}"
OUT="${1:-data/extraction_probe.csv}"
mkdir -p "$(dirname "$OUT")"

extract() {  # $1 = datei -> Text auf stdout (Quelle bleibt unberührt)
  case "${1,,}" in
    *.pdf)
      pdftotext -layout "$1" - 2>/dev/null ;;
    *.docx)
      # docx2txt schreibt zwingend eine .txt neben die Quelle -> Temp-Kopie nutzen
      local td; td="$(mktemp -d)"
      cp "$1" "$td/d.docx"
      docx2txt "$td/d.docx" >/dev/null 2>&1
      cat "$td/d.txt" 2>/dev/null
      rm -rf "$td" ;;
  esac
}

echo "pfad;format;text_len;hat_legende;hat_to;top_count" > "$OUT"

n=0; scans=0; ok_legende=0; ok_to=0
while IFS= read -r -d '' f; do
  txt="$(extract "$f")"
  len=${#txt}
  leg=$(printf '%s' "$txt" | grep -ciE "I *= *Information" || true)
  to=$(printf '%s' "$txt"  | grep -ciE "Tagesordnung|^Inhalt|Inhalt *\.\.\." || true)
  # TOP-artige Überschriften: "1." / "1)" / "TOP 1" am Zeilenanfang
  tops=$(printf '%s' "$txt" | grep -ciE "^[[:space:]]*(TOP[[:space:]]+)?[0-9]{1,2}[\.\)]" || true)
  fmt="${f##*.}"; fmt="${fmt,,}"
  rel="${f#"$SRC"/}"
  echo "${rel};${fmt};${len};${leg};${to};${tops}" >> "$OUT"
  n=$((n+1))
  [ "$len" -lt 600 ] && scans=$((scans+1))
  [ "$leg" -gt 0 ] && ok_legende=$((ok_legende+1))
  [ "$to" -gt 0 ] && ok_to=$((ok_to+1))
done < <(find "$SRC" \( -iname "*.pdf" -o -iname "*.docx" \) \( -iname "*pk*" -o -iname "*pl*" \) ! -iname "*TO*" -print0)

echo
echo "==== Zusammenfassung ($n Protokolle) ===="
echo "  mit I/B/E-Legende : $ok_legende / $n"
echo "  mit Tagesordnung  : $ok_to / $n"
echo "  vermutl. Scan (text<600 Zeichen): $scans"
echo "  CSV: $OUT"
