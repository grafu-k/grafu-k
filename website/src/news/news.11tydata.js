import { hatInhalt, dateiname } from "../_includes/hatinhalt.js";
export default {
  layout: "layouts/eintrag.njk",
  typ: "news",
  eleventyComputed: {
    permalink: (data) => (hatInhalt(data) ? `/news/${dateiname(data)}/` : false),
  },
};
