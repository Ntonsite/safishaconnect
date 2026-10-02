import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';
import 'package:safishacon_mobile/core/api_client.dart';
import 'package:safishacon_mobile/core/config.dart';
import 'package:safishacon_mobile/core/repository.dart';
import 'package:safishacon_mobile/core/token_store.dart';
import 'package:safishacon_mobile/l10n/app_localizations.dart';
import 'package:safishacon_mobile/main.dart';
import 'package:safishacon_mobile/ui/screens/home_screens.dart';
import 'package:safishacon_mobile/state/app_state.dart';

void main() {
  final binding = IntegrationTestWidgetsFlutterBinding.ensureInitialized();
  const locale = String.fromEnvironment('AUDIT_LOCALE', defaultValue: 'en');
  const manualProvider = bool.fromEnvironment('MANUAL_PROVIDER');
  testWidgets(
    'real customer journey on Android ($locale)',
    (tester) async {
      final repo = Repository(
        ApiClient(baseUrl: AppConfig.apiBaseUrl, tokens: MemoryTokenStore()),
      );
      final state = AppState(repo, initialLocale: const Locale(locale));
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
      await wait(find.byType(TextFormField));
      await tester.enterText(
        find.byType(TextFormField).at(0),
        customer['email'],
      );
      await tester.enterText(
        find.byType(TextFormField).at(1),
        customer['password'],
      );
      FocusManager.instance.primaryFocus?.unfocus();
      await tester.pump(const Duration(milliseconds: 700));
      await shot("login");
      await tap(find.byType(FilledButton).first);
      await wait(find.byKey(const ValueKey('home-book')));
      await state.setLocale(const Locale(locale), persistRemote: false);
      await tester.pump(const Duration(milliseconds: 400));
      final l = lookupAppLocalizations(const Locale(locale));
      await shot('home');
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
      final now = DateTime.now().add(const Duration(days: 1));
      final date =
          '${now.year}-${now.month.toString().padLeft(2, '0')}-${now.day.toString().padLeft(2, '0')}';
      final slots = await repo.slots(
        serviceId: service.id,
        areaId: area.id,
        date: date,
        durationMinutes: quote.durationMinutes,
      );
      final slot =
          slots.where((s) => s.available && s.start == '10:00').firstOrNull ??
          slots.firstWhere((s) => s.available);
      await tap(find.text(slot.start));
      await shot('schedule');
      await nextStep();
      await shot('review');
      await nextStep();
      await wait(find.byKey(const ValueKey('track-booking')));
      await shot('confirmed');
      await tap(find.byKey(const ValueKey('track-booking')));
      final summaries = await repo.bookings('all');
      final reference = tester
          .widgetList<Text>(find.byType(Text))
          .map((t) => t.data ?? '')
          .firstWhere((s) => s.startsWith('SC-'));
      final booking = summaries.firstWhere((b) => b.reference == reference);
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
      await wait(find.text(l.yourReview));
      await shot('reviewed');
      expect((await repo.booking(booking.id)).status, 'CLOSED');
      expect((await repo.booking(booking.id)).review?['rating'], 5);
      // tester.pageBack() looks for the English 'Back' tooltip; this works in every locale.
      await tap(find.byType(BackButton));
      await tester.pump(const Duration(milliseconds: 600));
      await tap(find.byType(NavigationDestination).at(1));
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
      debugPrint('MOBILE_AUDIT_COMPLETED ${booking.reference} $locale');
      await tester.pumpWidget(const SizedBox.shrink());
      state.dispose();
    },
    timeout: const Timeout(Duration(minutes: 20)),
  );
}
