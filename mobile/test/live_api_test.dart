// Integration test against a running backend (skipped by default):
//   flutter test test/live_api_test.dart --dart-define=LIVE_API_URL=http://localhost:8000
import 'package:flutter_test/flutter_test.dart';
import 'package:intl/intl.dart';
import 'package:safishacon_mobile/core/api_client.dart';
import 'package:safishacon_mobile/core/repository.dart';
import 'package:safishacon_mobile/core/token_store.dart';

const liveUrl = String.fromEnvironment('LIVE_API_URL');

void main() {
  test('customer books, tracks and cancels through the real API', () async {
    final repo = Repository(ApiClient(baseUrl: liveUrl, tokens: MemoryTokenStore()));
    final config = await repo.config();
    final demo = (config['demo_accounts'] as List).firstWhere((a) => a['role'] == 'customer');
    await repo.login(demo['email'], demo['password']);
    final me = await repo.me();
    expect(me.role, 'CUSTOMER');

    final service = (await repo.services()).firstWhere((s) => s.slug == 'general-home-cleaning');
    final area = (await repo.areas()).firstWhere((a) => a.name == 'Kinondoni');
    final request = {
      'service_id': service.id,
      'property_type_option_id': service.group('PROPERTY_TYPE').first.id,
      'bedrooms': 2,
      'bathrooms': 1,
      'addons': [],
    };
    final quote = await repo.quote(request);
    expect(quote.total, 43000);

    // Find a bookable slot over the next few days.
    String? date;
    String? time;
    for (var i = 1; i <= 6 && time == null; i++) {
      final d = DateFormat('yyyy-MM-dd').format(DateTime.now().add(Duration(days: i)));
      final slots = await repo.slots(serviceId: service.id, areaId: area.id, date: d, durationMinutes: quote.durationMinutes);
      final free = slots.where((s) => s.available);
      if (free.isNotEmpty) {
        date = d;
        time = free.last.start;
      }
    }
    expect(time, isNotNull);

    final booking = await repo.createBooking({
      ...request,
      'area_id': area.id,
      'address_line': 'Flutter integration test, Plot 9',
      'scheduled_date': date,
      'scheduled_start_time': time,
      'payment_method': 'CASH',
    });
    expect(booking.status, 'FINDING_PROVIDER');
    expect((await repo.bookings('active')).any((b) => b.id == booking.id), isTrue);

    final cancelled = await repo.cancel(booking.id);
    expect(cancelled.status, 'CANCELLED');
    await repo.logout();
  }, skip: liveUrl.isEmpty ? 'Set --dart-define=LIVE_API_URL to run against a backend' : false);
}
