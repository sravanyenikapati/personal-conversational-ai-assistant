/// API Service — connects Flutter app to the Phase 4 FastAPI backend.
///
/// Built-in agents:
///   GET  /agents          -> List<Agent>
///   POST /chat/stream     -> SSE stream of token events
///   DELETE /chat          -> clear one agent history
///   DELETE /session       -> clear all agent histories
///
/// Custom agents (Phase 4):
///   GET    /custom-agents       -> List of custom agents
///   POST   /custom-agents       -> Create custom agent
///   GET    /custom-agents/{id}  -> Get one custom agent
///   PUT    /custom-agents/{id}  -> Update custom agent
///   DELETE /custom-agents/{id}  -> Delete custom agent

import 'dart:async';
import 'dart:convert';

import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

import '../models/agent.dart';

class ApiService {
  /// Production URL injected at build time via --dart-define=API_URL=https://...
  /// Falls back to localhost (dev) if not set.
  static const String _compiledUrl =
      String.fromEnvironment('API_URL', defaultValue: '');

  static final String _defaultBaseUrl = _compiledUrl.isNotEmpty
      ? _compiledUrl
      : (kIsWeb ? 'http://localhost:8000' : 'http://10.0.2.2:8000');

  static const String _prefKey = 'backend_base_url';

  String _baseUrl = _defaultBaseUrl;

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
  // GET /agents  (built-in + custom)
  // ---------------------------------------------------------------------------

  Future<List<Agent>> fetchAgents() async {
    final uri = Uri.parse('$_baseUrl/agents');
    try {
      final response = await http.get(uri).timeout(const Duration(seconds: 10));
      if (response.statusCode == 200) {
        final List<dynamic> data = jsonDecode(response.body) as List<dynamic>;
        return data.map((j) => Agent.fromJson(j as Map<String, dynamic>)).toList();
      }
    } catch (_) {}
    return Agent.defaults;
  }

  // ---------------------------------------------------------------------------
  // POST /chat/stream  (Server-Sent Events)
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
        buffer.clear();
        buffer.write(lines.last);

        for (final line in lines.sublist(0, lines.length - 1)) {
          if (line.startsWith('data: ')) {
            try {
              final json = jsonDecode(line.substring(6)) as Map<String, dynamic>;
              yield json;
            } catch (_) {}
          }
        }
      }

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
  // DELETE /chat  and  DELETE /session
  // ---------------------------------------------------------------------------

  Future<void> clearChat({required String sessionId, String agentId = 'general'}) async {
    final uri = Uri.parse('$_baseUrl/chat?session_id=$sessionId&agent_id=$agentId');
    try {
      await http.delete(uri).timeout(const Duration(seconds: 10));
    } catch (_) {}
  }

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

  // ---------------------------------------------------------------------------
  // Custom Agents — Phase 4
  // ---------------------------------------------------------------------------

  Future<List<Agent>> fetchCustomAgents() async {
    final uri = Uri.parse('$_baseUrl/custom-agents');
    try {
      final resp = await http.get(uri).timeout(const Duration(seconds: 10));
      if (resp.statusCode == 200) {
        final List<dynamic> data = jsonDecode(resp.body) as List<dynamic>;
        return data.map((j) => Agent.fromJson({
          ...j as Map<String, dynamic>,
          'has_disclaimer': (j['disclaimer'] != null),
          'is_custom': true,
        })).toList();
      }
    } catch (_) {}
    return [];
  }

  Future<Agent?> createCustomAgent({
    required String name,
    required String emoji,
    required String description,
    required String personality,
    required String knowledge,
    String? disclaimer,
  }) async {
    final uri = Uri.parse('$_baseUrl/custom-agents');
    try {
      final resp = await http.post(
        uri,
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'name': name,
          'emoji': emoji,
          'description': description,
          'personality': personality,
          'knowledge': knowledge,
          if (disclaimer != null && disclaimer.isNotEmpty) 'disclaimer': disclaimer,
        }),
      ).timeout(const Duration(seconds: 10));

      if (resp.statusCode == 201) {
        final j = jsonDecode(resp.body) as Map<String, dynamic>;
        return Agent.fromJson({...j, 'has_disclaimer': j['disclaimer'] != null, 'is_custom': true});
      }
    } catch (_) {}
    return null;
  }

  Future<Agent?> updateCustomAgent({
    required String agentId,
    String? name,
    String? emoji,
    String? description,
    String? personality,
    String? knowledge,
    String? disclaimer,
  }) async {
    final uri = Uri.parse('$_baseUrl/custom-agents/$agentId');
    try {
      final body = <String, dynamic>{};
      if (name != null) body['name'] = name;
      if (emoji != null) body['emoji'] = emoji;
      if (description != null) body['description'] = description;
      if (personality != null) body['personality'] = personality;
      if (knowledge != null) body['knowledge'] = knowledge;
      if (disclaimer != null) body['disclaimer'] = disclaimer;

      final resp = await http.put(
        uri,
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode(body),
      ).timeout(const Duration(seconds: 10));

      if (resp.statusCode == 200) {
        final j = jsonDecode(resp.body) as Map<String, dynamic>;
        return Agent.fromJson({...j, 'has_disclaimer': j['disclaimer'] != null, 'is_custom': true});
      }
    } catch (_) {}
    return null;
  }

  Future<bool> deleteCustomAgent(String agentId) async {
    final uri = Uri.parse('$_baseUrl/custom-agents/$agentId');
    try {
      final resp = await http.delete(uri).timeout(const Duration(seconds: 10));
      return resp.statusCode == 204;
    } catch (_) {
      return false;
    }
  }

  Future<Map<String, dynamic>?> getCustomAgentDetails(String agentId) async {
    final uri = Uri.parse('$_baseUrl/custom-agents/$agentId');
    try {
      final resp = await http.get(uri).timeout(const Duration(seconds: 10));
      if (resp.statusCode == 200) {
        return jsonDecode(resp.body) as Map<String, dynamic>;
      }
    } catch (_) {}
    return null;
  }
}
