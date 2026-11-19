import fs from "node:fs";
import path from "node:path";
import markdownIt from "markdown-it";
import Image from "@11ty/eleventy-img";

const md = markdownIt({ html: true, breaks: true, linkify: true });

const MONATE = ["Jänner", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober", "November", "Dezember"];

function toDate(d) {
  if (d instanceof Date) return d;
  return new Date(String(d).slice(0, 10) + "T00:00:00Z");
}

const byDateDesc = (a, b) => {
  const d = toDate(b.data.date) - toDate(a.data.date);
  if (d) return d;
  return String(b.data.uhrzeit || "").localeCompare(String(a.data.uhrzeit || ""));
};

export default function (eleventyConfig) {
  eleventyConfig.setLibrary("md", md);

  // Statische Dateien 1:1 kopieren
  eleventyConfig.addPassthroughCopy({ "src/assets": "assets" });
  eleventyConfig.addPassthroughCopy({ "src/bilder": "bilder" });
  eleventyConfig.addPassthroughCopy({ "src/admin/config.yml": "admin/config.yml" });
  eleventyConfig.addPassthroughCopy({ "src/_redirects": "_redirects" });

  // ---------- Sammlungen ----------
  const hasPage = (item) => item.data.permalink !== false && item.url;
  eleventyConfig.addCollection("einsaetze", (api) => api.getFilteredByGlob("src/einsaetze/*.md").sort(byDateDesc));
  eleventyConfig.addCollection("news", (api) => api.getFilteredByGlob("src/news/*.md").sort(byDateDesc));
  eleventyConfig.addCollection("fahrzeuge", (api) =>
    api.getFilteredByGlob("src/fahrzeuge/*.md").sort((a, b) => (a.data.reihenfolge || 99) - (b.data.reihenfolge || 99))
  );
  eleventyConfig.addCollection("mannschaft", (api) =>
    api.getFilteredByGlob("src/mannschaft/*.md").sort((a, b) => (a.data.reihenfolge || 99) - (b.data.reihenfolge || 99))
  );

  // ---------- Filter ----------
  eleventyConfig.addFilter("md", (s) => (s ? md.render(String(s)) : ""));
  eleventyConfig.addFilter("datum", (d) => {
    const x = toDate(d);
    return `${String(x.getUTCDate()).padStart(2, "0")}.${String(x.getUTCMonth() + 1).padStart(2, "0")}.${x.getUTCFullYear()}`;
  });
  eleventyConfig.addFilter("datumLang", (d) => {
    const x = toDate(d);
    return `${x.getUTCDate()}. ${MONATE[x.getUTCMonth()]} ${x.getUTCFullYear()}`;
  });
  eleventyConfig.addFilter("isoDatum", (d) => toDate(d).toISOString().slice(0, 10));
  eleventyConfig.addFilter("jahr", (d) => toDate(d).getUTCFullYear());
  eleventyConfig.addFilter("nachJahr", (items) => {
    const groups = [];
    for (const it of items) {
      const y = toDate(it.data.date).getUTCFullYear();
      let g = groups.find((g) => g.jahr === y);
      if (!g) groups.push((g = { jahr: y, items: [] }));
      g.items.push(it);
    }
    return groups;
  });
  eleventyConfig.addFilter("where", (items, key, value) => items.filter((i) => i.data[key] === value));
  eleventyConfig.addFilter("mitSeite", (items) => items.filter(hasPage));
  eleventyConfig.addFilter("nachbarn", (items, url) => {
    const list = items.filter(hasPage);
    const i = list.findIndex((x) => x.url === url);
    return { neuer: i > 0 ? list[i - 1] : null, aelter: i >= 0 && i < list.length - 1 ? list[i + 1] : null };
  });
  eleventyConfig.addFilter("limit", (arr, n) => (arr || []).slice(0, n));
  eleventyConfig.addFilter("zeilen", (s) =>
    String(s || "")
      .split("\n")
      .map((z) => z.trim())
      .filter(Boolean)
  );
  eleventyConfig.addFilter("alarmtext", (data) => {
    if (data.kartentext) return data.kartentext;
    const d = toDate(data.date);
    const ds = `${String(d.getUTCDate()).padStart(2, "0")}.${String(d.getUTCMonth() + 1).padStart(2, "0")}.${d.getUTCFullYear()}`;
    return `Sirenenalarm am ${ds}${data.uhrzeit ? ` um ${data.uhrzeit} Uhr` : ""} 🚨`;
  });

  // ---------- Bilder: verkleinerte Vorschaubilder für Kacheln ----------
  eleventyConfig.addAsyncShortcode("vorschau", async (src, alt = "", breite = 600, klasse = "") => {
    if (!src) return "";
    const file = path.join("src", decodeURI(src));
    if (!src.startsWith("/") || !fs.existsSync(file)) {
      return `<img src="${src}" alt="${alt}" loading="lazy" decoding="async" class="${klasse}">`;
    }
    const meta = await Image(file, {
      widths: [breite, breite * 2],
      formats: ["webp", "jpeg"],
      outputDir: "_site/img/",
      urlPath: "/img/",
      sharpJpegOptions: { quality: 78 },
      sharpWebpOptions: { quality: 75 },
    });
    return Image.generateHTML(meta, {
      alt,
      class: klasse,
      sizes: `(max-width: 700px) 100vw, ${breite}px`,
      loading: "lazy",
      decoding: "async",
    });
  });

  eleventyConfig.addFilter("menue", (nav, collections) =>
    nav.map((p) => {
      if (p.auto === "fahrzeuge")
        return { ...p, unter: [{ titel: "Übersicht", url: "/fahrzeuge/" }, ...collections.fahrzeuge.filter((f) => !f.data.historisch && hasPage(f)).map((f) => ({ titel: f.data.title, url: f.url }))] };
      if (p.auto === "mannschaft")
        return { ...p, unter: collections.mannschaft.filter((m) => m.data.im_menue !== false).map((m) => ({ titel: m.data.title, url: m.url })) };
      return { ...p, unter: p.unter || [] };
    })
  );

  eleventyConfig.addGlobalData("jetzt", () => new Date());

  return {
    dir: { input: "src", output: "_site", includes: "_includes", data: "_data" },
    markdownTemplateEngine: false,
    htmlTemplateEngine: "njk",
  };
}
