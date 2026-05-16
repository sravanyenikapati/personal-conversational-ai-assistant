/// Agent model — mirrors the AgentInfo returned by GET /agents.

class Agent {
  final String id;
  final String name;
  final String emoji;
  final String description;
  final bool hasDisclaimer;
  final String? disclaimer;

  const Agent({
    required this.id,
    required this.name,
    required this.emoji,
    required this.description,
    required this.hasDisclaimer,
    this.disclaimer,
  });

  factory Agent.fromJson(Map<String, dynamic> json) => Agent(
        id:            json['id'] as String,
        name:          json['name'] as String,
        emoji:         json['emoji'] as String,
        description:   json['description'] as String,
        hasDisclaimer: json['has_disclaimer'] as bool? ?? false,
        disclaimer:    json['disclaimer'] as String?,
      );

  /// Fallback list used before the API responds.
  static const List<Agent> defaults = [
    Agent(id: 'general',  name: 'General',  emoji: '🤖', description: 'General assistant',          hasDisclaimer: false),
    Agent(id: 'health',   name: 'Health',   emoji: '🏥', description: 'Health & wellness guidance',  hasDisclaimer: true),
    Agent(id: 'career',   name: 'Career',   emoji: '💼', description: 'Career coaching',             hasDisclaimer: false),
    Agent(id: 'finance',  name: 'Finance',  emoji: '💰', description: 'Financial guidance',          hasDisclaimer: true),
    Agent(id: 'fitness',  name: 'Fitness',  emoji: '💪', description: 'Fitness & workouts',          hasDisclaimer: true),
    Agent(id: 'mental',   name: 'Mental',   emoji: '🧠', description: 'Mental wellness support',     hasDisclaimer: true),
    Agent(id: 'nutrition',name: 'Nutrition',emoji: '🥗', description: 'Nutrition & diet advice',     hasDisclaimer: true),
    Agent(id: 'learning', name: 'Learning', emoji: '📚', description: 'Learning & skill building',   hasDisclaimer: false),
    Agent(id: 'creative', name: 'Creative', emoji: '🎨', description: 'Creative writing & ideas',    hasDisclaimer: false),
  ];
}
