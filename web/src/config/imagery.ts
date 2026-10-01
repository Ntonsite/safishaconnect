import hero480 from "../assets/images/brand/hero-professional-cleaning-480.webp";
import hero800 from "../assets/images/brand/hero-professional-cleaning-800.webp";
import hero1200 from "../assets/images/brand/hero-professional-cleaning-1200.webp";
import mobile480 from "../assets/images/brand/hero-professional-cleaning-mobile-480.webp";
import mobile800 from "../assets/images/brand/hero-professional-cleaning-mobile-800.webp";
import dar480 from "../assets/images/brand/dar-es-salaam-480.webp";
import dar800 from "../assets/images/brand/dar-es-salaam-800.webp";
import dar1200 from "../assets/images/brand/dar-es-salaam-1200.webp";

/** Replace these launch assets with commissioned photography; provenance is in docs/IMAGE_SOURCES.md. */
export const brandImagery = {
  hero: {
    src: hero800,
    srcSet: `${hero480} 480w, ${hero800} 800w, ${hero1200} 1200w`,
    mobileSrcSet: `${mobile480} 480w, ${mobile800} 800w`,
    altKey: "landing.imagery.heroAlt",
    width: 800, height: 1000,
  },
  dar: {
    src: dar800,
    srcSet: `${dar480} 480w, ${dar800} 800w, ${dar1200} 1200w`,
    altKey: "landing.imagery.darAlt",
    width: 800, height: 450,
  },
} as const;
