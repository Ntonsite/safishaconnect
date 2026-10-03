import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:safishacon_mobile/core/api_client.dart';
import 'package:safishacon_mobile/core/repository.dart';
import 'package:safishacon_mobile/core/token_store.dart';
import 'package:safishacon_mobile/main.dart';
import 'package:safishacon_mobile/state/app_state.dart';
import 'package:safishacon_mobile/ui/screens/auth_screens.dart';
import 'package:safishacon_mobile/ui/screens/home_screens.dart';
import 'package:safishacon_mobile/ui/screens/onboarding_screen.dart';
import 'package:shared_preferences/shared_preferences.dart';

AppState stateWith(http.Client client, {TokenStore? tokens}) => AppState(
  Repository(
    ApiClient(
      baseUrl: 'http://api',
      tokens: tokens ?? MemoryTokenStore(),
      httpClient: client,
    ),
  ),
);

void main() {
  setUp(() => SharedPreferences.setMockInitialValues({}));

  for (final language in ['en', 'sw']) {
    testWidgets(
      'compact $language discovery home keeps the booking action in the first viewport',
      (tester) async {
        tester.view.physicalSize = const Size(320, 640);
        tester.view.devicePixelRatio = 1;
        addTearDown(tester.view.resetPhysicalSize);
        addTearDown(tester.view.resetDevicePixelRatio);
        final state =
            stateWith(MockClient((_) async => http.Response('[]', 200)))
              ..status = AuthStatus.signedIn
              ..locale = Locale(language);
        await (FontLoader(
          'DMSans',
        )..addFont(rootBundle.load('assets/fonts/DMSans.ttf'))).load();
        await tester.pumpWidget(SafishaApp(repo: state.repo, state: state));
        await tester.pumpAndSettle();
        expect(
          tester.getBottomRight(find.byKey(const ValueKey('home-book'))).dy,
          lessThanOrEqualTo(tester.getTopLeft(find.byType(NavigationBar)).dy),
        );
        expect(tester.takeException(), isNull);
      },
    );
  }

  for (final skipPage in [0, 1, 2]) {
    testWidgets(
      'offline first launch, exit on page $skipPage persists across restart',
      (tester) async {
        // A configuration request that never resolves cannot hold the startup route.
        final pending = Completer<http.Response>();
        final client = MockClient((_) => pending.future);
        final state = stateWith(client);
        await tester.pumpWidget(SafishaApp(repo: state.repo, state: state));
        expect(find.byType(LoginScreen), findsNothing);
        await state.bootstrap();
        await tester.pumpAndSettle();
        expect(find.byType(OnboardingScreen), findsOneWidget);
        for (var i = 0; i < skipPage; i++) {
          await tester.tap(find.byKey(const ValueKey('onboarding-next')));
          await tester.pumpAndSettle();
        }
        await tester.tap(
          find.byKey(
            ValueKey(skipPage < 2 ? 'onboarding-skip' : 'onboarding-next'),
          ),
        );
        await tester.pumpAndSettle();
        expect(find.byType(LoginScreen), findsOneWidget);
        expect(
          (await SharedPreferences.getInstance()).getBool(
            AppState.onboardingKey,
          ),
          isTrue,
        );
        final restart = stateWith(client);
        await restart.bootstrap();
        await tester.pumpWidget(SafishaApp(repo: restart.repo, state: restart));
        await tester.pumpAndSettle();
        expect(find.byType(LoginScreen), findsOneWidget);
        expect(find.byType(OnboardingScreen), findsNothing);
        pending.complete(http.Response('{}', 200));
        await tester.pumpAndSettle();
      },
    );
  }

  testWidgets('language changes in place and is restored after restart', (
    tester,
  ) async {
    final client = MockClient((_) async => http.Response('{}', 200));
    final state = stateWith(client);
    await state.bootstrap();
    await tester.pumpWidget(SafishaApp(repo: state.repo, state: state));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const ValueKey('onboarding-next')));
    await tester.pumpAndSettle();
    await tester.tap(find.text('SW'));
    await tester.pumpAndSettle();
    expect(
      find.text('Wataalamu unaowaamini. Tayari kufanya usafi.'),
      findsOneWidget,
    );
    expect(find.byKey(const ValueKey('onboarding-skip')), findsOneWidget);
    expect((await AppState.savedLocale()).languageCode, 'sw');
    await tester.drag(find.byType(PageView), const Offset(-650, 0));
    await tester.pumpAndSettle();
    expect(find.byKey(const ValueKey('onboarding-sign-in')), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets(
    'authenticated returning customer bypasses onboarding without a flag',
    (tester) async {
      final tokens = MemoryTokenStore();
      await tokens.writeRefreshToken('test-session');
      final client = MockClient((request) async {
        if (request.url.path.endsWith('/refresh')) {
          return http.Response(
            jsonEncode({'access_token': 'access', 'refresh_token': 'refresh'}),
            200,
          );
        }
        if (request.url.path.endsWith('/me')) {
          return http.Response(
            jsonEncode({
              'id': 'customer',
              'full_name': 'Test Customer',
              'phone': '+255700000000',
              'role': 'CUSTOMER',
              'preferred_locale': 'en',
            }),
            200,
          );
        }
        if (request.url.path.endsWith('/services') ||
            request.url.path.endsWith('/bookings')) {
          return http.Response('[]', 200);
        }
        return http.Response('{}', 200);
      });
      final state = stateWith(client, tokens: tokens);
      await tester.pumpWidget(SafishaApp(repo: state.repo, state: state));
      await state.bootstrap();
      await tester.pumpAndSettle();
      expect(find.byType(HomeShell), findsOneWidget);
      expect(find.byType(OnboardingScreen), findsNothing);
      expect(find.byType(LoginScreen), findsNothing);
    },
  );

  testWidgets(
    'active booking loads ahead of delayed services and precedes the hero',
    (tester) async {
      final services = Completer<http.Response>();
      final client = MockClient((request) async {
        if (request.url.path.endsWith('/services')) {
          return services.future;
        }
        if (request.url.path.endsWith('/bookings')) {
          return http.Response(
            jsonEncode([
              {
                'id': 'booking',
                'reference': 'SC-TEST',
                'area_id': 'area',
                'status': 'PROVIDER_ASSIGNED',
                'service': {'name_en': 'Deep Cleaning', 'icon': 'sparkles'},
                'area_name': 'Mikocheni',
                'scheduled_date': '2026-10-05',
                'scheduled_start_time': '10:00:00',
                'estimated_duration_minutes': 180,
                'total_amount': '95000',
              },
            ]),
            200,
          );
        }
        return http.Response('{}', 200);
      });
      final state = stateWith(client)..status = AuthStatus.signedIn;
      await tester.pumpWidget(SafishaApp(repo: state.repo, state: state));
      await tester.pump(const Duration(milliseconds: 100));
      await tester.pump(const Duration(milliseconds: 100));
      final active = find.byKey(const ValueKey('home-active-booking'));
      final hero = find.byKey(const ValueKey('home-hero'));
      expect(active, findsOneWidget);
      expect(
        tester.getTopLeft(active).dy,
        lessThan(tester.getTopLeft(hero).dy),
      );
      services.complete(http.Response('[]', 200));
      await tester.pumpAndSettle();
      expect(tester.takeException(), isNull);
    },
  );
}
