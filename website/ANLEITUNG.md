# Website Feuerwehr St. Stefan ob Leoben – Anleitung

Die Website ist eine schnelle, statische Seite (kein WordPress mehr). Alle Inhalte
liegen als einfache Textdateien in diesem Ordner. Bearbeitet wird bequem über die
**Redaktionsoberfläche unter `https://www.ff-ststefan.at/admin/`**.

---

## 1. Inhalte bearbeiten (für die Redaktion)

1. `https://www.ff-ststefan.at/admin/` öffnen (oder Menü **Links → Admin-Login**).
2. Mit GitHub anmelden.
3. Links den Bereich wählen:

| Bereich | Was ist das? |
|---|---|
| **Einsätze** | Einsatzberichte. Neue Einsätze erscheinen automatisch ganz oben unter *Einsätze* und auf der Startseite. |
| **News** | Beiträge wie Wehrversammlung, Babystorch, Wissenstest … |
| **Fahrzeuge** | Aktuelle und historische Fahrzeuge (Häkchen *Historisches Fahrzeug*). |
| **Mannschaft** | Kommando, Ausschuss, Aktivstand … – Personen hinzufügen, löschen, per Drag & Drop sortieren. |
| **Seiten** | Startseite (Zitat, Titelbild, Video), Spenden, Links, Impressum, Datenschutz, Wetter. |
| **Einstellungen** | E-Mail, Telefon, Facebook/Instagram/YouTube. |

### Neuen Einsatz anlegen
1. **Einsätze → Neue(r/s) Einsatz**
2. *Titel* (z. B. „Bahndammbrand“), *Einsatzstichwort* (z. B. „🔥 B09-Hecken-Wiese // Bahndammbrand 🔥“),
   *Datum* und *Uhrzeit* ausfüllen.
3. *Titelbild* hochladen, weitere Fotos unter *Bildergalerie* hinzufügen.
4. Bericht schreiben (Vorlage ist schon eingetragen). Eine neue Zeile = Zeilenumbruch,
   eine Leerzeile = neuer Absatz.
5. Oben auf **Veröffentlichen** klicken. Nach ca. 1–2 Minuten ist der Einsatz online.

Tipp: Ein Einsatz **ohne Text und ohne Galerie** wird nur als Kachel gezeigt (ohne eigene Seite) –
praktisch für kurze Meldungen wie „T07-Unwetter // Baum über Straße“.

### Fotos
* Fotos direkt vom Handy hochladen ist ok. Ideal sind Fotos bis ca. 2000 Pixel Breite
  (Facebook-Bilder passen perfekt). Vorschaubilder werden automatisch verkleinert.
* Alle Bilder liegen im Ordner `src/bilder/`.

---

## 2. Technik (für Admins)

* **Generator:** [Eleventy](https://www.11ty.dev/) – baut aus den Textdateien fertige HTML-Seiten.
* **Redaktion:** [Decap CMS](https://decapcms.org/) – speichert Änderungen direkt im GitHub-Repository.
* **Hosting:** Netlify (Konfiguration in `../netlify.toml`). Jede Änderung im Repository löst
  automatisch einen neuen Build aus.

### Ordnerstruktur
```
website/
├─ src/
│  ├─ einsaetze/      ← ein .md pro Einsatz (Dateiname: JJJJ-MM-TT-titel.md)
│  ├─ news/           ← ein .md pro News-Beitrag
│  ├─ fahrzeuge/      ← ein .md pro Fahrzeug
│  ├─ mannschaft/     ← ein .md pro Gruppe (Personen-Liste)
│  ├─ seiten/         ← Spenden, Links, Impressum, Datenschutz, Wetter
│  ├─ _data/          ← site.json (Kontakt), startseite.json, navigation.js (Menü)
│  ├─ bilder/         ← alle Fotos
│  ├─ assets/         ← CSS, JavaScript, Logo, Schrift
│  ├─ admin/          ← Redaktionsoberfläche (config.yml)
│  └─ _redirects      ← Weiterleitungen alter WordPress-Adressen
└─ eleventy.config.js
```

### Lokal starten
```bash
cd website
npm install
npm start            # Vorschau auf http://localhost:8080
npm run cms          # (2. Terminal) Redaktion lokal ohne Login: http://localhost:8080/admin/
npm run build        # fertige Seite in _site/
```

### Online stellen (einmalig)
1. Auf [netlify.com](https://www.netlify.com/) mit GitHub anmelden → **Add new site → Import from Git**
   → dieses Repository wählen. Build-Einstellungen kommen automatisch aus `netlify.toml`.
2. Für den Login in `/admin/`: in GitHub unter *Settings → Developer settings → OAuth Apps* eine
   OAuth-App anlegen (Callback-URL `https://api.netlify.com/auth/done`), dann in Netlify unter
   *Site configuration → Access & security → OAuth → Install provider → GitHub* Client-ID und Secret eintragen.
3. Redakteure brauchen einen GitHub-Account mit Schreibrecht auf das Repository.
4. Domain `ff-ststefan.at` in Netlify unter *Domain management* hinzufügen und beim Domain-Anbieter
   die DNS-Einträge wie von Netlify angezeigt setzen.

Wird ein anderes Repository oder ein anderer Branch verwendet, in `src/admin/config.yml`
die Zeilen `repo:` und `branch:` sowie die Pfade (`website/src/…`) anpassen.

### Menü ändern
`src/_data/navigation.js`. Die Untermenüs *Fahrzeuge* und *Mannschaft* werden automatisch aus den
Inhalten erzeugt.
