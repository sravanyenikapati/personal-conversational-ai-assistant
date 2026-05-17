/// Main chat screen — the primary UI of the app.
///
/// Layout (top to bottom):
///   AppBar         agent name + online indicator + menu
///   AgentSelector  horizontal chip row
///   MessageList    scrollable bubble list
///   Divider
///   InputRow       text field + send + mic button

import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';

import '../providers/chat_provider.dart';
import '../theme/aurora_theme.dart';
import '../widgets/agent_selector.dart';
import '../widgets/chat_bubble.dart';
import '../widgets/mic_button.dart';
import 'settings_screen.dart';

class ChatScreen extends StatefulWidget {
  const ChatScreen({super.key});

  @override
  State<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> {
  final _controller   = TextEditingController();
  final _scrollCtrl   = ScrollController();
  final _focusNode    = FocusNode();

  @override
  void dispose() {
    _controller.dispose();
    _scrollCtrl.dispose();
    _focusNode.dispose();
    super.dispose();
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollCtrl.hasClients) {
        _scrollCtrl.animateTo(
          _scrollCtrl.position.maxScrollExtent,
          duration: const Duration(milliseconds: 200),
          curve: Curves.easeOut,
        );
      }
    });
  }

  void _send(ChatProvider provider) {
    final text = _controller.text.trim();
    if (text.isEmpty) return;
    _controller.clear();
    provider.sendMessage(text);
    _scrollToBottom();
    _focusNode.unfocus();
  }

  @override
  Widget build(BuildContext context) {
    final provider = context.watch<ChatProvider>();

    // Auto-scroll when new content arrives
    if (provider.messages.isNotEmpty) _scrollToBottom();

    final body = Column(
      children: [
        const AgentSelector(),
        const SizedBox(height: 4),
        const Divider(height: 1),
        Expanded(child: _buildMessageList(provider)),
        const Divider(height: 1),
        _buildInputRow(context, provider),
      ],
    );

    return Scaffold(
      appBar: _buildAppBar(context, provider),
      // On web: centre a max-720 px column so text never spans the full browser width
      body: kIsWeb
          ? Center(
              child: ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 720),
                child: body,
              ),
            )
          : body,
    );
  }

  PreferredSizeWidget _buildAppBar(BuildContext context, ChatProvider provider) {
    return AppBar(
      title: Row(
        children: [
          Text(
            '${provider.selectedAgent.emoji} ${provider.selectedAgent.name}',
            style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w600),
          ),
          const SizedBox(width: 10),
          AnimatedContainer(
            duration: const Duration(milliseconds: 400),
            width: 8,
            height: 8,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: provider.backendOnline ? AuroraColors.accent : AuroraColors.error,
            ),
          ),
        ],
      ),
      actions: [
        IconButton(
          icon: Icon(
            provider.ttsEnabled ? Icons.volume_up_rounded : Icons.volume_off_rounded,
            color: provider.ttsEnabled ? AuroraColors.accent : AuroraColors.textSecondary,
          ),
          tooltip: provider.ttsEnabled ? 'Mute voice' : 'Unmute voice',
          onPressed: provider.toggleTts,
        ),
        PopupMenuButton<String>(
          icon: const Icon(Icons.more_vert_rounded, color: AuroraColors.textSecondary),
          color: AuroraColors.surface2,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
          onSelected: (value) async {
            if (value == 'clear') {
              await provider.clearHistory();
            } else if (value == 'settings') {
              if (!context.mounted) return;
              Navigator.push(
                context,
                MaterialPageRoute(builder: (_) => const SettingsScreen()),
              );
            }
          },
          itemBuilder: (_) => [
            const PopupMenuItem(
              value: 'clear',
              child: Row(children: [
                Icon(Icons.delete_outline_rounded, color: AuroraColors.error, size: 20),
                SizedBox(width: 10),
                Text('Clear history', style: TextStyle(color: AuroraColors.textPrimary)),
              ]),
            ),
            const PopupMenuItem(
              value: 'settings',
              child: Row(children: [
                Icon(Icons.settings_outlined, color: AuroraColors.textSecondary, size: 20),
                SizedBox(width: 10),
                Text('Settings', style: TextStyle(color: AuroraColors.textPrimary)),
              ]),
            ),
          ],
        ),
      ],
    );
  }

  Widget _buildMessageList(ChatProvider provider) {
    if (provider.messages.isEmpty) {
      return _EmptyState(agentName: provider.selectedAgent.name, emoji: provider.selectedAgent.emoji);
    }

    return ListView.builder(
      controller: _scrollCtrl,
      padding: const EdgeInsets.symmetric(vertical: 12),
      itemCount: provider.messages.length,
      itemBuilder: (_, i) => ChatBubble(message: provider.messages[i]),
    );
  }

  Widget _buildInputRow(BuildContext context, ChatProvider provider) {
    final isListening = provider.listeningState == ListeningState.listening;

    // On web, Enter sends; Shift+Enter inserts a newline.
    // On mobile, the soft keyboard send button sends.
    final textField = TextField(
      controller: _controller,
      focusNode: _focusNode,
      maxLines: 5,
      minLines: 1,
      textInputAction: kIsWeb ? TextInputAction.done : TextInputAction.newline,
      style: const TextStyle(color: AuroraColors.textPrimary, fontSize: 15),
      decoration: InputDecoration(
        hintText: isListening
            ? provider.liveTranscript.isEmpty
                ? 'Listening…'
                : provider.liveTranscript
            : 'Message ${provider.selectedAgent.name}…',
        hintStyle: TextStyle(
          color: isListening ? AuroraColors.accent : AuroraColors.textSecondary,
          fontSize: 15,
        ),
        border: InputBorder.none,
        focusedBorder: InputBorder.none,
        enabledBorder: InputBorder.none,
        contentPadding: const EdgeInsets.symmetric(horizontal: 18, vertical: 12),
        suffixIcon: _controller.text.isEmpty
            ? null
            : IconButton(
                icon: const Icon(Icons.send_rounded, color: AuroraColors.accent),
                onPressed: () => _send(provider),
              ),
      ),
      onChanged: (_) => setState(() {}),
      onSubmitted: (_) => _send(provider),
    );

    // Intercept Enter key on web to send; Shift+Enter passes through.
    final wrappedField = kIsWeb
        ? KeyboardListener(
            focusNode: FocusNode(),
            onKeyEvent: (event) {
              if (event is KeyDownEvent &&
                  event.logicalKey == LogicalKeyboardKey.enter &&
                  !HardwareKeyboard.instance.isShiftPressed) {
                _send(provider);
              }
            },
            child: textField,
          )
        : textField;

    return SafeArea(
      child: Padding(
        padding: EdgeInsets.fromLTRB(
          16,
          8,
          16,
          kIsWeb ? 16 : 12, // extra bottom padding on web (no home bar)
        ),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.end,
          children: [
            Expanded(
              child: AnimatedContainer(
                duration: const Duration(milliseconds: 200),
                decoration: BoxDecoration(
                  color: AuroraColors.surface2,
                  borderRadius: BorderRadius.circular(24),
                  border: Border.all(
                    color: isListening ? AuroraColors.accent : AuroraColors.border,
                    width: isListening ? 1.5 : 1,
                  ),
                ),
                child: wrappedField,
              ),
            ),
            const SizedBox(width: 10),
            // Hide mic on web — speech API requires native platform
            if (!kIsWeb) const MicButton(),
          ],
        ),
      ),
    );
  }
}

class _EmptyState extends StatelessWidget {
  const _EmptyState({required this.agentName, required this.emoji});
  final String agentName;
  final String emoji;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(emoji, style: const TextStyle(fontSize: 56)),
          const SizedBox(height: 16),
          Text(
            'Chat with $agentName',
            style: const TextStyle(color: AuroraColors.textPrimary, fontSize: 18, fontWeight: FontWeight.w600),
          ),
          const SizedBox(height: 8),
          const Text(
            'Type a message or tap the mic to speak',
            style: TextStyle(color: AuroraColors.textSecondary, fontSize: 14),
          ),
        ],
      ),
    );
  }
}
