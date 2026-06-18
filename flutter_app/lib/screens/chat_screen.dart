/// Main chat screen — the primary UI of the app.
///
/// Layout (top to bottom):
///   AppBar         "AI Assistant" brand + tappable agent selector → bottom sheet
///   MessageList    scrollable bubble list
///   Divider
///   InputRow       text field + send + mic button

import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';

import '../providers/chat_provider.dart';
import '../theme/aurora_theme.dart';
import '../widgets/agent_bottom_sheet.dart';
import '../widgets/chat_bubble.dart';
import '../widgets/mic_button.dart';
import 'profile_screen.dart';
import 'settings_screen.dart';

class ChatScreen extends StatefulWidget {
  const ChatScreen({super.key});

  @override
  State<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> {
  final _controller = TextEditingController();
  final _scrollCtrl = ScrollController();
  final _focusNode  = FocusNode();

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

  Future<void> _confirmClearHistory(ChatProvider provider) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        backgroundColor: AuroraColors.surface2,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        title: const Text('Clear history?', style: TextStyle(color: AuroraColors.textPrimary)),
        content: const Text(
          'This will delete all messages across all agents.\nThis cannot be undone.',
          style: TextStyle(color: AuroraColors.textSecondary, height: 1.5),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancel', style: TextStyle(color: AuroraColors.textSecondary)),
          ),
          TextButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Clear', style: TextStyle(color: AuroraColors.error, fontWeight: FontWeight.w600)),
          ),
        ],
      ),
    );
    if (confirmed == true && mounted) {
      await provider.clearHistory();
    }
  }

  @override
  Widget build(BuildContext context) {
    final provider = context.watch<ChatProvider>();

    // Auto-scroll when new content arrives
    if (provider.messages.isNotEmpty) _scrollToBottom();

    final body = Column(
      children: [
        const Divider(height: 1),
        Expanded(child: _buildMessageList(provider)),
        const Divider(height: 1),
        _buildInputRow(context, provider),
      ],
    );

    return Scaffold(
      appBar: _buildAppBar(context, provider),
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
      toolbarHeight: 60,
      title: GestureDetector(
        onTap: () => AgentBottomSheet.show(context),
        behavior: HitTestBehavior.opaque,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: [
            const Text(
              'AI ASSISTANT',
              style: TextStyle(
                color: AuroraColors.textSecondary,
                fontSize: 10,
                fontWeight: FontWeight.w600,
                letterSpacing: 1.2,
              ),
            ),
            const SizedBox(height: 3),
            Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  '${provider.selectedAgent.emoji} ${provider.selectedAgent.name}',
                  style: const TextStyle(
                    color: AuroraColors.textPrimary,
                    fontSize: 16,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                const SizedBox(width: 4),
                const Icon(
                  Icons.keyboard_arrow_down_rounded,
                  color: AuroraColors.textSecondary,
                  size: 16,
                ),
                const SizedBox(width: 8),
                AnimatedContainer(
                  duration: const Duration(milliseconds: 400),
                  width: 7,
                  height: 7,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: provider.backendOnline
                        ? AuroraColors.accent
                        : AuroraColors.error,
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
      actions: [
        // Profile
        IconButton(
          icon: const Icon(Icons.person_outline_rounded, color: AuroraColors.textSecondary),
          tooltip: 'Profile',
          onPressed: () => Navigator.push(
            context,
            MaterialPageRoute(builder: (_) => const ProfileScreen()),
          ),
        ),
        // TTS toggle
        IconButton(
          icon: Icon(
            provider.ttsEnabled ? Icons.volume_up_rounded : Icons.volume_off_rounded,
            color: provider.ttsEnabled ? AuroraColors.accent : AuroraColors.textSecondary,
          ),
          tooltip: provider.ttsEnabled ? 'Mute voice' : 'Unmute voice',
          onPressed: provider.toggleTts,
        ),
        // Overflow menu
        PopupMenuButton<String>(
          icon: const Icon(Icons.more_vert_rounded, color: AuroraColors.textSecondary),
          color: AuroraColors.surface2,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
          onSelected: (value) async {
            if (value == 'clear') {
              await _confirmClearHistory(provider);
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
      return _EmptyState(
        agentName: provider.selectedAgent.name,
        emoji: provider.selectedAgent.emoji,
      );
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
        padding: EdgeInsets.fromLTRB(16, 8, 16, kIsWeb ? 16 : 12),
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
            if (!kIsWeb) const MicButton(),
          ],
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------------------

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
            style: const TextStyle(
              color: AuroraColors.textPrimary,
              fontSize: 18,
              fontWeight: FontWeight.w600,
            ),
          ),
          const SizedBox(height: 8),
          const Text(
            'Type a message or tap the mic to speak',
            style: TextStyle(color: AuroraColors.textSecondary, fontSize: 14),
          ),
          const SizedBox(height: 20),
          GestureDetector(
            onTap: () => AgentBottomSheet.show(context),
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
              decoration: BoxDecoration(
                color: AuroraColors.surface2,
                borderRadius: BorderRadius.circular(20),
                border: Border.all(color: AuroraColors.border),
              ),
              child: const Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(Icons.swap_horiz_rounded, color: AuroraColors.textSecondary, size: 16),
                  SizedBox(width: 6),
                  Text(
                    'Switch assistant',
                    style: TextStyle(color: AuroraColors.textSecondary, fontSize: 13),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}
