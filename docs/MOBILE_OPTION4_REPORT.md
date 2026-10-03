# SafishaCon mobile — Option 4 implementation

Date: 2026-10-03. Scope: Flutter customer app; real booking, provider assignment and payment contracts are preserved.

## Home before / after

Before: greeting, a generic question and button, service rows, with a small monochrome photo below the catalogue. Active bookings followed the marketing headline.

After: restrained wordmark and Dar es Salaam service-region label; active booking and Track Booking appear before marketing. New customers see a large natural-colour Dar interior, “Clean spaces. Brighter days.”, concise copy and one Book a Cleaning action into the existing five-step flow. Completed customers get their latest completed cleaning and Book Again, which loads its actual detail and prefills the existing flow. Actual API service names, summaries and prices are accompanied by curated thumbnails and photographic detail sheets. Home / Bookings / Profile navigation is preserved. Returning from a new booking resets Home's scroll position so the active card is visible.

Option 4 is adopted through immersive photography, editorial DM Sans typography, white space, green primary actions, thin dividers and minimal cards. No concept discounts, fabricated counts, online payments, provider shopping, ratings or messaging are introduced. The trust strip reflects verification, included equipment and clear pricing.

## Photography and licensing

Three optimized, licensed real photographs, bundled locally: a Dar es Salaam interior with patterned chairs, a Dar café workspace and a documented Nairobi apartment. The [source register](IMAGE_SOURCES.md) records originals, photographers, location evidence, licences, crops and usage. All previous foreign/unknown-location assets are removed from web and mobile. No AI or competitor/social photography is used. No suitable licensed local housecleaner photo was verified; onboarding page 2 uses the Dar workspace illustration rather than showing a cleaner at work.

## Three onboarding pages

1. Outcome: a bright contemporary interior and “A cleaner home, without the hassle.”
2. Professionals: a verified Dar commercial interior; explains eligible verified provider assignment and included materials. A local team photo remains a future replacement slot.
3. Peace of mind: a bright Dar interior with patterned chairs and “Book. Relax. We’ll handle the rest.”

Swipe / Next, page dots, immediate Skip on pages 1–2, Get Started and Sign In on page 3. All routes enter the existing authentication screens. Content and photographic slots are centralised; text and photo accessibility descriptions have English/Kiswahili equivalents. The language selector preserves the current page and saves the preference.

## First launch, Skip and persistence

The local `safisha.onboarding.completed` flag is resolved before rendering a signed-out destination. Skip, Get Started and Sign In share the persisted completion path. Returning signed-out customers see authentication. A stored session bypasses the introduction; a validated customer session opens Home even if the onboarding flag is absent. An expired/unavailable session still respects the returning-user introduction flag and uses authentication.

Optional public configuration loads independently; offline onboarding renders from bundled photos and local text without waiting on a backend response. Startup uses the existing splash while resolving authentication, without briefly rendering Login or the introduction for a validated signed-in customer.

## Performance

Three unique photos: 179,686 bytes (175.5 KiB), shared across placements. Previous foreign images are removed. Decode width is bounded to 960 pixels for editorial photos and 264 for service thumbnails. Opening and adjacent onboarding images are precached. Home's hero loads locally while services and bookings resolve independently; a slow catalogue cannot delay an active booking. Error/retry states preserve loaded content. Fonts and photographs need no runtime CDN connection. No production FPS benchmark is claimed from debug tests.

## Major files

- `mobile/lib/ui/screens/onboarding_screen.dart` — introduction, progression, Skip and language controls.
- `mobile/lib/state/app_state.dart`, `mobile/lib/main.dart` — local persistence and startup routing.
- `mobile/lib/ui/screens/home_screens.dart` — active-first Home, API catalogue and real repeat booking.
- `mobile/lib/ui/widgets/home_editorial.dart`, `editorial_photo.dart` — reusable editorial components and image map.
- `mobile/lib/ui/screens/auth_screens.dart`, `ui/widgets/service_widgets.dart` — matching auth and service details.
- `mobile/lib/l10n/app_en.arb`, `app_sw.arb` and generated localizations.
- `mobile/assets/images/{home,services,onboarding}/`, `mobile/pubspec.yaml`.
- `mobile/test/onboarding_test.dart`, `mobile_layout_test.dart`, `widget_test.dart`; `mobile/integration_test/customer_journey_test.dart`, `test_driver/integration_test.dart`.

## Verification

- `dart format .`: completed.
- `flutter analyze`: no issues.
- `flutter test`: **55 passed, 1 opt-in live API test skipped**. EN/SW layout matrix covers widths 320/360/375/390/412/430 and font scales 1/1.6/2. Compact 320 × 640 Home CTA, offline startup, Skip/final persistence, locale switching, authenticated startup and independent active booking loading are covered.
- Physical Android device NBA75TZACA000614: English registration, new/returning onboarding routes and full booking through CLOSED plus review passed for SC-N7MDLV. Baseline app was also run before editing; its original next-day slot fixture had no Sunday availability, so the integration test now selects actual available slots within 14 days.
- `npm.cmd run build`: passed. `npm.cmd run test`: **18 passed**.
- `docker compose up -d --build --no-deps web`: completed. Port 8080 serves the new responsive Dar hero. Browser inspection covered desktop and 390px mobile, EN/SW and loaded hero source/alt descriptions.
- Screenshots: [English Home](screenshots/mobile-option4/en-home.png), [professionals introduction](screenshots/mobile-option4/en-onboarding-2.png), [active booking](screenshots/mobile-option4/en-home-active.png). These are development integration captures; native phone capture additionally confirmed Android status bar presentation.

### Finalization (2026-10-03)

- The integration test's Book Again check referenced `liveStatuses` without importing `models.dart`. `flutter analyze` reported the error and the test could not compile. I added the import.
- The Kiswahili run (demo customer, long booking history) failed at the Past filter. Opening the new booking had scrolled the Bookings list, so the filter chips in the lazy list's first row were no longer built. The test now scrolls the list to the top first. App behaviour was unchanged.
- Re-verified on physical device NBA75TZACA000614. Each run went from the introduction through CLOSED and the review, then history, the EN/SW Home re-check and Book Again prefill:
  - Kiswahili ✓ SC-VH8R8S;
  - English ✓ SC-X5UG8L.
- `flutter analyze`: no issues.
- `flutter test`: 56 passed, 1 skipped.
- `dart format`: no changes.
- Web: `npm run test` 18 passed; `npm run build` passed.
- The release APK is built separately by the project owner: `flutter build apk --release --dart-define=API_BASE_URL=…`.
