import 'package:flutter/foundation.dart';

/// Build-time configuration. Override with:
///   flutter run --dart-define=API_BASE_URL=http://192.168.1.20:8000
class AppConfig {
  static const String _override = String.fromEnvironment('API_BASE_URL');
  static const String appName = String.fromEnvironment(
    'APP_NAME',
    defaultValue: 'SafishaCon',
  );

  /// Sensible local defaults: the Android emulator reaches the host via 10.0.2.2.
  static String get apiBaseUrl {
    if (_override.isNotEmpty) return _override.replaceAll(RegExp(r'/$'), '');
    if (!kIsWeb && defaultTargetPlatform == TargetPlatform.android) {
      return 'http://10.0.2.2:8000';
    }
    return 'http://localhost:8000';
  }
}
