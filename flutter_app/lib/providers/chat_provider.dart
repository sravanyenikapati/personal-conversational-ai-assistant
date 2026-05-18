/// ChatProvider — ChangeNotifier that owns all chat state.

import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter_tts/flutter_tts.dart';
import 'package:speech_to_text/speech_to_text.dart';
import 'package:uuid/uuid.dart';

import '../models/agent.dart';
import '../models/message.dart';
import '../services/api_service.dart';

enum ListeningState { idle, listening, processing }

class ChatProvider extends ChangeNotifier {
  final ApiService _api;

  ChatProvider(this._api) {
    _loadAgents();
    _initTts();
  }

  // -- State -----------------------------------------------------------------

  List<Message> messages = [];
  List<Agent> agents = Agent.defaults;
  Agent _selectedAgent = Agent.defaults.first;
  Agent get selectedAgent => _selectedAgent;

  String _sessionId = const Uuid().v4();
  String get sessionId => _sessionId;

  ApiService get apiService => _api;

  bool _isResponding = false;
  bool get isResponding => _isResponding;

  ListeningState _listeningState = ListeningState.idle;
  ListeningState get listeningState => _listeningState;

  bool _backendOnline = false;
  bool get backendOnline => _backendOnline;

  String _liveTranscript = '';
  String get liveTranscript => _liveTranscript;

  // -- TTS / STT internals ---------------------------------------------------

  final FlutterTts _tts = FlutterTts();
  final SpeechToText _stt = SpeechToText();
  bool _sttReady = false;
  bool _ttsEnabled = true;
  bool get ttsEnabled => _ttsEnabled;

  // -- Init ------------------------------------------------------------------

  Future<void> _loadAgents() async {
    _backendOnline = await _api.checkHealth();
    if (_backendOnline) {
      agents = await _api.fetchAgents();
      if (agents.isNotEmpty) _selectedAgent = agents.first;
    }
    notifyListeners();
  }

  Future<void> _initTts() async {
    await _tts.setLanguage('en-US');
    await _tts.setSpeechRate(0.52);
    await _tts.setPitch(1.0);
    await _tts.setVolume(1.0);
  }

  // -- Agent selection -------------------------------------------------------

  void selectAgent(Agent agent) {
    if (_selectedAgent.id == agent.id) return;
    _selectedAgent = agent;
    notifyListeners();
  }

  /// Refresh agent list from backend (called after create/edit/delete).
  Future<void> refreshAgents() async {
    _backendOnline = await _api.checkHealth();
    if (_backendOnline) {
      final fresh = await _api.fetchAgents();
      if (fresh.isNotEmpty) {
        agents = fresh;
        // Keep selected agent if it still exists; otherwise fall back to general.
        final stillExists = agents.any((a) => a.id == _selectedAgent.id);
        if (!stillExists) {
          _selectedAgent = agents.firstWhere(
            (a) => a.id == 'general',
            orElse: () => agents.first,
          );
        }
      }
    }
    notifyListeners();
  }

  /// Delete a custom agent, deselect if currently selected, refresh list.
  Future<void> deleteCustomAgent(String agentId) async {
    await _api.deleteCustomAgent(agentId);
    await refreshAgents();
  }

  // -- Send message ----------------------------------------------------------

  Future<void> sendMessage(String text) async {
    final trimmed = text.trim();
    if (trimmed.isEmpty || _isResponding) return;

    await _tts.stop();

    final userMsg = Message(
      id: const Uuid().v4(),
      isUser: true,
      text: trimmed,
      agentId: _selectedAgent.id,
    );
    messages.add(userMsg);
    _isResponding = true;
    notifyListeners();

    final assistantMsg = Message(
      id: const Uuid().v4(),
      isUser: false,
      text: '',
      agentId: _selectedAgent.id,
      isStreaming: true,
    );
    messages.add(assistantMsg);
    notifyListeners();

    String sessionIdForRequest = _sessionId;
    final sentenceBuf = StringBuffer();

    try {
      await for (final event in _api.streamChat(
        message: trimmed,
        agentId: _selectedAgent.id,
        sessionId: sessionIdForRequest,
      )) {
        switch (event['type']) {
          case 'session':
            final sid = event['session_id'] as String?;
            if (sid != null) _sessionId = sid;

          case 'token':
            final chunk = event['text'] as String? ?? '';
            assistantMsg.text += chunk;
            sentenceBuf.write(chunk);

            if (_ttsEnabled) {
              final pending = sentenceBuf.toString();
              final match = RegExp(r'(?<=[.!?])\s').firstMatch(pending);
              if (match != null) {
                final sentence = pending.substring(0, match.start + 1).trim();
                sentenceBuf.clear();
                sentenceBuf.write(pending.substring(match.end));
                if (sentence.isNotEmpty) unawaited(_tts.speak(sentence));
              }
            }
            notifyListeners();

          case 'done':
            if (_ttsEnabled && sentenceBuf.isNotEmpty) {
              final remainder = sentenceBuf.toString().trim();
              if (remainder.isNotEmpty) unawaited(_tts.speak(remainder));
            }
            assistantMsg.isStreaming = false;
            notifyListeners();

          case 'error':
            assistantMsg.text = event['text'] as String? ?? 'Something went wrong.';
            assistantMsg.isStreaming = false;
            notifyListeners();
        }
      }
    } catch (e) {
      assistantMsg.text = 'Connection error. Is the backend running?';
      assistantMsg.isStreaming = false;
    }

    _isResponding = false;
    notifyListeners();
  }

  // -- STT -------------------------------------------------------------------

  Future<void> startListening() async {
    if (_listeningState != ListeningState.idle) return;

    _sttReady = _sttReady || await _stt.initialize(
      onError: (_) => _stopListening(),
    );

    if (!_sttReady) return;

    _listeningState = ListeningState.listening;
    _liveTranscript = '';
    notifyListeners();

    await _stt.listen(
      onResult: (result) {
        _liveTranscript = result.recognizedWords;
        notifyListeners();
        if (result.finalResult) {
          _stopListening();
          if (_liveTranscript.isNotEmpty) {
            sendMessage(_liveTranscript);
            _liveTranscript = '';
          }
        }
      },
      listenFor: const Duration(seconds: 30),
      pauseFor: const Duration(seconds: 3),
      localeId: 'en_US',
    );
  }

  Future<void> _stopListening() async {
    await _stt.stop();
    _listeningState = ListeningState.idle;
    notifyListeners();
  }

  Future<void> stopListening() => _stopListening();

  // -- TTS toggle ------------------------------------------------------------

  void toggleTts() {
    _ttsEnabled = !_ttsEnabled;
    if (!_ttsEnabled) _tts.stop();
    notifyListeners();
  }

  // -- Clear history ---------------------------------------------------------

  Future<void> clearHistory() async {
    await _api.clearSession(_sessionId);
    messages.clear();
    _sessionId = const Uuid().v4();
    notifyListeners();
  }

  // -- Settings --------------------------------------------------------------

  Future<void> updateBackendUrl(String url) async {
    await _api.setBaseUrl(url);
    await refreshAgents();
  }

  @override
  void dispose() {
    _tts.stop();
    _stt.stop();
    super.dispose();
  }
}
