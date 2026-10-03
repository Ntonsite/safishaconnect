import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';
import 'package:safishacon_mobile/core/api_client.dart';
import 'package:safishacon_mobile/core/config.dart';
import 'package:safishacon_mobile/core/repository.dart';
import 'package:safishacon_mobile/core/token_store.dart';
import 'package:safishacon_mobile/l10n/app_localizations.dart';
import 'package:safishacon_mobile/main.dart';
import 'package:safishacon_mobile/models/models.dart';
import 'package:safishacon_mobile/ui/screens/home_screens.dart';
import 'package:safishacon_mobile/ui/screens/booking_flow_screen.dart';
import 'package:safishacon_mobile/state/app_state.dart';

void main() {
  final binding = IntegrationTestWidgetsFlutterBinding.ensureInitialized();
  const locale = String.fromEnvironment('AUDIT_LOCALE', defaultValue: 'en');
  const manualProvider = bool.fromEnvironment('MANUAL_PROVIDER');
  testWidgets(
    'real customer journey on Android ($locale)',
    (tester) async {
      final prefs = await SharedPreferences.getInstance();
      await prefs.remove(AppState.onboardingKey);
      final repo = Repository(
        ApiClient(baseUrl: AppConfig.apiBaseUrl, tokens: MemoryTokenStore()),
      );
      var state = AppState(repo, initialLocale: const Locale(locale));
      await state.bootstrap();
      final config = await repo.config();
      final accounts = config['demo_accounts'] as List;
      final customer = accounts.firstWhere((a) => a['role'] == 'customer');
      await tester.pumpWidget(SafishaApp(repo: repo, state: state));

      Future<void> wait(Finder finder) async {
        final deadline = DateTime.now().add(const Duration(seconds: 50));
        while (finder.evaluate().isEmpty && DateTime.now().isBefore(deadline)) {
          await tester.pump(const Duration(milliseconds: 300));
        }
        if (finder.evaluate().isEmpty) {
          debugPrint(
            "SCREEN_TEXTS: ${tester.widgetList<Text>(find.byType(Text)).map((t) => t.data).join(" | ")}",
          );
        }
        expect(finder, findsWidgets);
        await tester.pump(const Duration(milliseconds: 300));
      }

      Future<void> tap(Finder finder) async {
        await wait(finder);
        await tester.ensureVisible(finder.first);
        await tester.pump(const Duration(milliseconds: 500));
        await tester.tap(finder.first);
        await tester.pump(const Duration(milliseconds: 350));
      }

      Future<void> shot(String name) async {
        await tester.pump(const Duration(milliseconds: 500));
        await binding.takeScreenshot('$locale-$name');
      }

      await binding.convertFlutterSurfaceToImage();
      await shot('onboarding-1');
      await tap(find.byKey(const ValueKey('onboarding-skip')));
      expect(prefs.getBool(AppState.onboardingKey), isTrue);
      state = AppState(repo, initialLocale: const Locale(locale));
      await state.bootstrap();
      await tester.pumpWidget(SafishaApp(repo: repo, state: state));
      await wait(find.byType(TextFormField));
      await shot('skip-restart-auth');
      // Simulate a new install's local flag for the complete three-page path.
      await prefs.remove(AppState.onboardingKey);
      state = AppState(repo, initialLocale: const Locale(locale));
      await state.bootstrap();
      await tester.pumpWidget(SafishaApp(repo: repo, state: state));
      await tester.pump(const Duration(milliseconds: 500));
      await tap(find.byKey(const ValueKey('onboarding-next')));
      await shot('onboarding-2');
      await tap(find.byKey(const ValueKey('onboarding-next')));
      await shot('onboarding-3');
      await tap(find.byKey(const ValueKey('onboarding-next')));
      expect(prefs.getBool(AppState.onboardingKey), isTrue);
      await wait(find.byType(TextFormField));
      final l = lookupAppLocalizations(const Locale(locale));
      if (locale == 'en') {
        // A real fresh customer shows the discovery home without existing bookings.
        await tap(find.widgetWithText(TextButton, l.noAccount));
        await tester.pumpAndSettle();
        final timestamp = DateTime.now().millisecondsSinceEpoch;
        final phone =
            '+2557${(timestamp % 100000000).toString().padLeft(8, '0')}';
        final fields = find.byType(TextFormField);
        await tester.enterText(fields.at(0), 'Option Four Test');
        await tester.enterText(fields.at(1), phone);
        await tester.enterText(
          fields.at(2),
          'mobile.option4.$timestamp@example.com',
        );
        await tester.enterText(fields.at(3), customer['password']);
      } else {
        await tester.enterText(
          find.byType(TextFormField).at(0),
          customer['email'],
        );
        await tester.enterText(
          find.byType(TextFormField).at(1),
          customer['password'],
        );
      }
      FocusManager.instance.primaryFocus?.unfocus();
      await tester.pump(const Duration(milliseconds: 700));
      await shot("login");
      await tap(find.byType(FilledButton).first);
      await wait(find.byKey(const ValueKey('home-book')));
      await state.setLocale(const Locale(locale), persistRemote: false);
      await tester.pump(const Duration(milliseconds: 400));
      await shot('home');
      // A persisted session must bypass the intro, even without its local flag.
      await prefs.remove(AppState.onboardingKey);
      state = AppState(repo, initialLocale: const Locale(locale));
      await state.bootstrap();
      expect(state.status, AuthStatus.signedIn);
      await tester.pumpWidget(SafishaApp(repo: repo, state: state));
      await wait(find.byType(HomeShell));
      await shot('authenticated-restart-home');
      await tester.scrollUntilVisible(
        find.byKey(const ValueKey('home-book')),
        180,
        scrollable: find.byType(Scrollable).first,
      );
      await shot('home-editorial');
      await tap(find.byKey(const ValueKey('home-book')));
      final services = await repo.services();
      final service = services.firstWhere((s) => s.slug == 'deep-cleaning');
      await tap(find.text(service.name(locale)));
      await tap(find.byKey(const ValueKey('select-service')));
      await wait(find.byTooltip('${l.bedrooms} +'));
      // Set the requested property to three bedrooms and two bathrooms.
      await tap(find.byTooltip('${l.bedrooms} +'));
      await tap(find.byTooltip('${l.bedrooms} +'));
      await tap(find.byTooltip('${l.bathrooms} +'));
      final next = find.byKey(const ValueKey('booking-next'));
      Future<void> nextStep() async {
        final deadline = DateTime.now().add(const Duration(seconds: 40));
        while (tester.widget<FilledButton>(next).onPressed == null &&
            DateTime.now().isBefore(deadline)) {
          await tester.pump(const Duration(milliseconds: 300));
        }
        expect(tester.widget<FilledButton>(next).onPressed, isNotNull);
        await tap(next);
      }

      await shot('property');
      await nextStep();
      await tap(find.byType(DropdownButtonFormField<String>));
      final area = (await repo.areas()).firstWhere(
        (a) => a.name == 'Mikocheni',
      );
      await tap(find.text('${area.name}, ${area.cityName}').last);
      final address =
          'Mobile UX audit $locale ${DateTime.now().millisecondsSinceEpoch}, Plot 9';
      await tester.enterText(find.byType(TextField).first, address);
      FocusManager.instance.primaryFocus?.unfocus();
      await tester.pump(const Duration(milliseconds: 400));
      await nextStep();
      // Choose a real available slot, using the same API data the screen shows.
      final request = {
        'service_id': service.id,
        'property_type_option_id': service.group('PROPERTY_TYPE').first.id,
        'bedrooms': 3,
        'bathrooms': 2,
        'addons': [],
      };
      final quote = await repo.quote(request);
      expect(quote.total, 110000);
      final today = DateTime.now();
      DateTime? availableDay;
      String? start;
      for (var offset = 1; offset < 14; offset++) {
        final day = DateTime(today.year, today.month, today.day + offset);
        final slots = await repo.slots(
          serviceId: service.id,
          areaId: area.id,
          date: DateFormat('yyyy-MM-dd').format(day),
          durationMinutes: quote.durationMinutes,
        );
        final slot =
            slots.where((s) => s.available && s.start == '10:00').firstOrNull ??
            slots.where((s) => s.available).firstOrNull;
        if (slot != null) {
          availableDay = day;
          start = slot.start;
          break;
        }
      }
      expect(
        availableDay,
        isNotNull,
        reason: 'An eligible provider needs availability in the next 14 days',
      );
      final dayFinder = find.byKey(
        ValueKey(
          'booking-date-${DateFormat('yyyy-MM-dd').format(availableDay!)}',
        ),
      );
      await tester.scrollUntilVisible(
        dayFinder,
        180,
        scrollable: find.byWidgetPredicate(
          (w) => w is Scrollable && w.axisDirection == AxisDirection.right,
        ),
      );
      await tap(dayFinder);
      await tap(find.text(start!));
      await shot('schedule');
      await nextStep();
      await shot('review');
      await nextStep();
      await wait(find.byKey(const ValueKey('track-booking')));
      await shot('confirmed');
      final summaries = await repo.bookings('all');
      final reference = RegExp(r'SC-[\w-]+')
          .firstMatch(
            tester
                .widgetList<Text>(find.byType(Text))
                .map((t) => t.data ?? '')
                .firstWhere((s) => s.contains('SC-')),
          )!
          .group(0)!;
      final booking = summaries.firstWhere((b) => b.reference == reference);
      await tap(find.widgetWithText(TextButton, l.backHome));
      await wait(find.byKey(const ValueKey('home-active-booking')));
      await shot('home-active');
      await tap(find.byType(NavigationDestination).at(1));
      await tap(
        find.byWidgetPredicate(
          (w) => w is BookingTile && w.booking.id == booking.id,
        ),
      );
      expect((await repo.booking(booking.id)).addressLine, address);
      // Provider actions use real API transitions; no statuses are injected into UI.
      ApiClient? provider;
      dynamic offer;
      for (final account in accounts.where(
        (a) => a['role'] == 'cleaner' || a['role'] == 'company',
      )) {
        final candidate = ApiClient(
          baseUrl: AppConfig.apiBaseUrl,
          tokens: MemoryTokenStore(),
        );
        await Repository(
          candidate,
        ).login(account['email'], account['password']);
        final offers =
            await candidate.get(
                  '/providers/me/jobs',
                  query: {'scope': 'offers'},
                )
                as List;
        final matches = offers.where((j) => j['booking']['id'] == booking.id);
        if (matches.isNotEmpty) {
          debugPrint('AUDIT_PROVIDER ${account['email']}');
          provider = candidate;
          offer = matches.first;
          break;
        }
      }
      expect(
        provider,
        isNotNull,
        reason: 'A seeded eligible provider must receive the assignment',
      );
      Future<void> waitStatus(String status) async {
        debugPrint('AUDIT_PORTAL_WAIT ${booking.reference} $status');
        final deadline = DateTime.now().add(const Duration(minutes: 4));
        while ((await repo.booking(booking.id)).status != status &&
            DateTime.now().isBefore(deadline)) {
          await tester.pump(const Duration(seconds: 3));
        }
        expect((await repo.booking(booking.id)).status, status);
      }

      if (manualProvider) {
        await waitStatus('PROVIDER_ASSIGNED');
      } else {
        await provider!.post('/assignments/${offer['assignment_id']}/accept');
      }
      await tap(find.byTooltip(l.refreshBooking));
      await wait(find.text(l.assignedTitle));
      await shot('assigned');
      for (final transition in [
        ('PROVIDER_EN_ROUTE', l.enRouteTitle),
        ('PROVIDER_ARRIVED', l.arrivedTitle),
        ('SERVICE_IN_PROGRESS', l.inProgressTitle),
        ('COMPLETED_BY_PROVIDER', l.completedTitle),
      ]) {
        if (manualProvider) {
          await waitStatus(transition.$1);
        } else {
          await provider!.post('/providers/me/jobs/${booking.id}/advance', {
            'expected_status': transition.$1,
          });
        }
        await tap(find.byTooltip(l.refreshBooking));
        await wait(find.text(transition.$2));
      }
      await shot('complete');
      await tap(find.widgetWithText(FilledButton, l.confirmCompletion));
      await wait(find.text(l.rateTitle));
      if (manualProvider) {
        await waitStatus('CLOSED');
      } else {
        await provider!.post('/payments/bookings/${booking.id}/confirm-cash', {
          'note': 'Demo mobile UX audit cash confirmation',
        });
      }
      await tap(find.byTooltip(l.ratingLabel(5)));
      await tester.enterText(
        find.byType(TextField).first,
        'Demo mobile UI test, not a customer testimonial.',
      );
      await tap(find.widgetWithText(FilledButton, l.submitReview));
      // The longer SW page can leave the new review section above the lazy viewport.
      await tester.fling(
        find.byType(Scrollable).first,
        const Offset(0, 3000),
        3000,
      );
      await tester.pumpAndSettle();
      await wait(find.text(l.yourReview));
      await shot('reviewed');
      expect((await repo.booking(booking.id)).status, 'CLOSED');
      expect((await repo.booking(booking.id)).review?['rating'], 5);
      // tester.pageBack() looks for the English 'Back' tooltip; this works in every locale.
      await tap(find.byType(BackButton));
      await tester.pump(const Duration(milliseconds: 600));
      await tap(find.byType(NavigationDestination).at(1));
      // The demo customer's long list stays scrolled to the opened booking; the
      // filter chips live in the lazy list's first row.
      await tester.fling(
        find.byType(Scrollable).first,
        const Offset(0, 3000),
        3000,
      );
      await tester.pumpAndSettle();
      await tap(find.text(l.pastBookings));
      final historyTile = find.byWidgetPredicate(
        (w) => w is BookingTile && w.booking.id == booking.id,
      );
      await tester.scrollUntilVisible(
        historyTile,
        200,
        scrollable: find.byType(Scrollable).last,
      );
      await tester.pump(const Duration(milliseconds: 500));
      await shot('history');
      expect(historyTile, findsOneWidget);
      await tap(find.byType(NavigationDestination).first);
      await wait(find.byType(HomeShell));
      for (final homeLocale in ['en', 'sw']) {
        await state.setLocale(Locale(homeLocale), persistRemote: false);
        await tester.pumpAndSettle();
        await tester.fling(
          find.byType(Scrollable).first,
          const Offset(0, 3000),
          3000,
        );
        await tester.pumpAndSettle();
        await shot('home-retest-$homeLocale');
        expect(tester.takeException(), isNull);
      }
      await state.setLocale(const Locale(locale), persistRemote: false);
      await tester.pumpAndSettle();
      if (!(await repo.bookings('all')).any(
        (b) => liveStatuses.contains(b.status) || b.status == 'DISPUTED',
      )) {
        final again = find.widgetWithText(OutlinedButton, l.bookAgain);
        await tester.scrollUntilVisible(
          again,
          180,
          scrollable: find.byType(Scrollable).first,
        );
        await tap(again);
        await wait(find.byTooltip('${l.bedrooms} +'));
        final repeat = tester
            .widget<BookingFlowScreen>(find.byType(BookingFlowScreen))
            .repeatBooking;
        expect(repeat?.id, booking.id);
        expect(repeat?.bedrooms, 3);
        expect(repeat?.bathrooms, 2);
        expect(repeat?.addressLine, address);
        await shot('home-book-again');
      }
      debugPrint('MOBILE_AUDIT_COMPLETED ${booking.reference} $locale');
      await tester.pumpWidget(const SizedBox.shrink());
      state.dispose();
    },
    timeout: const Timeout(Duration(minutes: 20)),
  );
}
