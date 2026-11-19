// Hauptmenü. Fahrzeuge und Mannschaft werden automatisch aus den Inhalten ergänzt (siehe base.njk).
export default [
  { titel: "Aktuelles", url: "/news/", unter: [ { titel: "News", url: "/news/" }, { titel: "Einsätze", url: "/einsaetze/" } ] },
  { titel: "Fahrzeuge", url: "/fahrzeuge/", auto: "fahrzeuge" },
  { titel: "Mannschaft", url: "/mannschaft/", auto: "mannschaft" },
  { titel: "Spenden", url: "/spenden/", unter: [ { titel: "Spenden", url: "/spenden/" } ] },
  { titel: "Chronik", url: "/chronik/", unter: [ { titel: "Historische Fahrzeuge", url: "/fahrzeuge/historisch/" }, { titel: "Verstorbene Kameraden", url: "/mannschaft/verstorbene-kameraden/" } ] },
  { titel: "Links", url: "/links/", unter: [
    { titel: "Spenden", url: "/spenden/" },
    { titel: "Facebook", url: "https://www.facebook.com/FF.St.Stefan" },
    { titel: "Instagram", url: "https://www.instagram.com/feuerwehr_st.stefan_ob_leoben/" },
    { titel: "Youtube", url: "https://www.youtube.com/@ff-st.stefan" },
    { titel: "Admin-Login", url: "/admin/" }
  ] }
];
