import { hatInhalt, dateiname } from "../_includes/hatinhalt.js";
export default {
  layout: "layouts/eintrag.njk",
  typ: "einsatz",
  eleventyComputed: {
    permalink: (data) => (hatInhalt(data) ? `/einsaetze/${dateiname(data)}/` : false),
  },
};
