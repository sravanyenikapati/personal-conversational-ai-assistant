/// Create / Edit Custom Agent screen.
///
/// Opens as a modal from the agent selector "+" button (create)
/// or the pencil icon on a custom agent chip (edit).
///
/// On save: calls the backend, refreshes the agent list, and pops.

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../providers/chat_provider.dart';
import '../services/api_service.dart';
import '../theme/aurora_theme.dart';

class CreateAgentScreen extends StatefulWidget {
  /// Pass existing agent data when editing; null when creating new.
  const CreateAgentScreen({super.key, this.existingAgentId, this.existingData});

  final String? existingAgentId;
  final Map<String, dynamic>? existingData;

  @override
  State<CreateAgentScreen> createState() => _CreateAgentScreenState();
}

class _CreateAgentScreenState extends State<CreateAgentScreen> {
  final _formKey  = GlobalKey<FormState>();
  final _namectrl = TextEditingController();
  final _descCtrl = TextEditingController();
  final _persCtrl = TextEditingController();
  final _knowCtrl = TextEditingController();
  final _discCtrl = TextEditingController();

  String _emoji = '\u{1F916}';
  bool _saving  = false;
  bool get _isEditing => widget.existingAgentId != null;

  // Common emojis for the picker
  static const _emojis = [
    '\u{1F916}','⭐','\u{1F525}','\u{1F4A1}','\u{1F3AF}','\u{1F9E0}',
    '\u{1F4DA}','\u{1F3A8}','\u{1F3B5}','\u{1F4BB}','⚖️','\u{1F4B0}',
    '\u{1F3E5}','\u{1F4BC}','✈️','\u{1F37D}️','\u{1F3CB}️',
    '\u{1F4AC}','\u{1F50D}','\u{1F6E0}️','\u{1F9EA}','\u{1F3D7}️',
    '\u{1F4CA}','\u{1F393}','\u{1F3A4}','\u{1F4F1}','\u{1F30D}','\u{1F4DD}',
    '\u{1F44D}','\u{1F9D1}‍\u{1F4BB}','\u{1F9D9}','\u{1F6B4}',
  ];

  @override
  void initState() {
    super.initState();
    if (_isEditing && widget.existingData != null) {
      final d = widget.existingData!;
      _emoji = d['emoji'] as String? ?? '\u{1F916}';
      _namectrl.text = d['name'] as String? ?? '';
      _descCtrl.text = d['description'] as String? ?? '';
      _persCtrl.text = d['personality'] as String? ?? '';
      _knowCtrl.text = d['knowledge'] as String? ?? '';
      _discCtrl.text = d['disclaimer'] as String? ?? '';
    }
  }

  @override
  void dispose() {
    _namectrl.dispose();
    _descCtrl.dispose();
    _persCtrl.dispose();
    _knowCtrl.dispose();
    _discCtrl.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() => _saving = true);

    final api = context.read<ChatProvider>().apiService;

    try {
      bool ok;
      if (_isEditing) {
        final updated = await api.updateCustomAgent(
          agentId:     widget.existingAgentId!,
          name:        _namectrl.text.trim(),
          emoji:       _emoji,
          description: _descCtrl.text.trim(),
          personality: _persCtrl.text.trim(),
          knowledge:   _knowCtrl.text.trim(),
          disclaimer:  _discCtrl.text.trim().isEmpty ? null : _discCtrl.text.trim(),
        );
        ok = updated != null;
      } else {
        final created = await api.createCustomAgent(
          name:        _namectrl.text.trim(),
          emoji:       _emoji,
          description: _descCtrl.text.trim(),
          personality: _persCtrl.text.trim(),
          knowledge:   _knowCtrl.text.trim(),
          disclaimer:  _discCtrl.text.trim().isEmpty ? null : _discCtrl.text.trim(),
        );
        ok = created != null;
      }

      if (!mounted) return;

      if (ok) {
        await context.read<ChatProvider>().refreshAgents();
        Navigator.pop(context, true);
      } else {
        _showError('Could not save agent. Is the backend running?');
      }
    } catch (e) {
      _showError('Error: $e');
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  void _showError(String msg) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(msg, style: const TextStyle(color: Colors.white)),
        backgroundColor: AuroraColors.error,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AuroraColors.background,
      appBar: AppBar(
        title: Text(_isEditing ? 'Edit Agent' : 'New Agent'),
        actions: [
          if (_saving)
            const Padding(
              padding: EdgeInsets.all(16),
              child: SizedBox(
                width: 20,
                height: 20,
                child: CircularProgressIndicator(
                  strokeWidth: 2,
                  color: AuroraColors.accent,
                ),
              ),
            )
          else
            TextButton(
              onPressed: _save,
              child: const Text('Save', style: TextStyle(color: AuroraColors.accent, fontWeight: FontWeight.w700)),
            ),
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(20),
        child: Form(
          key: _formKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Emoji picker
              _SectionLabel('Choose an emoji'),
              const SizedBox(height: 8),
              _EmojiPicker(
                selected: _emoji,
                emojis: _emojis,
                onSelect: (e) => setState(() => _emoji = e),
              ),
              const SizedBox(height: 24),

              // Name
              _SectionLabel('Name *'),
              const SizedBox(height: 6),
              _Field(
                controller: _namectrl,
                hint: 'e.g. My Cooking Expert',
                maxLength: 60,
                validator: (v) => (v == null || v.trim().isEmpty) ? 'Name is required' : null,
              ),
              const SizedBox(height: 20),

              // Description
              _SectionLabel('Short description *'),
              const SizedBox(height: 6),
              _Field(
                controller: _descCtrl,
                hint: 'e.g. Recipes, techniques, and meal planning',
                maxLength: 200,
                validator: (v) => (v == null || v.trim().isEmpty) ? 'Description is required' : null,
              ),
              const SizedBox(height: 20),

              // Personality
              _SectionLabel('Personality & tone *'),
              const SizedBox(height: 4),
              const Text(
                'How should it speak? e.g. "Friendly and enthusiastic, uses simple language"',
                style: TextStyle(color: AuroraColors.textSecondary, fontSize: 12),
              ),
              const SizedBox(height: 6),
              _Field(
                controller: _persCtrl,
                hint: 'Friendly, encouraging, concise...',
                maxLines: 3,
                maxLength: 1000,
                validator: (v) => (v == null || v.trim().isEmpty) ? 'Personality is required' : null,
              ),
              const SizedBox(height: 20),

              // Knowledge
              _SectionLabel('Knowledge & expertise *'),
              const SizedBox(height: 4),
              const Text(
                'What does it specialise in? The more detail you give, the better it performs.',
                style: TextStyle(color: AuroraColors.textSecondary, fontSize: 12),
              ),
              const SizedBox(height: 6),
              _Field(
                controller: _knowCtrl,
                hint: 'Focus on Italian cuisine, vegetarian cooking, food pairing...',
                maxLines: 5,
                maxLength: 2000,
                validator: (v) => (v == null || v.trim().isEmpty) ? 'Knowledge is required' : null,
              ),
              const SizedBox(height: 20),

              // Disclaimer (optional)
              _SectionLabel('Disclaimer (optional)'),
              const SizedBox(height: 4),
              const Text(
                'Shown below chat bubbles. Use for legal/health/finance agents.',
                style: TextStyle(color: AuroraColors.textSecondary, fontSize: 12),
              ),
              const SizedBox(height: 6),
              _Field(
                controller: _discCtrl,
                hint: 'For informational purposes only...',
                maxLength: 300,
              ),
              const SizedBox(height: 32),

              // Save button
              SizedBox(
                width: double.infinity,
                height: 52,
                child: ElevatedButton(
                  onPressed: _saving ? null : _save,
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AuroraColors.accent,
                    foregroundColor: AuroraColors.background,
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                    disabledBackgroundColor: AuroraColors.accent.withOpacity(0.4),
                  ),
                  child: _saving
                      ? const CircularProgressIndicator(color: AuroraColors.background, strokeWidth: 2)
                      : Text(
                          _isEditing ? 'Save Changes' : 'Create Agent',
                          style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w700),
                        ),
                ),
              ),
              const SizedBox(height: 24),
            ],
          ),
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Internal widgets
// ---------------------------------------------------------------------------

class _SectionLabel extends StatelessWidget {
  const _SectionLabel(this.text);
  final String text;

  @override
  Widget build(BuildContext context) => Text(
        text,
        style: const TextStyle(
          color: AuroraColors.textPrimary,
          fontSize: 14,
          fontWeight: FontWeight.w600,
        ),
      );
}

class _Field extends StatelessWidget {
  const _Field({
    required this.controller,
    required this.hint,
    this.maxLines = 1,
    this.maxLength,
    this.validator,
  });

  final TextEditingController controller;
  final String hint;
  final int maxLines;
  final int? maxLength;
  final String? Function(String?)? validator;

  @override
  Widget build(BuildContext context) {
    return TextFormField(
      controller: controller,
      maxLines: maxLines,
      maxLength: maxLength,
      style: const TextStyle(color: AuroraColors.textPrimary, fontSize: 14),
      validator: validator,
      decoration: InputDecoration(
        hintText: hint,
        hintStyle: const TextStyle(color: AuroraColors.textSecondary, fontSize: 14),
        filled: true,
        fillColor: AuroraColors.surface2,
        counterStyle: const TextStyle(color: AuroraColors.textSecondary, fontSize: 11),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: AuroraColors.border),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: AuroraColors.border),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: AuroraColors.accent, width: 1.5),
        ),
        errorBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: AuroraColors.error),
        ),
        contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      ),
    );
  }
}

class _EmojiPicker extends StatelessWidget {
  const _EmojiPicker({required this.selected, required this.emojis, required this.onSelect});

  final String selected;
  final List<String> emojis;
  final void Function(String) onSelect;

  @override
  Widget build(BuildContext context) {
    return Wrap(
      spacing: 8,
      runSpacing: 8,
      children: emojis.map((e) {
        final isSelected = e == selected;
        return GestureDetector(
          onTap: () => onSelect(e),
          child: AnimatedContainer(
            duration: const Duration(milliseconds: 150),
            width: 44,
            height: 44,
            decoration: BoxDecoration(
              color: isSelected ? AuroraColors.accent.withOpacity(0.18) : AuroraColors.surface2,
              borderRadius: BorderRadius.circular(10),
              border: Border.all(
                color: isSelected ? AuroraColors.accent : AuroraColors.border,
                width: isSelected ? 2 : 1,
              ),
            ),
            child: Center(child: Text(e, style: const TextStyle(fontSize: 22))),
          ),
        );
      }).toList(),
    );
  }
}
