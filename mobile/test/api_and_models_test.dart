import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:safishacon_mobile/core/api_client.dart';
import 'package:safishacon_mobile/core/token_store.dart';
import 'package:safishacon_mobile/models/models.dart';
import 'package:safishacon_mobile/ui/widgets/common.dart';

void main() {
  group('ApiClient', () {
    test('refreshes an expired access token once and retries the request', () async {
      var meCalls = 0;
      final client = MockClient((request) async {
        if (request.url.path == '/api/v1/auth/refresh') {
          expect(jsonDecode(request.body)['refresh_token'], 'old-refresh');
          return http.Response(jsonEncode({'access_token': 'new-access', 'refresh_token': 'new-refresh'}), 200);
        }
        if (request.url.path == '/api/v1/auth/me') {
          meCalls++;
          if (request.headers['Authorization'] != 'Bearer new-access') {
            return http.Response(jsonEncode({'error': {'code': 'TOKEN_EXPIRED', 'message': 'expired'}}), 401);
          }
          return http.Response(jsonEncode({'id': '1'}), 200);
        }
        return http.Response('', 404);
      });
      final store = MemoryTokenStore();
      await store.writeRefreshToken('old-refresh');
      final api = ApiClient(baseUrl: 'http://api', tokens: store, httpClient: client);

      final me = await api.get('/auth/me');

      expect(me, {'id': '1'});
      expect(meCalls, 2);
      expect(await store.readRefreshToken(), 'new-refresh');
    });

    test('surfaces API error codes', () async {
      final client = MockClient((_) async => http.Response(
          jsonEncode({'error': {'code': 'DUPLICATE_REVIEW', 'message': 'Already reviewed'}}), 409));
      final api = ApiClient(baseUrl: 'http://api', tokens: MemoryTokenStore(), httpClient: client);
      expect(
        () => api.post('/reviews', {}),
        throwsA(isA<ApiException>().having((e) => e.code, 'code', 'DUPLICATE_REVIEW').having((e) => e.status, 'status', 409)),
      );
    });

    test('reports network failures distinctly', () async {
      final client = MockClient((_) async => throw Exception('offline'));
      final api = ApiClient(baseUrl: 'http://api', tokens: MemoryTokenStore(), httpClient: client);
      expect(() => api.get('/services', auth: false), throwsA(isA<ApiException>().having((e) => e.isNetwork, 'network', true)));
    });
  });

  group('models', () {
    test('parse a booking detail from the API shape', () {
      final b = BookingDetail.fromJson({
        'id': 'b1',
        'reference': 'SC-ABC123',
        'status': 'PROVIDER_ASSIGNED',
        'service': {'name_en': 'Deep Cleaning', 'name_sw': 'Usafi wa Kina', 'icon': 'sparkles'},
        'area_name': 'Mikocheni',
        'scheduled_date': '2026-10-02',
        'scheduled_start_time': '10:00:00',
        'estimated_duration_minutes': 375,
        'total_amount': '110000.00',
        'currency': 'TZS',
        'provider_name': 'Rehema Juma',
        'bedrooms': 3,
        'bathrooms': 2,
        'price_items': [
          {'label_en': 'Deep Cleaning', 'label_sw': 'Usafi wa Kina', 'quantity': 1, 'amount': '70000.00'},
        ],
        'history': [
          {'to_status': 'CONFIRMED', 'created_at': '2026-10-01T10:00:00Z'},
        ],
        'allowed_actions': ['CANCEL'],
      });
      expect(b.total, 110000);
      expect(b.startTime, '10:00');
      expect(b.serviceName('sw'), 'Usafi wa Kina');
      expect(b.priceItems.single.amount, 70000);
      expect(b.can('CANCEL'), isTrue);
      expect(b.can('REVIEW'), isFalse);
    });

    test('format helpers', () {
      expect(formatMoney(110000), 'TZS 110,000');
      expect(addMinutes('10:00', 375), '16:15');
      expect(addMinutes('22:00', 300), '23:59');
    });
  });
}
