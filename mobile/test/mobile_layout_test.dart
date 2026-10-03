import 'dart:convert';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:provider/provider.dart';
import 'package:safishacon_mobile/core/api_client.dart';
import 'package:safishacon_mobile/core/repository.dart';
import 'package:safishacon_mobile/core/token_store.dart';
import 'package:safishacon_mobile/l10n/app_localizations.dart';
import 'package:safishacon_mobile/state/app_state.dart';
import 'package:safishacon_mobile/ui/screens/booking_flow_screen.dart';
import 'package:safishacon_mobile/ui/screens/auth_screens.dart';
import 'package:safishacon_mobile/ui/screens/home_screens.dart';
import 'package:safishacon_mobile/ui/screens/onboarding_screen.dart';
import 'package:safishacon_mobile/ui/theme.dart';
import 'package:safishacon_mobile/ui/widgets/common.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  setUp(() => SharedPreferences.setMockInitialValues({}));
  final services = File('test/fixtures/services.json').readAsStringSync();
  final areas = File('test/fixtures/areas.json').readAsStringSync();
  for (final width in [320, 360, 375, 390, 412, 430]) {
    for (final lang in ['en', 'sw']) {
      for (final scale in [1.0, 1.6, 2.0]) {
        testWidgets(
          '$lang width $width at $scale font: auth and all booking steps',
          (tester) async {
            tester.view.physicalSize = Size(width.toDouble(), 900);
            tester.view.devicePixelRatio = 1;
            addTearDown(tester.view.resetPhysicalSize);
            addTearDown(tester.view.resetDevicePixelRatio);
            final api = ApiClient(
              baseUrl: 'http://api',
              tokens: MemoryTokenStore(),
              httpClient: MockClient((r) async {
                final path = r.url.path;
                if (path.endsWith('/bookings')) return http.Response('[]', 200);
                if (path.endsWith('/services')) {
                  return http.Response(
                    services,
                    200,
                    headers: {
                      "content-type": "application/json; charset=utf-8",
                    },
                  );
                }
                if (path.endsWith('/areas')) {
                  return http.Response(
                    areas,
                    200,
                    headers: {
                      "content-type": "application/json; charset=utf-8",
                    },
                  );
                }
                if (path.endsWith('/quotes')) {
                  return http.Response(
                    jsonEncode({
                      'lines': [],
                      'total_amount': '110000',
                      'estimated_duration_minutes': 375,
                    }),
                    200,
                  );
                }
                if (path.endsWith('/availability')) {
                  return http.Response(
                    jsonEncode({
                      'slots': [
                        {
                          'start_time': '10:00:00',
                          'end_time': '16:15:00',
                          'available': true,
                        },
                      ],
                    }),
                    200,
                  );
                }
                return http.Response('{}', 200);
              }),
            );
            final repo = Repository(api);
            final state = AppState(repo, initialLocale: Locale(lang));
            Widget app(Widget child) => MultiProvider(
              providers: [
                Provider<Repository>.value(value: repo),
                ChangeNotifierProvider<AppState>.value(value: state),
              ],
              child: MaterialApp(
                key: ValueKey(child.runtimeType),
                theme: buildTheme(),
                locale: Locale(lang),
                supportedLocales: AppLocalizations.supportedLocales,
                localizationsDelegates: AppLocalizations.localizationsDelegates,
                builder: (context, child) => MediaQuery(
                  data: MediaQuery.of(
                    context,
                  ).copyWith(textScaler: TextScaler.linear(scale)),
                  child: child!,
                ),
                home: child,
              ),
            );
            final l = lookupAppLocalizations(Locale(lang));
            await tester.pumpWidget(app(const OnboardingScreen()));
            await tester.pumpAndSettle();
            expect(tester.takeException(), isNull);
            for (var i = 0; i < 2; i++) {
              await tester.tap(find.byKey(const ValueKey('onboarding-next')));
              await tester.pumpAndSettle();
              expect(tester.takeException(), isNull);
            }
            await tester.pumpWidget(app(const LoginScreen()));
            await tester.pumpAndSettle();
            expect(tester.takeException(), isNull);
            await tester.pumpWidget(app(const RegisterScreen()));
            await tester.pumpAndSettle();
            expect(tester.takeException(), isNull);
            await tester.pumpWidget(app(const HomeShell()));
            await tester.pumpAndSettle();
            expect(tester.takeException(), isNull);
            await tester.tap(find.byType(NavigationDestination).at(1));
            await tester.pumpAndSettle();
            expect(tester.takeException(), isNull);
            await tester.tap(find.byType(NavigationDestination).at(2));
            await tester.pumpAndSettle();
            expect(tester.takeException(), isNull);
            await tester.pumpWidget(app(const BookingFlowScreen()));
            await tester.pumpAndSettle();
            expect(tester.takeException(), isNull);
            final deep = (jsonDecode(services) as List).firstWhere(
              (s) => s['slug'] == 'deep-cleaning',
            );
            await tester.scrollUntilVisible(
              find.text(deep['name_$lang']),
              180,
              scrollable: find.byType(Scrollable).first,
            );
            await tester.pumpAndSettle();
            await tester.ensureVisible(find.text(deep['name_$lang']));
            await tester.pumpAndSettle();
            await tester.tap(find.text(deep['name_$lang']));
            await tester.pumpAndSettle();
            await tester.ensureVisible(
              find.byKey(const ValueKey('select-service')),
            );
            await tester.pumpAndSettle();
            await tester.tap(find.byKey(const ValueKey('select-service')));
            await tester.pumpAndSettle();
            expect(tester.takeException(), isNull);
            final next = find.byKey(const ValueKey('booking-next'));
            await tester.tap(next);
            await tester.pumpAndSettle();
            await tester.ensureVisible(
              find.byType(DropdownButtonFormField<String>),
            );
            await tester.pumpAndSettle();
            await tester.tap(find.byType(DropdownButtonFormField<String>));
            await tester.pumpAndSettle();
            await tester.tap(find.text('Mikocheni, Dar es Salaam').last);
            await tester.pumpAndSettle();
            await tester.scrollUntilVisible(
              find.byKey(const ValueKey('booking-address')),
              160,
              scrollable: find.byType(Scrollable).first,
            );
            await tester.pumpAndSettle();
            await tester.enterText(
              find.byKey(const ValueKey('booking-address')),
              'Plot 9, Mikocheni',
            );
            FocusManager.instance.primaryFocus?.unfocus();
            await tester.pumpAndSettle();
            expect(tester.takeException(), isNull);
            await tester.tap(next);
            await tester.pumpAndSettle();
            await tester.ensureVisible(find.text('10:00'));
            await tester.pumpAndSettle();
            await tester.tap(find.text('10:00'));
            await tester.pumpAndSettle();
            expect(tester.takeException(), isNull);
            await tester.tap(next);
            await tester.pumpAndSettle();
            expect(find.text(l.reviewBooking), findsOneWidget);
            expect(tester.takeException(), isNull);
            // Native back moves one step rather than discarding the booking.
            await tester.binding.handlePopRoute();
            await tester.pumpAndSettle();
            expect(find.text(l.chooseDate), findsOneWidget);
            expect(tester.takeException(), isNull);
            await tester.pumpWidget(
              app(
                const Scaffold(
                  body: SingleChildScrollView(
                    child: Padding(
                      padding: EdgeInsets.all(20),
                      child: PriceLines(
                        lines: [
                          (
                            label:
                                'Extra bedrooms / Vyumba vya kulala vya ziada',
                            quantity: 3,
                            amount: 15000,
                          ),
                        ],
                        total: 110000,
                      ),
                    ),
                  ),
                ),
              ),
            );
            await tester.pumpAndSettle();
            expect(tester.takeException(), isNull);
            await tester.pumpWidget(const SizedBox.shrink());
            state.dispose();
          },
        );
      }
    }
  }
}
