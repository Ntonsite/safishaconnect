import '../models/models.dart';
import 'api_client.dart';

/// Customer-facing API calls. Business rules (pricing, eligibility, transitions)
/// live in the backend; the app only renders what the API returns.
class Repository {
  final ApiClient api;
  Repository(this.api);

  // --- Auth -------------------------------------------------------------------------
  Future<void> login(String identifier, String password) async {
    final pair = await api.post('/auth/login', {
      'identifier': identifier,
      'password': password,
    }, false);
    await api.setSession(pair as Map<String, dynamic>);
  }

  Future<void> register({
    required String fullName,
    required String phone,
    String? email,
    required String password,
    required String locale,
  }) async {
    final pair = await api.post('/auth/register', {
      'full_name': fullName,
      'phone': phone,
      'email': (email == null || email.isEmpty) ? null : email,
      'password': password,
      'preferred_locale': locale,
    }, false);
    await api.setSession(pair as Map<String, dynamic>);
  }

  Future<Me> me() async => Me.fromJson(await api.get('/auth/me'));

  Future<void> logout() async {
    final refresh = await api.tokens.readRefreshToken();
    await api.clearSession();
    if (refresh != null) {
      try {
        await api.post('/auth/logout', {'refresh_token': refresh}, false);
      } catch (_) {}
    }
  }

  Future<void> updateLocale(String locale) =>
      api.patch('/auth/me', {'preferred_locale': locale});

  // --- Catalogue --------------------------------------------------------------------
  Future<List<Service>> services() async =>
      ((await api.get('/services', auth: false)) as List)
          .map((j) => Service.fromJson(j))
          .toList();

  Future<List<Area>> areas() async =>
      ((await api.get('/areas', auth: false)) as List)
          .map((j) => Area.fromJson(j))
          .toList();

  Future<Map<String, dynamic>> config() async =>
      await api.get('/config', auth: false) as Map<String, dynamic>;

  Future<Quote> quote(Map<String, dynamic> request) async =>
      Quote.fromJson(await api.post('/quotes', request, false));

  Future<List<Slot>> slots({
    required String serviceId,
    required String areaId,
    required String date,
    required int durationMinutes,
  }) async {
    final data = await api.get(
      '/availability',
      auth: false,
      query: {
        'service_id': serviceId,
        'area_id': areaId,
        'date': date,
        'duration_minutes': '$durationMinutes',
      },
    );
    return ((data as Map)['slots'] as List)
        .map((s) => Slot.fromJson(s))
        .toList();
  }

  // --- Bookings ---------------------------------------------------------------------
  Future<List<BookingSummary>> bookings(String scope) async =>
      ((await api.get('/bookings', query: {'scope': scope})) as List)
          .map((j) => BookingSummary.fromJson(j))
          .toList();

  Future<BookingDetail> booking(String id) async =>
      BookingDetail.fromJson(await api.get('/bookings/$id'));

  Future<BookingDetail> createBooking(
    Map<String, dynamic> body, {
    String? requestKey,
  }) async => BookingDetail.fromJson(
    requestKey == null
        ? await api.post('/bookings', body)
        : await api.postOnce('/bookings', body, requestKey),
  );

  Future<BookingDetail> cancel(String id) async =>
      BookingDetail.fromJson(await api.post('/bookings/$id/cancel', {}));

  Future<BookingDetail> confirmCompletion(String id) async =>
      BookingDetail.fromJson(
        await api.post('/bookings/$id/confirm-completion'),
      );

  Future<void> review(String bookingId, int rating, String? comment) =>
      api.post('/reviews', {
        'booking_id': bookingId,
        'rating': rating,
        'comment': comment,
      });

  Future<void> reportIssue(
    String bookingId,
    String category,
    String description,
  ) => api.post('/complaints', {
    'booking_id': bookingId,
    'category': category,
    'description': description,
  });
}
