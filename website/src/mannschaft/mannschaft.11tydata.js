import { hatInhalt, dateiname } from "../_includes/hatinhalt.js";
export default {
  layout: "layouts/mannschaft.njk",
  typ: "mannschaft",
  eleventyComputed: {
    permalink: (data) => `/mannschaft/${dateiname(data)}/`,
  },
};
