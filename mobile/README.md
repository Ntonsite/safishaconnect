# SafishaCon customer mobile app

Flutter customer app with English/Kiswahili, a locally persisted three-page introduction, active booking tracking and the existing five-step booking flow. Providers/admins use the web portal.

## Run on the connected Android device

Start the backend on port 8000, then:

```powershell
adb reverse tcp:8000 tcp:8000
flutter run --dart-define=API_BASE_URL=http://127.0.0.1:8000
```

The default API URL is for an Android emulator. The loopback override above requires USB reverse forwarding; use a reachable backend URL for a standalone installation.

## Verify and build

```powershell
dart format .
flutter analyze
flutter test
flutter build apk --release --dart-define=API_BASE_URL=http://127.0.0.1:8000
```

APK: `build/app/outputs/flutter-apk/app-release.apk`. Current Android release signing uses the existing development signing configuration; configure production signing and API URL before distribution.

The physical-device integration test uses the local demo API, creates actual test bookings, advances eligible demo providers and records screenshots. Run only against the development/demo backend:

```powershell
flutter drive --driver=test_driver/integration_test.dart --target=integration_test/customer_journey_test.dart -d <device-id> --dart-define=API_BASE_URL=http://127.0.0.1:8000 --dart-define=AUDIT_LOCALE=en
```

Repeat with `AUDIT_LOCALE=sw`. English covers registration; Kiswahili covers demo customer login. First launch, Skip, persisted restart, authenticated restart and the complete booking/payment/review journey are checked.

Photography and licences: [source register](../docs/IMAGE_SOURCES.md). Implementation and verification: [Option 4 report](../docs/MOBILE_OPTION4_REPORT.md). Assets are bundled; onboarding does not wait for optional public API configuration.
