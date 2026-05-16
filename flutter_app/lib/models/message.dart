/// Chat message model.
///
/// [isUser]    true = user bubble (right), false = assistant bubble (left)
/// [isStreaming] true while SSE tokens are still arriving — shows cursor
/// [agentId]   which agent produced this reply (for colour/icon lookup)

class Message {
  final String id;
  final bool isUser;
  String text;
  bool isStreaming;
  final String agentId;
  final DateTime timestamp;

  Message({
    required this.id,
    required this.isUser,
    required this.text,
    required this.agentId,
    this.isStreaming = false,
    DateTime? timestamp,
  }) : timestamp = timestamp ?? DateTime.now();

  Message copyWith({String? text, bool? isStreaming}) => Message(
        id: id,
        isUser: isUser,
        text: text ?? this.text,
        agentId: agentId,
        isStreaming: isStreaming ?? this.isStreaming,
        timestamp: timestamp,
      );
}
