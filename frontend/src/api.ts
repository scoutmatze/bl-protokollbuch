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

export interface ThemaKopf {
  id: string;
  name: string;
  status: string;
  sitzungen: number;
  von: string | null;
  bis: string | null;
}

export interface VerlaufEintrag {
  section_id: string;
  document_id: string;
  sitzungsdatum: string | null;
  sitzungstyp: string;
  top_nr: string | null;
  top_titel: string | null;
  items: Item[];
}

export interface ThemaDetail {
  id: string;
  name: string;
  status: string;
  verlauf: VerlaufEintrag[];
}

export interface SektionTreffer {
  id: string;
  top_titel: string | null;
  sitzungsdatum: string | null;
  sitzungstyp: string;
  aktuelles_thema: string | null;
}

async function get<T>(url: string): Promise<T> {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
  return r.json() as Promise<T>;
}

async function send<T>(method: string, url: string, body?: unknown): Promise<T> {
  const r = await fetch(url, {
    method,
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
  return r.json() as Promise<T>;
}

export const api = {
  suche: (q: string, typ?: string, sort: string = "relevanz") =>
    get<{ anzahl: number; treffer: Treffer[]; hinweis: string | null }>(
      `/api/search?q=${encodeURIComponent(q)}${typ ? `&typ=${typ}` : ""}&sort=${sort}&limit=50`,
    ),
  sitzungen: () => get<{ sitzungen: SitzungKopf[] }>("/api/sitzungen"),
  sitzung: (id: string) => get<SitzungDetail>(`/api/sitzungen/${id}`),
  themen: (min = 2) => get<{ anzahl: number; themen: ThemaKopf[] }>(`/api/themen?min_sitzungen=${min}`),
  thema: (id: string) => get<ThemaDetail>(`/api/themen/${id}`),

  // Matching-Review
  themaUmbenennen: (id: string, name: string) =>
    send("PATCH", `/api/themen/${id}`, { name }),
  topEntfernen: (themaId: string, sectionId: string) =>
    send("POST", `/api/themen/${themaId}/sections/${sectionId}/ablehnen`),
  topHinzufuegen: (themaId: string, sectionId: string) =>
    send("POST", `/api/themen/${themaId}/sections/${sectionId}`),
  themenZusammenfuehren: (zielId: string, quelleId: string) =>
    send("POST", `/api/themen/${zielId}/merge`, { quelle_id: quelleId }),
  sektionenSuche: (q: string) =>
    get<{ treffer: SektionTreffer[] }>(`/api/sektionen?q=${encodeURIComponent(q)}`),
};
