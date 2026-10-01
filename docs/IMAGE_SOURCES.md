# SafishaCon photography sources

Retrieved and license pages reviewed: **2026-10-01**. All production photographs are local WebP assets in `web/src/assets/images/brand/`. References and responsive variants are centralized in `web/src/config/imagery.ts`.

## Selected launch photography

| Asset | Original source / creator | Usage basis | SafishaCon placement |
|---|---|---|---|
| `hero-professional-cleaning-*.webp` (including mobile variants) | [Woman Wearing a Jumper Cleaning a Glass Window](https://www.pexels.com/photo/woman-wearing-a-jumper-cleaning-a-glass-window-6197114/), **Tima Miroshnichenko**, Pexels photo 6197114; original 3753 ? 5629 | [Pexels License](https://www.pexels.com/license/): free website/commercial use and modification; attribution optional. No endorsement, offensive portrayal, trademark use or stock redistribution. | Landing hero; general illustrative brand photography. The source establishes neither Tanzania nor East Africa. The depicted person is **not identified as a SafishaCon provider**. |
| `dar-es-salaam-*.webp` | [A city with many buildings](https://unsplash.com/photos/a-city-with-many-buildings-y1bnAADWAqk), **Okra Amps (@oamps12)**, Unsplash. Source caption: ?Shot from Reagent Estate?; explicit location Dar es Salaam, Tanzania; published 2022-06-11 | [Unsplash License](https://unsplash.com/license/): free commercial use, downloading and modification; attribution optional. No sale of unmodified images or competing image collection. | Landing service areas; caption identifies the city only. It does not claim pictured buildings are customers or that the view depicts every listed neighbourhood. |

Download URLs used for high-resolution working copies:
- Hero: `https://images.pexels.com/photos/6197114/pexels-photo-6197114.jpeg?auto=compress&cs=tinysrgb&w=1800`
- City: `https://images.unsplash.com/photo-1654941348480-217757d5f933?auto=format&fit=max&w=2000&q=85`

No watermarks, generative alterations, invented identities, portraits in testimonials, or competitor images are used. These are launch illustrations; commission original local photography using the accompanying shoot guide.

## Research and curation

Research covered Tanzanian cleaning professionals, Dar apartments/interiors/offices, East African cleaning teams, Black cleaning professionals, equipment details, and Dar urban photography. Local cleaning-company and social-media images lacked transferable permission and were not downloaded. Paid stock without an acquired license, AI imagery, safari imagery, low-resolution city imagery, and cold-climate interiors were excluded.

The final direction uses a deliberate monochrome editorial hero with quiet green UI; the daylight city photograph is a documentary location cue. Text sits beside images. Services, process, trust and provider types retain their informative icons. Provider recruitment was evaluated: the available team image had a visibly foreign timber house and winter surroundings, so it was rejected. No extra photograph was forced into recruitment, final CTA, authenticated dashboards or booking forms.

### Downloaded research candidates (not shipped)

All were retrieved 2026-10-01 for inspection. Pexels candidates share the [Pexels License](https://www.pexels.com/license/). Temporary previews are research-only; no app references them.

| Source page | Creator | Decision |
|---|---|---|
| [Black woman wiping table, 5331102](https://www.pexels.com/photo/black-woman-wiping-table-with-napkin-in-morning-5331102/) | Monstera Production | Rejected: casual cropped clothing and incomplete professional context. |
| [Woman cleaning her living room, 6197050](https://www.pexels.com/photo/woman-cleaning-her-living-room-6197050/) | Tima Miroshnichenko | Rejected: cold-climate fireplace setting. |
| [Cleaners walking with equipment, 6196677](https://www.pexels.com/photo/cleaners-walking-while-holding-cleaning-equipment-6196677/) | Tima Miroshnichenko | Rejected: winter setting and foreign residential architecture. |
| [Woman cleaning the house, 6195198](https://www.pexels.com/photo/woman-cleaning-the-house-6195198/) | Tima Miroshnichenko | Rejected: fireplace / winter interior. |
| [Woman in gray shirt wiping window, 6195281](https://www.pexels.com/photo/woman-in-gray-shirt-wiping-the-glass-window-6195281/) | Tima Miroshnichenko | Rejected: a better representation match was available. |
| [Person cleaning bathroom sink, 4098576](https://www.pexels.com/photo/person-cleaning-the-bathroom-sink-4098576/) | Matilda Wormwood | Rejected: pandemic/hazmat visual language. |
| [Window cleaning, 6197114](https://www.pexels.com/photo/woman-wearing-a-jumper-cleaning-a-glass-window-6197114/) | Tima Miroshnichenko | Selected; two preview resolutions of the same photograph were inspected. |

## Asset preparation and replacement

Pillow EXIF orientation normalization, RGB conversion, Lanczos resizing and WebP quality 80 (hero) / 78 (city), method 6. No upscaling. Originals are not served.

- Desktop hero: 4:5 crop from the source at 10% of its height, widths 480/800/1200. Face and cleaning action remain visible; the bucket is partially visible at the lower edge.
- Mobile/tablet hero: 4:3 crop from 24% of source height, widths 480/800; focus is face and cleaning action. CTA precedes the photograph.
- City: original 16:9 composition, widths 480/800/1200.
- Explicit intrinsic dimensions and matching CSS aspect ratios reserve space. Hero uses `fetchPriority="high"`; city uses `loading="lazy"`; both decode asynchronously. No runtime external photo requests.
- Total eight variants: approximately 448 KiB; a browser selects one hero and one city variant, rather than downloading all eight. Typical 1? mobile selection is about 44 KB combined; desktop about 122 KB combined (image bytes only). High density screens may select larger files.

When replacing imagery, update the central config, source register, dimensions, localized alt text and intentional desktop/mobile crops together. Retain releases from actual providers, customers and property owners.
