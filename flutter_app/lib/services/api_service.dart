/// API Service — connects Flutter app to the Phase 2.5 FastAPI backend.
///
/// GET  /agents          -> List<Agent>
/// POST /chat/stream     -> SSE stream of token events
/// DELETE /chat          -> clear one agent history
/// DELETE /session       -> clear all agent histories

import 'dart:async';
import 'dart:convert';

import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

import '../models/agent.dart';

class ApiService {
  /// Web runs in the same host browser — use localhost.
  /// Android emulator maps host localhost to 10.0.2.2.
  static final String _defaultBaseUrl =
      kIsWeb ? 'http://localhost:8000' : 'http://10.0.2.2:8000';

  static const String _prefKey = 'backend_base_url';

  String _baseUrl = kIsWeb ? 'http://localhost:8000' : 'http://10.0.2.2:8000';

  ApiService() {
    _loadBaseUrl();
  }

  Future<void> _loadBaseUrl() async {
    final prefs = await SharedPreferences.getInstance();
    _baseUrl = prefs.getString(_prefKey) ?? _defaultBaseUrl;
  }

  Future<void> setBaseUrl(String url) async {
    _baseUrl = url.trimRight().replaceAll(RegExp(r'/$'), '');
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_prefKey, _baseUrl);
  }

  String get baseUrl => _baseUrl;

  // ---------------------------------------------------------------------------
  // GET /agents
  // ---------------------------------------------------------------------------

  Future<List<Agent>> fetchAgents() async {
    final uri = Uri.parse('$_baseUrl/agents');
    try {
      final response = await http.get(uri).timeout(const Duration(seconds: 10));
      if (response.statusCode == 200) {
        final List<dynamic> data = jsonDecode(response.body) as List<dynamic>;
        return data.map((j) => Agent.fromJson(j as Map<String, dynamic>)).toList();
      }
    } catch (_) {
      // fall through — caller uses Agent.defaults
    }
    return Agent.defaults;
  }

  // ---------------------------------------------------------------------------
  // POST /chat/stream  (Server-Sent Events)
  //
  // Yields SSE event maps:
  //   {"type": "session", "session_id": "...", "agent_id": "..."}
  //   {"type": "token",   "text": "..."}
  //   {"type": "done",    "disclaimer": null}
  // ---------------------------------------------------------------------------

  Stream<Map<String, dynamic>> streamChat({
    required String message,
    required String agentId,
    String? sessionId,
  }) async* {
    final uri = Uri.parse('$_baseUrl/chat/stream');
    final client = http.Client();

    try {
      final request = http.Request('POST', uri)
        ..headers['Content-Type'] = 'application/json'
        ..headers['Accept'] = 'text/event-stream'
        ..body = jsonEncode({
          'message': message,
          'agent_id': agentId,
          if (sessionId != null) 'session_id': sessionId,
        });

      final response = await client.send(request).timeout(const Duration(seconds: 30));

      if (response.statusCode != 200) {
        yield {'type': 'error', 'text': 'Server error ${response.statusCode}'};
        return;
      }

      final buffer = StringBuffer();

      await for (final chunk in response.stream.transform(utf8.decoder)) {
        buffer.write(chunk);
        final raw = buffer.toString();
        final lines = raw.split('\n');

        // Keep incomplete last line in buffer
        buffer.clear();
        buffer.write(lines.last);

        for (final line in lines.sublist(0, lines.length - 1)) {
          if (line.startsWith('data: ')) {
            try {
              final json = jsonDecode(line.substring(6)) as Map<String, dynamic>;
              yield json;
            } catch (_) {
              // skip malformed event
            }
          }
        }
      }

      // Flush remaining buffer
      final remaining = buffer.toString().trim();
      if (remaining.startsWith('data: ')) {
        try {
          yield jsonDecode(remaining.substring(6)) as Map<String, dynamic>;
        } catch (_) {}
      }
    } finally {
      client.close();
    }
  }

  // ---------------------------------------------------------------------------
  // DELETE /chat
  // ---------------------------------------------------------------------------

  Future<void> clearChat({required String sessionId, String agentId = 'general'}) async {
    final uri = Uri.parse('$_baseUrl/chat?session_id=$sessionId&agent_id=$agentId');
    try {
      await http.delete(uri).timeout(const Duration(seconds: 10));
    } catch (_) {}
  }

  // ---------------------------------------------------------------------------
  // DELETE /session
  // ---------------------------------------------------------------------------

  Future<void> clearSession(String sessionId) async {
    final uri = Uri.parse('$_baseUrl/session?session_id=$sessionId');
    try {
      await http.delete(uri).timeout(const Duration(seconds: 10));
    } catch (_) {}
  }

  // ---------------------------------------------------------------------------
  // GET /health
  // ---------------------------------------------------------------------------

  Future<bool> checkHealth() async {
    try {
      final uri = Uri.parse('$_baseUrl/health');
      final response = await http.get(uri).timeout(const Duration(seconds: 5));
      return response.statusCode == 200;
    } catch (_) {
      return false;
    }
  }
}
