# Photography implementation review

Reviewed 2026-10-01?02 on the running React development app, with the existing local API.

## Browser review

| Width | English | Kiswahili |
|---|---|---|
| 1440 | Pass | Pass |
| 1280 | Pass | Pass |
| 768 | Pass | Pass |
| 430 | Pass | Pass |
| 390 | Pass | Pass |
| 375 | Pass | Pass |
| 320 | Pass | Pass |

At each width: no horizontal document overflow, local hero loaded, localized image description, appropriate desktop/mobile crop. Screenshots are in `docs/screenshots/photography/`. Primary mobile booking CTA precedes the image; at 320px both hero buttons end within approximately 623px of the document top. Face and cleaning action stay visible. City composition was checked at desktop and mobile; lazy loading succeeds with a localized description and city caption.

Before: informational hero panel without photography; areas represented by chips only. After: the same headline/actions with professional cleaning imagery, booking-inclusions panel below, and a verified Dar city view beside coverage. The current typography, green identity and real catalogue pricing remain prominent.

## Performance and accessibility

Eight local WebP variants total 458,820 bytes (448 KiB). A responsive browser selects one hero variant; desktop widths 480/800/1200, mobile 480/800. Hero variants range 10,384?65,648 bytes. City variants range 33,210?190,908 bytes and load lazily below the fold. No third-party runtime photo hotlinks. Hero fetch priority high; both images decode asynchronously. Intrinsic dimensions and aspect ratios reserve their layout space, including art-directed source dimensions. This checks image sizing and loading; a production network-throttled Lighthouse / Core Web Vitals measurement was not performed.

## Verification

- npm.cmd run lint: passed.
- npm.cmd run typecheck: passed.
- npm.cmd run build: passed; all eight assets emitted with hashed filenames.
- npm.cmd test: 18 tests passed across three files, including English/Kiswahili key parity. Existing React Router v7 future warnings only.

The photography change is confined to landing UI, localization and local assets/configuration. Source licenses, restrictions and rejected downloaded candidates are registered in IMAGE_SOURCES.md; commissioned replacement direction is in SAFISHA_PHOTOSHOOT_GUIDE.md.
