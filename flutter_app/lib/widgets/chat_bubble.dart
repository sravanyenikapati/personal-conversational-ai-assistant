/// Chat bubble widget.
///
/// User bubbles: right-aligned, navy blue fill.
/// Assistant bubbles: left-aligned, dark surface fill, streaming cursor.

import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';

import '../models/message.dart';
import '../theme/aurora_theme.dart';

class ChatBubble extends StatelessWidget {
  const ChatBubble({super.key, required this.message});

  final Message message;

  @override
  Widget build(BuildContext context) {
    final isUser = message.isUser;

    return Padding(
      padding: EdgeInsets.only(
        left:   isUser ? 56 : 16,
        right:  isUser ? 16 : 56,
        bottom: 10,
      ),
      child: Column(
        crossAxisAlignment: isUser ? CrossAxisAlignment.end : CrossAxisAlignment.start,
        children: [
          _buildBubble(context, isUser),
          const SizedBox(height: 3),
          _buildTimestamp(),
        ],
      ),
    );
  }

  Widget _buildBubble(BuildContext context, bool isUser) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      decoration: BoxDecoration(
        color: isUser ? AuroraColors.userBubble : AuroraColors.surface,
        borderRadius: BorderRadius.only(
          topLeft:     const Radius.circular(18),
          topRight:    const Radius.circular(18),
          bottomLeft:  Radius.circular(isUser ? 18 : 4),
          bottomRight: Radius.circular(isUser ? 4  : 18),
        ),
        border: isUser
            ? null
            : Border.all(color: AuroraColors.border, width: 1),
      ),
      child: _buildText(),
    ).animate().fadeIn(duration: 180.ms).slideY(begin: 0.08, end: 0);
  }

  Widget _buildText() {
    if (message.isStreaming && message.text.isEmpty) {
      // Show typing indicator while first token hasn't arrived yet
      return _TypingDots();
    }

    return RichText(
      text: TextSpan(
        children: [
          TextSpan(
            text: message.text,
            style: const TextStyle(
              color: AuroraColors.textPrimary,
              fontSize: 15,
              height: 1.55,
            ),
          ),
          if (message.isStreaming)
            WidgetSpan(
              alignment: PlaceholderAlignment.middle,
              child: _StreamingCursor(),
            ),
        ],
      ),
    );
  }

  Widget _buildTimestamp() {
    final h = message.timestamp.hour.toString().padLeft(2, '0');
    final m = message.timestamp.minute.toString().padLeft(2, '0');
    return Text(
      '$h:$m',
      style: const TextStyle(color: AuroraColors.textSecondary, fontSize: 11),
    );
  }
}

// Blinking cursor shown at end of streaming assistant message
class _StreamingCursor extends StatefulWidget {
  @override
  State<_StreamingCursor> createState() => _StreamingCursorState();
}

class _StreamingCursorState extends State<_StreamingCursor>
    with SingleTickerProviderStateMixin {
  late final AnimationController _ctrl;

  @override
  void initState() {
    super.initState();
    _ctrl = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 500),
    )..repeat(reverse: true);
  }

  @override
  void dispose() {
    _ctrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return FadeTransition(
      opacity: _ctrl,
      child: const Text(
        ' ▋',
        style: TextStyle(color: AuroraColors.accent, fontSize: 14),
      ),
    );
  }
}

// Three-dot typing indicator
class _TypingDots extends StatefulWidget {
  @override
  State<_TypingDots> createState() => _TypingDotsState();
}

class _TypingDotsState extends State<_TypingDots>
    with SingleTickerProviderStateMixin {
  late final AnimationController _ctrl;

  @override
  void initState() {
    super.initState();
    _ctrl = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 900),
    )..repeat();
  }

  @override
  void dispose() {
    _ctrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _ctrl,
      builder: (_, __) {
        final step = (_ctrl.value * 3).floor();
        return Row(
          mainAxisSize: MainAxisSize.min,
          children: List.generate(3, (i) {
            return Padding(
              padding: const EdgeInsets.symmetric(horizontal: 2),
              child: Opacity(
                opacity: i == step ? 1.0 : 0.3,
                child: const CircleAvatar(
                  radius: 4,
                  backgroundColor: AuroraColors.accent,
                ),
              ),
            );
          }),
        );
      },
    );
  }
}
