/// Agent model — mirrors the AgentInfo returned by GET /agents.

class Agent {
  final String id;
  final String name;
  final String emoji;
  final String description;
  final bool hasDisclaimer;
  final String? disclaimer;
  final bool isCustom;

  const Agent({
    required this.id,
    required this.name,
    required this.emoji,
    required this.description,
    required this.hasDisclaimer,
    this.disclaimer,
    this.isCustom = false,
  });

  factory Agent.fromJson(Map<String, dynamic> json) => Agent(
        id:            json['id'] as String,
        name:          json['name'] as String,
        emoji:         json['emoji'] as String,
        description:   json['description'] as String,
        hasDisclaimer: json['has_disclaimer'] as bool? ?? false,
        disclaimer:    json['disclaimer'] as String?,
        isCustom:      json['is_custom'] as bool? ?? false,
      );

  Agent copyWith({
    String? name,
    String? emoji,
    String? description,
  }) =>
      Agent(
        id: id,
        name: name ?? this.name,
        emoji: emoji ?? this.emoji,
        description: description ?? this.description,
        hasDisclaimer: hasDisclaimer,
        disclaimer: disclaimer,
        isCustom: isCustom,
      );

  static const List<Agent> defaults = [
    Agent(id: 'general',  name: 'General',  emoji: '\u{1F916}', description: 'General assistant',         hasDisclaimer: false),
    Agent(id: 'health',   name: 'Health',   emoji: '\u{1F3E5}', description: 'Health & wellness guidance', hasDisclaimer: true),
    Agent(id: 'finance',  name: 'Finance',  emoji: '\u{1F4B0}', description: 'Financial guidance',         hasDisclaimer: true),
    Agent(id: 'legal',    name: 'Legal',    emoji: '⚖️', description: 'Legal information',       hasDisclaimer: true),
    Agent(id: 'career',   name: 'Career',   emoji: '\u{1F4BC}', description: 'Career coaching',            hasDisclaimer: false),
    Agent(id: 'tutor',    name: 'Tutor',    emoji: '\u{1F4DA}', description: 'Learning & education',       hasDisclaimer: false),
    Agent(id: 'travel',   name: 'Travel',   emoji: '✈️', description: 'Travel & lifestyle',      hasDisclaimer: false),
    Agent(id: 'tech',     name: 'Tech',     emoji: '\u{1F4BB}', description: 'Tech support & coding',      hasDisclaimer: false),
    Agent(id: 'creative', name: 'Creative', emoji: '\u{1F3A8}', description: 'Creative writing & ideas',   hasDisclaimer: false),
  ];
}
