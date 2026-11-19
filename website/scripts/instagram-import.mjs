// Holt neue Beiträge vom Instagram-Account der Feuerwehr und legt sie als
// Einsatz oder News auf der Website an (inkl. Fotos).
//
// Aufruf:  INSTAGRAM_TOKEN=... node scripts/instagram-import.mjs
// Optional: INSTAGRAM_API_BASE (nur für Tests), DRY_RUN=1
//
// Einstellungen + bereits importierte Beiträge: src/_data/instagram.json
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import sharp from "sharp";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const SRC = path.join(ROOT, "src");
const STATE_FILE = path.join(SRC, "_data", "instagram.json");
const API = process.env.INSTAGRAM_API_BASE || "https://graph.instagram.com";
const TOKEN = process.env.INSTAGRAM_TOKEN;
const DRY = !!process.env.DRY_RUN;

const state = JSON.parse(fs.readFileSync(STATE_FILE, "utf8"));
state.importiert ||= [];

// ---------- Hilfsfunktionen ----------
const EMOJI = /[\p{Extended_Pictographic}️‍]/gu;
const ohneEmoji = (s) => s.replace(EMOJI, "").replace(/\s+/g, " ").trim();

function slugify(s) {
  return ohneEmoji(s)
    .toLowerCase()
    .replace(/ä/g, "ae").replace(/ö/g, "oe").replace(/ü/g, "ue").replace(/ß/g, "ss")
    .normalize("NFKD").replace(/[̀-ͯ]/g, "")
    .replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "")
    .slice(0, 60).replace(/-+$/, "") || "beitrag";
}

// Datum/Uhrzeit in österreichischer Zeit
function wienZeit(iso) {
  const d = new Date(iso.replace(/([+-]\d{2})(\d{2})$/, "$1:$2"));
  const t = Object.fromEntries(
    new Intl.DateTimeFormat("de-AT", { timeZone: "Europe/Vienna", year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", hour12: false })
      .formatToParts(d)
      .map((p) => [p.type, p.value])
  );
  return { datum: `${t.year}-${t.month}-${t.day}`, uhrzeit: `${t.hour}:${t.minute}` };
}

const yamlWert = (v) => (typeof v === "string" ? JSON.stringify(v) : String(v));
function frontmatter(obj) {
  let s = "---\n";
  for (const [k, v] of Object.entries(obj)) {
    if (v === undefined || v === "" || (Array.isArray(v) && !v.length)) continue;
    if (Array.isArray(v)) s += `${k}:\n${v.map((x) => `  - ${yamlWert(x)}`).join("\n")}\n`;
    else s += `${k}: ${yamlWert(v)}\n`;
  }
  return s + "---\n";
}

const ALARMCODE = /(?:^|[\s(])((?:B|T|S|BEAS)\d{0,2}[A-Z]?-[\wÄÖÜäöüß.-]+)/;
export function istEinsatz(text) {
  if (/#news\b/i.test(text)) return false;
  if (/#einsatz\b/i.test(text)) return true;
  return /sirenenalarm/i.test(text) || ALARMCODE.test(text);
}

// Zerlegt die Bildunterschrift in Titel, Stichwort, Text
export function zerlege(caption, timestamp) {
  const zeilen = (caption || "").replace(/\r/g, "").split("\n").map((z) => z.trimEnd());
  // reine Hashtag-Zeilen am Ende / dazwischen entfernen
  const text = zeilen.filter((z) => !/^\s*(#[\p{L}\p{N}_]+\s*)+$/u.test(z));
  while (text.length && !text[0].trim()) text.shift();
  while (text.length && !text[text.length - 1].trim()) text.pop();

  const erste = text[0] || "";
  const einsatz = istEinsatz(caption || "");
  const zeit = wienZeit(timestamp);
  let datum = zeit.datum, uhrzeit = zeit.uhrzeit;
  const m = (caption || "").match(/(\d{1,2})\.(\d{1,2})\.(\d{4})(?:\D{1,8}?(\d{1,2})[:.](\d{2})\s*Uhr)?/);
  if (einsatz && m) {
    datum = `${m[3]}-${m[2].padStart(2, "0")}-${m[1].padStart(2, "0")}`;
    uhrzeit = m[4] ? `${m[4].padStart(2, "0")}:${m[5]}` : "";
  }

  let titel = ohneEmoji(erste).replace(/[!.:]+$/, "") || (einsatz ? "Einsatz" : "Neuigkeiten");
  if (titel.length > 90) titel = titel.slice(0, 87).replace(/\s+\S*$/, "") + " …";
  let stichwort;
  if (einsatz) {
    const z = text.find((x) => ALARMCODE.test(x) && x.length < 120);
    stichwort = z ? z.replace(/^.*?(?:🚨\s*)/u, "").trim() || z.trim() : erste.trim();
    if (!EMOJI.test(stichwort)) {
      const sym = /^\s*(B|BEAS)\d/.test(ohneEmoji(stichwort)) ? "🔥" : /^\s*T\d/.test(ohneEmoji(stichwort)) ? "🛠️" : "";
      if (sym) stichwort = `${sym} ${stichwort} ${sym}`;
    }
    EMOJI.lastIndex = 0;
    if (/^sirenenalarm/i.test(titel) && z) titel = ohneEmoji(stichwort).split("//").pop().trim() || titel;
  }
  // Rest als Markdown (erste Zeile ist schon Titel); "#" am Zeilenanfang maskieren
  const rest = text.slice(1).join("\n").replace(/^(\s*)#/gm, "$1\\#").trim();
  return { einsatz, titel, stichwort, datum, uhrzeit, text: rest };
}

async function api(pfad, params = {}) {
  const u = new URL(API + pfad);
  for (const [k, v] of Object.entries({ ...params, access_token: TOKEN })) u.searchParams.set(k, v);
  const r = await fetch(u);
  const j = await r.json().catch(() => ({}));
  if (!r.ok || j.error) throw new Error(`Instagram-API ${pfad}: ${r.status} ${j.error?.message || ""}`);
  return j;
}

async function bildSpeichern(url, name) {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`Bild ${r.status}`);
  const buf = Buffer.from(await r.arrayBuffer());
  const datei = path.join(SRC, "bilder", name);
  if (!DRY)
    await sharp(buf, { failOn: "none" }).rotate().resize({ width: 1920, height: 1920, fit: "inside", withoutEnlargement: true }).jpeg({ quality: 80, mozjpeg: true }).toFile(datei);
  return `/bilder/${name}`;
}

function eindeutig(ordner, basis) {
  let n = basis, i = 2;
  while (fs.existsSync(path.join(SRC, ordner, n + ".md"))) n = `${basis}-${i++}`;
  return n;
}

// ---------- Ablauf ----------
async function main() {
  if (!TOKEN) {
    console.log("Kein INSTAGRAM_TOKEN gesetzt – Import übersprungen.");
    return;
  }
  // Token verlängern (gültig 60 Tage ab Verlängerung)
  if (!process.env.INSTAGRAM_API_BASE) {
    try {
      const r = await api("/refresh_access_token", { grant_type: "ig_refresh_token" });
      if (r.access_token && r.access_token !== TOKEN && process.env.GITHUB_OUTPUT)
        fs.appendFileSync(process.env.GITHUB_OUTPUT, `neuer_token=${r.access_token}\n`);
      console.log(`Token verlängert, gültig noch ${Math.round((r.expires_in || 0) / 86400)} Tage.`);
    } catch (e) {
      console.warn("Token konnte nicht verlängert werden:", e.message);
    }
  }

  const felder = "id,caption,media_type,media_url,thumbnail_url,permalink,timestamp,children{media_type,media_url,thumbnail_url}";
  const { data = [] } = await api("/me/media", { fields: felder, limit: String(state.max_pro_lauf || 25) });
  const ab = state.ab ? new Date(state.ab + "T00:00:00Z") : new Date(0);
  const neu = data
    .filter((p) => !state.importiert.includes(p.id) && new Date(p.timestamp.replace(/([+-]\d{2})(\d{2})$/, "$1:$2")) >= ab)
    .reverse(); // älteste zuerst
  console.log(`${data.length} Beiträge gelesen, ${neu.length} neu.`);

  for (const p of neu) {
    const t = zerlege(p.caption, p.timestamp);
    if (t.einsatz && !state.einsaetze) t.einsatz = false;
    if (!t.einsatz && !state.news) { state.importiert.push(p.id); continue; }

    const medien = p.media_type === "CAROUSEL_ALBUM" ? p.children?.data || [] : [p];
    const bilder = [];
    for (const [i, m] of medien.entries()) {
      const url = m.media_type === "VIDEO" ? m.thumbnail_url : m.media_url;
      if (!url) continue;
      try {
        bilder.push(await bildSpeichern(url, `ig-${p.id}-${i + 1}.jpg`));
      } catch (e) {
        console.warn(`  Bild ${i + 1} von ${p.id} fehlgeschlagen: ${e.message}`);
      }
    }
    const hatVideo = medien.some((m) => m.media_type === "VIDEO");
    let body = t.text;
    body += `\n\n[${hatVideo ? "Video" : "Beitrag"} auf Instagram ansehen](${p.permalink})`;
    body = body.trim() + "\n";

    const ordner = t.einsatz ? "einsaetze" : "news";
    const name = eindeutig(ordner, `${t.datum}-${slugify(t.titel)}`);
    const fm = t.einsatz
      ? { title: t.titel, stichwort: t.stichwort, date: t.datum, uhrzeit: t.uhrzeit, bild: bilder[0], galerie: bilder, instagram: p.permalink }
      : { title: t.titel, date: t.datum, bild: bilder[0], galerie: bilder, instagram: p.permalink };
    const inhalt = frontmatter(fm) + "\n" + body;
    console.log(`  + ${ordner}/${name}.md (${bilder.length} Bilder)`);
    if (DRY) console.log(inhalt);
    else fs.writeFileSync(path.join(SRC, ordner, name + ".md"), inhalt);
    state.importiert.push(p.id);
  }
  if (!DRY) fs.writeFileSync(STATE_FILE, JSON.stringify(state, null, 2) + "\n");
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  main().catch((e) => {
    console.error(e.message);
    process.exit(1);
  });
}
