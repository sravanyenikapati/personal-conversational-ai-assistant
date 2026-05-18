/// Horizontal scrolling agent selector chip row.
///
/// Built-in agents: standard chip.
/// Custom agents:   chip + pencil edit icon.
/// Last item:       "+" add button to open CreateAgentScreen.

import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter/gestures.dart';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../models/agent.dart';
import '../providers/chat_provider.dart';
import '../screens/create_agent_screen.dart';
import '../theme/aurora_theme.dart';

class AgentSelector extends StatelessWidget {
  const AgentSelector({super.key});

  @override
  Widget build(BuildContext context) {
    final provider = context.watch<ChatProvider>();
    final agents   = provider.agents;
    final selected = provider.selectedAgent;

    return SizedBox(
      height: 48,
      child: ScrollConfiguration(
        behavior: kIsWeb ? _WebScrollBehavior() : ScrollConfiguration.of(context),
        child: ListView(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 2),
          scrollDirection: Axis.horizontal,
          children: [
            for (int i = 0; i < agents.length; i++) ...[
              if (i > 0) const SizedBox(width: 8),
              _AgentChip(agent: agents[i], isSelected: agents[i].id == selected.id),
            ],
            const SizedBox(width: 8),
            _AddChip(),
          ],
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Agent chip (built-in + custom with edit icon)
// ---------------------------------------------------------------------------

class _AgentChip extends StatelessWidget {
  const _AgentChip({required this.agent, required this.isSelected});

  final Agent agent;
  final bool isSelected;

  Future<void> _openEdit(BuildContext context) async {
    final api      = context.read<ChatProvider>().apiService;
    final details  = await api.getCustomAgentDetails(agent.id);
    if (details == null || !context.mounted) return;

    await Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => CreateAgentScreen(
          existingAgentId: agent.id,
          existingData: details,
        ),
      ),
    );
  }

  Future<void> _confirmDelete(BuildContext context) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        backgroundColor: AuroraColors.surface2,
        title: const Text('Delete agent?', style: TextStyle(color: AuroraColors.textPrimary)),
        content: Text(
          'Delete "${agent.name}"? This cannot be undone.',
          style: const TextStyle(color: AuroraColors.textSecondary),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancel', style: TextStyle(color: AuroraColors.textSecondary)),
          ),
          TextButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Delete', style: TextStyle(color: AuroraColors.error)),
          ),
        ],
      ),
    );

    if (confirmed == true && context.mounted) {
      final provider = context.read<ChatProvider>();
      await provider.deleteCustomAgent(agent.id);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        AnimatedContainer(
          duration: const Duration(milliseconds: 200),
          child: FilterChip(
            label: Text('${agent.emoji} ${agent.name}'),
            selected: isSelected,
            onSelected: (_) => context.read<ChatProvider>().selectAgent(agent),
            backgroundColor: AuroraColors.surface2,
            selectedColor: AuroraColors.accent.withOpacity(0.18),
            checkmarkColor: AuroraColors.accent,
            labelStyle: TextStyle(
              color: isSelected ? AuroraColors.accent : AuroraColors.textSecondary,
              fontSize: 13,
              fontWeight: isSelected ? FontWeight.w600 : FontWeight.normal,
            ),
            side: BorderSide(
              color: isSelected ? AuroraColors.accent : AuroraColors.border,
              width: isSelected ? 1.5 : 1.0,
            ),
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
            showCheckmark: false,
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
          ),
        ),
        if (agent.isCustom) ...[
          const SizedBox(width: 2),
          // Edit icon
          GestureDetector(
            onTap: () => _openEdit(context),
            onLongPress: () => _confirmDelete(context),
            child: Container(
              width: 24,
              height: 24,
              decoration: BoxDecoration(
                color: AuroraColors.surface2,
                shape: BoxShape.circle,
                border: Border.all(color: AuroraColors.border),
              ),
              child: const Icon(Icons.edit_outlined, size: 13, color: AuroraColors.textSecondary),
            ),
          ),
        ],
      ],
    );
  }
}

// ---------------------------------------------------------------------------
// "+" add new agent chip
// ---------------------------------------------------------------------------

class _AddChip extends StatelessWidget {
  const _AddChip();

  @override
  Widget build(BuildContext context) {
    return ActionChip(
      label: const Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(Icons.add_rounded, size: 16, color: AuroraColors.accent),
          SizedBox(width: 4),
          Text('New', style: TextStyle(color: AuroraColors.accent, fontSize: 13)),
        ],
      ),
      onPressed: () => Navigator.push(
        context,
        MaterialPageRoute(builder: (_) => const CreateAgentScreen()),
      ),
      backgroundColor: AuroraColors.surface2,
      side: const BorderSide(color: AuroraColors.accent, width: 1),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
    );
  }
}

// ---------------------------------------------------------------------------
// Web scroll behavior — mouse/trackpad drag on horizontal list
// ---------------------------------------------------------------------------

class _WebScrollBehavior extends MaterialScrollBehavior {
  @override
  Set<PointerDeviceKind> get dragDevices => {
        PointerDeviceKind.touch,
        PointerDeviceKind.mouse,
        PointerDeviceKind.trackpad,
      };
}
