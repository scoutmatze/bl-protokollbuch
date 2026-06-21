export type ItemTyp = "beschluss" | "info" | "aufgabe" | "diskussion";

export interface Treffer {
  typ: ItemTyp;
  text: string;
  verantwortlich: string | null;
  abstimmung: Record<string, string> | null;
  sitzungsdatum: string | null;
  sitzungstyp: string;
  top_nr: string | null;
  top_titel: string | null;
}

export interface SitzungKopf {
  id: string;
  sitzungsdatum: string | null;
  sitzungstyp: string;
  titel: string | null;
  tops: number;
}

export interface Item {
  typ: ItemTyp;
  text: string;
  verantwortlich: string | null;
  abstimmung: Record<string, string> | null;
}

export interface Top {
  nr: string | null;
  titel: string | null;
  zeit_real_min: number | null;
  zeit_geplant_min: number | null;
  items: Item[];
}

export interface SitzungDetail {
  id: string;
  sitzungsdatum: string | null;
  sitzungstyp: string;
  titel: string | null;
  quelldatei: string;
  tops: Top[];
}

async function get<T>(url: string): Promise<T> {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
  return r.json() as Promise<T>;
}

export const api = {
  suche: (q: string, typ?: string, sort: string = "relevanz") =>
    get<{ anzahl: number; treffer: Treffer[] }>(
      `/api/search?q=${encodeURIComponent(q)}${typ ? `&typ=${typ}` : ""}&sort=${sort}&limit=50`,
    ),
  sitzungen: () => get<{ sitzungen: SitzungKopf[] }>("/api/sitzungen"),
  sitzung: (id: string) => get<SitzungDetail>(`/api/sitzungen/${id}`),
};
