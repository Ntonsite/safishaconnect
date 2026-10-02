// Data models mirroring the FastAPI schemas. Money arrives as decimal strings.

num _num(dynamic v) => v is num ? v : num.tryParse('$v') ?? 0;

String localized(Map<String, dynamic> json, String field, String locale) =>
    (json['${field}_$locale'] ?? json['${field}_en'] ?? '') as String;

class Me {
  final String id;
  final String fullName;
  final String phone;
  final String? email;
  final String role;
  final String preferredLocale;
  final String? defaultAreaId;
  final String? defaultAddress;

  Me.fromJson(Map<String, dynamic> j)
    : id = j['id'],
      fullName = j['full_name'],
      phone = j['phone'],
      email = j['email'],
      role = j['role'],
      preferredLocale = j['preferred_locale'] ?? 'en',
      defaultAreaId = j['default_area_id'],
      defaultAddress = j['default_address'];

  String get firstName => fullName.split(' ').first;
}

class ServiceOption {
  final String id;
  final String group;
  final Map<String, dynamic> raw;
  final num price;
  final int maxQuantity;

  ServiceOption.fromJson(Map<String, dynamic> j)
    : id = j['id'],
      group = j['group'],
      raw = j,
      price = _num(j['price_amount']),
      maxQuantity = j['max_quantity'] ?? 1;

  String name(String locale) => localized(raw, 'name', locale);
}

class Service {
  final String id;
  final String slug;
  final String icon;
  final Map<String, dynamic> raw;
  final num basePrice;
  final bool usesRooms;
  final int includedBedrooms;
  final int includedBathrooms;
  final int maxRooms;
  final List<ServiceOption> options;

  Service.fromJson(Map<String, dynamic> j)
    : id = j['id'],
      slug = j['slug'],
      icon = j['icon'],
      raw = j,
      basePrice = _num(j['base_price']),
      usesRooms = j['uses_rooms'] ?? false,
      includedBedrooms = j['included_bedrooms'] ?? 0,
      includedBathrooms = j['included_bathrooms'] ?? 0,
      maxRooms = j['max_rooms'] ?? 8,
      options = ((j['options'] ?? []) as List)
          .map((o) => ServiceOption.fromJson(o))
          .toList();

  String name(String locale) => localized(raw, 'name', locale);
  String summary(String locale) => localized(raw, 'summary', locale);
  List<ServiceOption> group(String g) =>
      options.where((o) => o.group == g).toList();
}

class Area {
  final String id;
  final String name;
  final String cityName;

  Area.fromJson(Map<String, dynamic> j)
    : id = j['id'],
      name = j['name'],
      cityName = j['city_name'] ?? '';
}

class PriceLine {
  final Map<String, dynamic> raw;
  final int quantity;
  final num amount;

  PriceLine.fromJson(Map<String, dynamic> j)
    : raw = j,
      quantity = j['quantity'] ?? 1,
      amount = _num(j['amount']);

  String label(String locale) => localized(raw, 'label', locale);
}

class Quote {
  final List<PriceLine> lines;
  final num total;
  final String currency;
  final int durationMinutes;

  Quote.fromJson(Map<String, dynamic> j)
    : lines = (j['lines'] as List).map((l) => PriceLine.fromJson(l)).toList(),
      total = _num(j['total_amount']),
      currency = j['currency'] ?? 'TZS',
      durationMinutes = j['estimated_duration_minutes'];
}

class Slot {
  final String start;
  final String end;
  final bool available;

  Slot.fromJson(Map<String, dynamic> j)
    : start = (j['start_time'] as String).substring(0, 5),
      end = (j['end_time'] as String).substring(0, 5),
      available = j['available'] == true;
}

class BookingSummary {
  final String id;
  final String reference;
  final String? areaId;
  final String status;
  final Map<String, dynamic> service;
  final String areaName;
  final DateTime date;
  final String startTime;
  final int durationMinutes;
  final num total;
  final String currency;
  final String? providerName;

  BookingSummary.fromJson(Map<String, dynamic> j)
    : id = j['id'],
      reference = j['reference'],
      areaId = j['area_id'],
      status = j['status'],
      service = j['service'],
      areaName = j['area_name'],
      date = DateTime.parse(j['scheduled_date']),
      startTime = (j['scheduled_start_time'] as String).substring(0, 5),
      durationMinutes = j['estimated_duration_minutes'],
      total = _num(j['total_amount']),
      currency = j['currency'] ?? 'TZS',
      providerName = j['provider_name'];

  String serviceName(String locale) => localized(service, 'name', locale);
  String get serviceIcon => service['icon'] ?? 'sparkles';
}

class StatusEvent {
  final String toStatus;
  final DateTime at;

  StatusEvent.fromJson(Map<String, dynamic> j)
    : toStatus = j['to_status'],
      at = DateTime.parse(j['created_at']).toLocal();
}

class BookingDetail extends BookingSummary {
  final String? addressLine;
  final Map<String, dynamic>? propertyType;
  final Map<String, dynamic>? size;
  final String? landmark;
  final int bedrooms;
  final int bathrooms;
  final List<PriceLine> priceItems;
  final List<StatusEvent> history;
  final Map<String, dynamic>? provider;
  final Map<String, dynamic>? payment;
  final Map<String, dynamic>? review;
  final List<String> allowedActions;

  BookingDetail.fromJson(super.j)
    : addressLine = j['address_line'],
      propertyType = j['property_type'],
      size = j['size'],
      landmark = j['landmark'],
      bedrooms = j['bedrooms'] ?? 0,
      bathrooms = j['bathrooms'] ?? 0,
      priceItems = ((j['price_items'] ?? []) as List)
          .map((l) => PriceLine.fromJson(l))
          .toList(),
      history = ((j['history'] ?? []) as List)
          .map((h) => StatusEvent.fromJson(h))
          .toList(),
      provider = j['provider'],
      payment = j['payment'],
      review = j['review'],
      allowedActions = List<String>.from(j['allowed_actions'] ?? const []),
      super.fromJson();

  bool can(String action) => allowedActions.contains(action);
}

/// Booking statuses that change without customer input — worth polling.
const liveStatuses = {
  'FINDING_PROVIDER',
  'REASSIGNMENT_REQUIRED',
  'PROVIDER_ASSIGNED',
  'PROVIDER_EN_ROUTE',
  'PROVIDER_ARRIVED',
  'SERVICE_IN_PROGRESS',
  'COMPLETED_BY_PROVIDER',
  'CUSTOMER_CONFIRMED',
};
