import 'dart:async';

import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../core/api_client.dart';
import '../core/repository.dart';
import '../models/models.dart';

enum AuthStatus { unknown, signedOut, signedIn }

/// Session + language state shared across the app.
class AppState extends ChangeNotifier {
  final Repository repo;
  AuthStatus status = AuthStatus.unknown;
  Me? me;
  Locale locale;
  bool demoMode = false;
  bool onboardingCompleted = false;
  Map<String, dynamic> brand = {};

  /// Demo customer credentials, only served by the API when DEMO_MODE is on.
  ({String email, String password})? demoCustomer;

  AppState(this.repo, {Locale? initialLocale})
    : locale = initialLocale ?? const Locale('en') {
    repo.api.onSessionExpired = () {
      me = null;
      status = AuthStatus.signedOut;
      notifyListeners();
    };
  }

  static const _localeKey = 'safisha.locale';
  static const onboardingKey = 'safisha.onboarding.completed';

  Future<void> completeOnboarding() async {
    if (onboardingCompleted) return;
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setBool(onboardingKey, true);
    } catch (_) {}
    onboardingCompleted = true;
    notifyListeners();
  }

  static Future<Locale> savedLocale() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final code = prefs.getString(_localeKey);
      if (code == 'en' || code == 'sw') return Locale(code!);
    } catch (_) {}
    return const Locale('en');
  }

  Future<void> bootstrap() async {
    try {
      onboardingCompleted =
          (await SharedPreferences.getInstance()).getBool(onboardingKey) ??
          false;
    } catch (_) {}
    // Optional public configuration must never delay an offline first launch.
    unawaited(_loadConfig());
    try {
      final hadSession = await repo.api.tokens.readRefreshToken() != null;
      if (hadSession) await completeOnboarding();
      if (await repo.api.refresh()) {
        me = await repo.me();
        status = me!.role == 'CUSTOMER'
            ? AuthStatus.signedIn
            : AuthStatus.signedOut;
      } else {
        status = AuthStatus.signedOut;
      }
    } catch (_) {
      status = AuthStatus.signedOut;
    }
    notifyListeners();
  }

  Future<void> _loadConfig() async {
    try {
      final config = await repo.config();
      brand = Map<String, dynamic>.from(config['brand'] as Map? ?? {});
      demoMode = config['demo_mode'] == true;
      for (final account in (config['demo_accounts'] as List? ?? const [])) {
        if (account['role'] == 'customer') {
          demoCustomer = (
            email: account['email'] as String,
            password: account['password'] as String,
          );
        }
      }
    } catch (_) {}
    notifyListeners();
  }

  Future<void> login(String identifier, String password) async {
    await repo.login(identifier, password);
    await _afterLogin();
  }

  Future<void> register({
    required String fullName,
    required String phone,
    String? email,
    required String password,
  }) async {
    await repo.register(
      fullName: fullName,
      phone: phone,
      email: email,
      password: password,
      locale: locale.languageCode,
    );
    await _afterLogin();
  }

  Future<void> _afterLogin() async {
    final profile = await repo.me();
    if (profile.role != 'CUSTOMER') {
      // The mobile app is for customers; providers and admins use the web portal.
      await repo.logout();
      throw ApiException(
        403,
        'CUSTOMERS_ONLY',
        'This app is for customers. Please use the web portal.',
      );
    }
    me = profile;
    await completeOnboarding();
    status = AuthStatus.signedIn;
    await setLocale(Locale(profile.preferredLocale), persistRemote: false);
    notifyListeners();
  }

  Future<void> logout() async {
    await repo.logout();
    me = null;
    status = AuthStatus.signedOut;
    notifyListeners();
  }

  Future<void> setLocale(Locale value, {bool persistRemote = true}) async {
    locale = value;
    notifyListeners();
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString(_localeKey, value.languageCode);
    } catch (_) {}
    if (persistRemote && status == AuthStatus.signedIn) {
      try {
        await repo.updateLocale(value.languageCode);
      } catch (_) {}
    }
  }
}
