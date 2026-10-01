import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:safishacon_mobile/core/api_client.dart';
import 'package:safishacon_mobile/core/repository.dart';
import 'package:safishacon_mobile/core/token_store.dart';
import 'package:safishacon_mobile/main.dart';
import 'package:safishacon_mobile/state/app_state.dart';
import 'package:shared_preferences/shared_preferences.dart';

AppState _state(Locale locale) {
  final client = MockClient((request) async {
    if (request.url.path.endsWith('/config')) {
      return http.Response(jsonEncode({'demo_mode': false, 'demo_accounts': []}), 200);
    }
    return http.Response('{}', 401);
  });
  final api = ApiClient(baseUrl: 'http://api', tokens: MemoryTokenStore(), httpClient: client);
  return AppState(Repository(api), initialLocale: locale);
}

void main() {
  setUp(() => SharedPreferences.setMockInitialValues({}));

  testWidgets('signed-out users see the localized login screen', (tester) async {
    final state = _state(const Locale('en'));
    await tester.pumpWidget(SafishaApp(repo: state.repo, state: state));
    await state.bootstrap();
    await tester.pumpAndSettle();

    expect(find.text('Professional cleaning, without the hassle.'), findsOneWidget);
    expect(find.widgetWithText(FilledButton, 'Sign in'), findsOneWidget);

    await tester.tap(find.text('SW'));
    await tester.pumpAndSettle();
    expect(find.text('Usafi wa kitaalamu, bila usumbufu.'), findsOneWidget);
    expect(find.widgetWithText(FilledButton, 'Ingia'), findsOneWidget);
  });

  testWidgets('login form validates required fields', (tester) async {
    final state = _state(const Locale('en'));
    await tester.pumpWidget(SafishaApp(repo: state.repo, state: state));
    await state.bootstrap();
    await tester.pumpAndSettle();

    await tester.tap(find.widgetWithText(FilledButton, 'Sign in'));
    await tester.pump();
    expect(find.text('This field is required.'), findsNWidgets(2));
  });
}
