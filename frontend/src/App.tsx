import { useEffect, useState } from "react";
import {
  api, type Item, type SitzungDetail, type SitzungKopf, type ThemaDetail,
  type ThemaKopf, type Treffer,
} from "./api";

const TYP_LABEL: Record<string, string> = {
  beschluss: "Beschluss",
  aufgabe: "Aufgabe",
  diskussion: "Diskussion",
  info: "Info",
};

function Badge({ typ }: { typ: string }) {
  return <span className={`badge badge-${typ}`}>{TYP_LABEL[typ] ?? typ}</span>;
}

function Abstimmung({ a }: { a: Record<string, string> | null }) {
  if (!a) return null;
  const parts = [a.modus, a.ergebnis].filter(Boolean);
  return parts.length ? <span className="vote">· {parts.join(", ")}</span> : null;
}

function ItemZeile({ it }: { it: Item }) {
  return (
    <li className="item">
      <Badge typ={it.typ} />
      <span className="item-text">{it.text}</span>
      {it.verantwortlich && <span className="wer">→ {it.verantwortlich}</span>}
      <Abstimmung a={it.abstimmung} />
    </li>
  );
}

function Suche() {
  const [q, setQ] = useState("");
  const [typ, setTyp] = useState("");
  const [sort, setSort] = useState("relevanz");
  const [treffer, setTreffer] = useState<Treffer[]>([]);
  const [status, setStatus] = useState<string>("");

  async function run(e?: React.FormEvent) {
    e?.preventDefault();
    if (q.trim().length < 2) return;
    setStatus("Suche …");
    try {
      const r = await api.suche(q.trim(), typ || undefined, sort);
      setTreffer(r.treffer);
      setStatus(`${r.anzahl} Treffer${r.hinweis ? ` · ${r.hinweis}` : ""}`);
    } catch (err) {
      setStatus(`Fehler: ${(err as Error).message}`);
    }
  }

  return (
    <div>
      <form className="suchleiste" onSubmit={run}>
        <input
          autoFocus
          placeholder={'Suche – mehrere Begriffe = UND · "genaue phrase" · wort OR wort · -ausschluss'}
          value={q}
          onChange={(e) => setQ(e.target.value)}
        />
        <select value={typ} onChange={(e) => setTyp(e.target.value)}>
          <option value="">alle Typen</option>
          <option value="beschluss">nur Beschlüsse</option>
          <option value="aufgabe">nur Aufgaben</option>
          <option value="diskussion">nur Diskussionen</option>
          <option value="info">nur Infos</option>
        </select>
        <select value={sort} onChange={(e) => setSort(e.target.value)} title="Sortierung">
          <option value="relevanz">Relevanz</option>
          <option value="datum">Datum (neueste zuerst)</option>
        </select>
        <button type="submit">Suchen</button>
      </form>
      <p className="status">{status}</p>
      <ul className="trefferliste">
        {treffer.map((t, i) => (
          <li key={i} className="treffer">
            <div className="treffer-meta">
              <Badge typ={t.typ} />
              <span className="datum">{t.sitzungsdatum ?? "—"}</span>
              <span className="topref">
                {t.sitzungstyp.toUpperCase()} · TOP {t.top_nr}: {t.top_titel}
              </span>
            </div>
            <div className="treffer-text">
              {t.text}
              {t.verantwortlich && <span className="wer">→ {t.verantwortlich}</span>}
              <Abstimmung a={t.abstimmung} />
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}

function Sitzungen() {
  const [liste, setListe] = useState<SitzungKopf[]>([]);
  const [detail, setDetail] = useState<SitzungDetail | null>(null);

  useEffect(() => {
    api.sitzungen().then((r) => setListe(r.sitzungen)).catch(() => setListe([]));
  }, []);

  if (detail) {
    return (
      <div>
        <button className="back" onClick={() => setDetail(null)}>← zurück</button>
        <h2>{detail.titel}</h2>
        <p className="status">{detail.sitzungsdatum} · {detail.quelldatei}</p>
        {detail.tops.map((top, i) => (
          <section key={i} className="top">
            <h3>TOP {top.nr}: {top.titel}</h3>
            <ul className="itemliste">
              {top.items.map((it, j) => <ItemZeile key={j} it={it} />)}
            </ul>
          </section>
        ))}
      </div>
    );
  }

  return (
    <table className="sitzungstabelle">
      <thead><tr><th>Datum</th><th>Typ</th><th>Titel</th><th>TOPs</th></tr></thead>
      <tbody>
        {liste.map((s) => (
          <tr key={s.id} onClick={() => api.sitzung(s.id).then(setDetail)}>
            <td>{s.sitzungsdatum ?? "—"}</td>
            <td>{s.sitzungstyp.toUpperCase()}</td>
            <td>{s.titel}</td>
            <td>{s.tops}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function Themen() {
  const [liste, setListe] = useState<ThemaKopf[]>([]);
  const [detail, setDetail] = useState<ThemaDetail | null>(null);

  useEffect(() => {
    api.themen(2).then((r) => setListe(r.themen)).catch(() => setListe([]));
  }, []);

  if (detail) {
    return (
      <div>
        <button className="back" onClick={() => setDetail(null)}>← zurück</button>
        <h2>{detail.name} <span className="badge badge-info">{detail.verlauf.length} TOPs</span></h2>
        {detail.verlauf.map((v, i) => (
          <section key={i} className="top">
            <h3>{v.sitzungsdatum} · {v.sitzungstyp.toUpperCase()} · TOP {v.top_nr}: {v.top_titel}</h3>
            <ul className="itemliste">
              {v.items.map((it, j) => <ItemZeile key={j} it={it} />)}
            </ul>
          </section>
        ))}
      </div>
    );
  }

  return (
    <>
      <p className="status">Wiederkehrende Themen über mehrere Sitzungen (ab 2 Sitzungen).</p>
      <table className="sitzungstabelle">
        <thead><tr><th>Thema</th><th>Sitzungen</th><th>Zeitraum</th></tr></thead>
        <tbody>
          {liste.map((t) => (
            <tr key={t.id} onClick={() => api.thema(t.id).then(setDetail)}>
              <td>{t.name}</td>
              <td>{t.sitzungen}</td>
              <td>{t.von} – {t.bis}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </>
  );
}

export function App() {
  const [tab, setTab] = useState<"suche" | "themen" | "sitzungen">("suche");
  return (
    <div className="app">
      <header>
        <h1>BL-Protokollbuch</h1>
        <nav>
          <button className={tab === "suche" ? "on" : ""} onClick={() => setTab("suche")}>Suche</button>
          <button className={tab === "themen" ? "on" : ""} onClick={() => setTab("themen")}>Themen</button>
          <button className={tab === "sitzungen" ? "on" : ""} onClick={() => setTab("sitzungen")}>Sitzungen</button>
        </nav>
      </header>
      <main>
        {tab === "suche" && <Suche />}
        {tab === "themen" && <Themen />}
        {tab === "sitzungen" && <Sitzungen />}
      </main>
    </div>
  );
}
