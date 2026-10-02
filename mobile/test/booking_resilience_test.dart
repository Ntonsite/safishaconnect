import 'dart:async';
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
import 'package:safishacon_mobile/models/models.dart';
import 'package:safishacon_mobile/state/app_state.dart';
import 'package:safishacon_mobile/ui/screens/booking_flow_screen.dart';
import 'package:safishacon_mobile/ui/theme.dart';
import 'package:safishacon_mobile/ui/widgets/common.dart';

void main() {
  testWidgets(
    'slow quotes block continuation and stale responses cannot change the price',
    (tester) async {
      final services = File('test/fixtures/services.json').readAsStringSync();
      final areas = File('test/fixtures/areas.json').readAsStringSync();
      final service = Service.fromJson((jsonDecode(services) as List).first);
      final pending = <Completer<http.Response>>[];
      final api = ApiClient(
        baseUrl: 'http://api',
        tokens: MemoryTokenStore(),
        httpClient: MockClient((r) async {
          if (r.url.path.endsWith('/quotes')) {
            final c = Completer<http.Response>();
            pending.add(c);
            return c.future;
          }
          return http.Response(
            r.url.path.endsWith('/services') ? services : areas,
            200,
            headers: {'content-type': 'application/json; charset=utf-8'},
          );
        }),
      );
      final repo = Repository(api);
      final state = AppState(repo);
      await tester.pumpWidget(
        MultiProvider(
          providers: [
            Provider<Repository>.value(value: repo),
            ChangeNotifierProvider<AppState>.value(value: state),
          ],
          child: MaterialApp(
            theme: buildTheme(),
            localizationsDelegates: AppLocalizations.localizationsDelegates,
            supportedLocales: AppLocalizations.supportedLocales,
            home: BookingFlowScreen(initialService: service),
          ),
        ),
      );
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 300));
      final next = find.byKey(const ValueKey('booking-next'));
      expect(tester.widget<FilledButton>(next).onPressed, isNull);
      expect(find.text('Updating your price…'), findsOneWidget);
      await tester.tap(find.byTooltip('Bedrooms +'));
      await tester.pump(const Duration(milliseconds: 300));
      expect(pending.length, 2);
      http.Response quote(int total) => http.Response(
        jsonEncode({
          'lines': [],
          'total_amount': '$total',
          'estimated_duration_minutes': 120,
        }),
        200,
      );
      pending[1].complete(quote(43000));
      await tester.pump();
      await tester.pump();
      expect(find.text('TZS 43,000'), findsOneWidget);
      expect(tester.widget<FilledButton>(next).onPressed, isNotNull);
      pending[0].complete(quote(99000));
      await tester.pumpAndSettle();
      expect(find.text('TZS 43,000'), findsOneWidget);
      expect(find.text('TZS 99,000'), findsNothing);
      await tester.pumpWidget(const SizedBox.shrink());
      state.dispose();
    },
  );
  testWidgets('API faults use customer wording in both languages', (
    tester,
  ) async {
    for (final lang in ['en', 'sw']) {
      final l = lookupAppLocalizations(Locale(lang));
      for (final item in [
        (0, 'NETWORK_ERROR', l.networkError),
        (401, 'TOKEN_EXPIRED', l.sessionExpired),
        (409, 'NO_PROVIDER', l.slotUnavailable),
        (422, 'AREA_UNSUPPORTED', l.unsupportedArea),
        (500, 'INTERNAL_ERROR', l.genericError),
      ]) {
        await tester.pumpWidget(
          MaterialApp(
            key: ValueKey('$lang${item.$2}'),
            locale: Locale(lang),
            supportedLocales: AppLocalizations.supportedLocales,
            localizationsDelegates: AppLocalizations.localizationsDelegates,
            home: Builder(
              builder: (ctx) => Scaffold(
                body: Text(
                  errorText(
                    ctx,
                    ApiException(item.$1, item.$2, 'Raw backend SQL traceback'),
                  ),
                ),
              ),
            ),
          ),
        );
        await tester.pumpAndSettle();
        expect(find.text(item.$3), findsOneWidget);
        expect(find.textContaining('SQL'), findsNothing);
      }
    }
  });
  test('explicit booking retries carry the same idempotency key', () async {
    final keys = <String?>[];
    final api = ApiClient(
      baseUrl: 'http://api',
      tokens: MemoryTokenStore(),
      httpClient: MockClient((r) async {
        keys.add(r.headers['Idempotency-Key']);
        return http.Response('{}', 200);
      }),
    );
    await api.postOnce('/bookings', {'service_id': 'demo'}, 'stable-request');
    await api.postOnce('/bookings', {'service_id': 'demo'}, 'stable-request');
    expect(keys, ['stable-request', 'stable-request']);
  });
}
