import 'dart:async';
import 'dart:convert';

import 'package:http/http.dart' as http;

import 'token_store.dart';

/// Error returned by the API: `{"error": {"code", "message"}}`.
class ApiException implements Exception {
  final int status;
  final String code;
  final String message;

  ApiException(this.status, this.code, this.message);

  bool get isNetwork => status == 0;

  @override
  String toString() => 'ApiException($status, $code, $message)';
}

/// Thin JSON client for the SafishaCon REST API with transparent token refresh.
/// The same endpoints are used by the React web app — no mobile-specific backend.
class ApiClient {
  final String baseUrl;
  final http.Client _http;
  final TokenStore tokens;
  String? _accessToken;
  Future<bool>? _refreshing;
  void Function()? onSessionExpired;

  ApiClient({required this.baseUrl, required this.tokens, http.Client? httpClient})
      : _http = httpClient ?? http.Client();

  bool get hasAccessToken => _accessToken != null;

  Future<void> setSession(Map<String, dynamic> tokenPair) async {
    _accessToken = tokenPair['access_token'] as String;
    await tokens.writeRefreshToken(tokenPair['refresh_token'] as String);
  }

  Future<void> clearSession() async {
    _accessToken = null;
    await tokens.clear();
  }

  Uri _uri(String path, [Map<String, String>? query]) =>
      Uri.parse('$baseUrl/api/v1$path').replace(queryParameters: query?.isEmpty ?? true ? null : query);

  Future<dynamic> get(String path, {Map<String, String>? query, bool auth = true}) =>
      _send('GET', path, query: query, auth: auth);

  Future<dynamic> post(String path, [Object? body, bool auth = true]) => _send('POST', path, body: body ?? {}, auth: auth);

  Future<dynamic> patch(String path, Object body) => _send('PATCH', path, body: body);

  Future<dynamic> _send(String method, String path,
      {Map<String, String>? query, Object? body, bool auth = true}) async {
    Future<http.Response> attempt() {
      final request = http.Request(method, _uri(path, query));
      request.headers['Accept'] = 'application/json';
      if (body != null) {
        request.headers['Content-Type'] = 'application/json';
        request.body = jsonEncode(body);
      }
      if (auth && _accessToken != null) request.headers['Authorization'] = 'Bearer $_accessToken';
      return _http.send(request).then(http.Response.fromStream).timeout(const Duration(seconds: 20));
    }

    http.Response response;
    try {
      response = await attempt();
      if (response.statusCode == 401 && auth && await refresh()) {
        response = await attempt();
      } else if (response.statusCode == 401 && auth) {
        onSessionExpired?.call();
      }
    } on ApiException {
      rethrow;
    } catch (_) {
      throw ApiException(0, 'NETWORK_ERROR', 'Network error');
    }
    return _decode(response);
  }

  dynamic _decode(http.Response response) {
    final text = utf8.decode(response.bodyBytes);
    final data = text.isEmpty ? null : jsonDecode(text);
    if (response.statusCode >= 200 && response.statusCode < 300) return data;
    final error = (data is Map && data['error'] is Map) ? data['error'] as Map : const {};
    throw ApiException(
      response.statusCode,
      (error['code'] ?? 'HTTP_ERROR') as String,
      (error['message'] ?? response.reasonPhrase ?? 'Error') as String,
    );
  }

  /// Rotate the refresh token. Concurrent callers share one in-flight refresh.
  Future<bool> refresh() {
    return _refreshing ??= () async {
      try {
        final stored = await tokens.readRefreshToken();
        if (stored == null) return false;
        final response = await _http.post(
          _uri('/auth/refresh'),
          headers: {'Content-Type': 'application/json'},
          body: jsonEncode({'refresh_token': stored}),
        );
        if (response.statusCode != 200) {
          await clearSession();
          return false;
        }
        await setSession(jsonDecode(utf8.decode(response.bodyBytes)) as Map<String, dynamic>);
        return true;
      } catch (_) {
        return false;
      } finally {
        scheduleMicrotask(() => _refreshing = null);
      }
    }();
  }
}
