// Prüft, ob ein Eintrag eine eigene Detailseite bekommt (Text oder Bildergalerie vorhanden).
import fs from "node:fs";
export function hatInhalt(data) {
  if (data.galerie && data.galerie.length) return true;
  try {
    const raw = fs.readFileSync(data.page.inputPath, "utf8");
    const body = raw.replace(/^---[\s\S]*?\n---/, "").trim();
    return body.length > 0;
  } catch {
    return true;
  }
}
export const dateiname = (data) => data.page.inputPath.split("/").pop().replace(/\.md$/, "");
