import { hatInhalt, dateiname } from "../_includes/hatinhalt.js";
export default {
  layout: "layouts/fahrzeug.njk",
  typ: "fahrzeug",
  eleventyComputed: {
    permalink: (data) => (hatInhalt(data) ? `/fahrzeuge/${dateiname(data)}/` : false),
  },
};
