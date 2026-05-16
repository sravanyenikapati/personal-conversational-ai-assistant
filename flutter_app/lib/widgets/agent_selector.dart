/// Horizontal scrolling agent selector chip row.

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../models/agent.dart';
import '../providers/chat_provider.dart';
import '../theme/aurora_theme.dart';

class AgentSelector extends StatelessWidget {
  const AgentSelector({super.key});

  @override
  Widget build(BuildContext context) {
    final provider = context.watch<ChatProvider>();
    final agents   = provider.agents;
    final selected = provider.selectedAgent;

    return SizedBox(
      height: 44,
      child: ListView.separated(
        padding: const EdgeInsets.symmetric(horizontal: 16),
        scrollDirection: Axis.horizontal,
        itemCount: agents.length,
        separatorBuilder: (_, __) => const SizedBox(width: 8),
        itemBuilder: (context, i) {
          final agent = agents[i];
          final isSelected = agent.id == selected.id;
          return _AgentChip(agent: agent, isSelected: isSelected);
        },
      ),
    );
  }
}

class _AgentChip extends StatelessWidget {
  const _AgentChip({required this.agent, required this.isSelected});

  final Agent agent;
  final bool isSelected;

  @override
  Widget build(BuildContext context) {
    return AnimatedContainer(
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
    );
  }
}
