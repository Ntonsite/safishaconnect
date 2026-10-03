# SafishaCon photography sources

Reviewed **2026-10-03**. All current photos have documented Tanzanian locations except the permitted Nairobi apartment fallback. Photos are served locally. Original contributor pages establish location; visual suitability was checked separately.

| Source / creator | Documented location | Placement / asset | Licence |
|---|---|---|---|
| [Patterned chairs, 1350789](https://www.pexels.com/photo/two-assorted-color-padded-chairs-near-side-table-1350789/), ERIC MUFASA | Dar es Salaam, Tanzania | Web `hero-dar-interior-*.webp`; Flutter `home/dar-living-room.webp`: Home, peaceful onboarding, general and sofa services | [Pexels](https://www.pexels.com/license/) |
| [CySuites apartment, 76JYlSoAYM4](https://unsplash.com/photos/a-living-room-with-a-couch-and-a-table-76JYlSoAYM4), Cytonn Photography | Westlands, Nairobi, Kenya | Flutter `onboarding/nairobi-apartment.webp`: introduction, auth, deep cleaning and move-in service illustrations | [Unsplash](https://unsplash.com/license) |
| [Bean there café, ztJM6VK6J9g](https://unsplash.com/photos/white-pendant-lamp-turned-on-in-room-ztJM6VK6J9g), Jabber Visuals | Dar es Salaam, Tanzania | Flutter `services/dar-workspace.webp`: professionals introduction and office service illustration | [Unsplash](https://unsplash.com/license) |
| [City view, y1bnAADWAqk](https://unsplash.com/photos/a-city-with-many-buildings-y1bnAADWAqk), Okra Amps | Dar es Salaam, Tanzania; caption “Shot from Reagent Estate” | Existing web `dar-es-salaam-*.webp`: service areas | [Unsplash](https://unsplash.com/license) |

These licences permit commercial use and modification without mandatory attribution. Credit is retained here. No implied endorsement, invented identities or claims that these are SafishaCon properties are made. The café is a local commercial interior illustration, not a photographed customer office. Nairobi is not labelled Tanzanian.

## Download references

- Chairs: `https://images.pexels.com/photos/1350789/pexels-photo-1350789.jpeg?auto=compress&cs=tinysrgb&w=1600`
- Apartment: `https://images.unsplash.com/photo-1658218635253-64728f6234be?auto=format&fit=max&w=1800&q=85`
- Workspace: `https://images.unsplash.com/photo-1614161980860-7d69a5292dab?auto=format&fit=max&w=1800&q=85`
- City: `https://images.unsplash.com/photo-1654941348480-217757d5f933?auto=format&fit=max&w=2000&q=85`

## Preparation

EXIF orientation normalization, RGB conversion, Lanczos crops and WebP quality 82, method 6 for new assets. Natural colour retained; no generated content, retouching or composites.

- Flutter: room 1200 × 768, 67,976 bytes; apartment 1080 × 900, 70,618 bytes; workspace 960 × 1200, 41,092 bytes. Total **179,686 bytes (175.5 KiB)** shared across placements. Editorial decode width 960; thumbnail width 264. Opening and adjacent onboarding images are precached.
- Web: desktop 480/800/1200 wide, 4:5 crops favouring green chair/table; mobile 480/800 wide, 4:3 retaining both chairs. Prepared from a 3200 × 2046 working copy without upscaling. Five new variants total **241,254 bytes**; browser selects one. Existing city variants retain 16:9. Intrinsic sizes, srcsets, async decoding, hero fetch priority and lazy city loading remain.
- Central maps: `web/src/config/imagery.ts` and `mobile/lib/ui/widgets/editorial_photo.dart`. EN/SW descriptions match subjects.
- Flutter DM Sans remains bundled with `mobile/assets/fonts/OFL.txt` (SIL Open Font License).

## Rejected / withdrawn imagery

Earlier Pexels 6197114 hero and proposed Option 4 photos 6196582, 10161225, 6044718, 6197050, 380769 and 4401538 are withdrawn. Their sources do not establish Tanzania/East Africa; 380769 identifies Berlin. Their application assets, including the unused old Flutter image, are removed. Historical screenshots may show prior designs.

Research covered Tanzanian/Kenyan cleaners, equipment, offices and homes. Competitor/social images lacked transferable permission. Unlicensed paid stock, AI imagery, foreign winter homes, beach cleanup, street shoe cleaning and industrial sanitation were rejected.

**Remaining photography gap:** no suitable high-quality, freely licensed Tanzanian/East African housecleaner photograph was verified. The professionals introduction uses the verified Dar commercial interior; it must not be described as showing a cleaner at work. A future licensed local team photo can replace this slot without layout changes. See the existing local photography shoot guide.
