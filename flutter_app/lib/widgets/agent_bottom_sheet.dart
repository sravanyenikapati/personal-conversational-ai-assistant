/// AgentBottomSheet — modal sheet for selecting an AI assistant.
///
/// Replaces the old horizontal chip row.
/// Usage: AgentBottomSheet.show(context)

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../models/agent.dart';
import '../providers/chat_provider.dart';
import '../screens/create_agent_screen.dart';
import '../theme/aurora_theme.dart';

class AgentBottomSheet extends StatelessWidget {
  const AgentBottomSheet({super.key});

  /// Open the sheet from any widget.
  static Future<void> show(BuildContext context) {
    return showModalBottomSheet(
      context: context,
      backgroundColor: Colors.transparent,
      isScrollControlled: true,
      builder: (_) => ChangeNotifierProvider.value(
        value: context.read<ChatProvider>(),
        child: const AgentBottomSheet(),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final provider = context.watch<ChatProvider>();
    final agents   = provider.agents;
    final selected = provider.selectedAgent;

    return Container(
      decoration: const BoxDecoration(
        color: AuroraColors.surface,
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      padding: const EdgeInsets.only(bottom: 32),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          // Drag handle
          Container(
            width: 40,
            height: 4,
            margin: const EdgeInsets.symmetric(vertical: 12),
            decoration: BoxDecoration(
              color: AuroraColors.border,
              borderRadius: BorderRadius.circular(2),
            ),
          ),

          // Header row
          Padding(
            padding: const EdgeInsets.fromLTRB(20, 4, 16, 8),
            child: Row(
              children: [
                const Text(
                  'Choose Assistant',
                  style: TextStyle(
                    color: AuroraColors.textPrimary,
                    fontSize: 16,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                const Spacer(),
                TextButton.icon(
                  onPressed: () {
                    Navigator.pop(context);
                    Navigator.push(
                      context,
                      MaterialPageRoute(builder: (_) => const CreateAgentScreen()),
                    );
                  },
                  icon: const Icon(Icons.add_rounded, size: 16, color: AuroraColors.accent),
                  label: const Text('New', style: TextStyle(color: AuroraColors.accent, fontSize: 13)),
                  style: TextButton.styleFrom(
                    padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
                    side: const BorderSide(color: AuroraColors.accent, width: 1),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
                    minimumSize: Size.zero,
                    tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                  ),
                ),
              ],
            ),
          ),

          const Divider(height: 1),

          // Agent list — constrained so it doesn't overflow on small screens
          ConstrainedBox(
            constraints: BoxConstraints(
              maxHeight: MediaQuery.of(context).size.height * 0.55,
            ),
            child: ListView.builder(
              shrinkWrap: true,
              itemCount: agents.length,
              itemBuilder: (ctx, i) => _AgentTile(
                agent: agents[i],
                isSelected: agents[i].id == selected.id,
                onSelect: () {
                  context.read<ChatProvider>().selectAgent(agents[i]);
                  Navigator.pop(context);
                },
                onEdit: agents[i].isCustom
                    ? () async {
                        Navigator.pop(context);
                        final api     = context.read<ChatProvider>().apiService;
                        final details = await api.getCustomAgentDetails(agents[i].id);
                        if (details == null || !context.mounted) return;
                        await Navigator.push(
                          context,
                          MaterialPageRoute(
                            builder: (_) => CreateAgentScreen(
                              existingAgentId: agents[i].id,
                              existingData: details,
                            ),
                          ),
                        );
                      }
                    : null,
                onDelete: agents[i].isCustom
                    ? () async {
                        Navigator.pop(context);
                        final confirmed = await showDialog<bool>(
                          context: context,
                          builder: (_) => AlertDialog(
                            backgroundColor: AuroraColors.surface2,
                            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                            title: const Text('Delete agent?', style: TextStyle(color: AuroraColors.textPrimary)),
                            content: Text(
                              'Delete "${agents[i].name}"? This cannot be undone.',
                              style: const TextStyle(color: AuroraColors.textSecondary),
                            ),
                            actions: [
                              TextButton(
                                onPressed: () => Navigator.pop(context, false),
                                child: const Text('Cancel', style: TextStyle(color: AuroraColors.textSecondary)),
                              ),
                              TextButton(
                                onPressed: () => Navigator.pop(context, true),
                                child: const Text('Delete', style: TextStyle(color: AuroraColors.error, fontWeight: FontWeight.w600)),
                              ),
                            ],
                          ),
                        );
                        if (confirmed == true && context.mounted) {
                          await context.read<ChatProvider>().deleteCustomAgent(agents[i].id);
                        }
                      }
                    : null,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

// ---------------------------------------------------------------------------

class _AgentTile extends StatelessWidget {
  const _AgentTile({
    required this.agent,
    required this.isSelected,
    required this.onSelect,
    this.onEdit,
    this.onDelete,
  });

  final Agent agent;
  final bool isSelected;
  final VoidCallback onSelect;
  final VoidCallback? onEdit;
  final VoidCallback? onDelete;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onSelect,
      onLongPress: onDelete,
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
        child: Row(
          children: [
            // Emoji box
            Container(
              width: 46,
              height: 46,
              decoration: BoxDecoration(
                color: isSelected
                    ? AuroraColors.accent.withOpacity(0.15)
                    : AuroraColors.surface2,
                borderRadius: BorderRadius.circular(12),
                border: Border.all(
                  color: isSelected ? AuroraColors.accent : AuroraColors.border,
                  width: isSelected ? 1.5 : 1,
                ),
              ),
              child: Center(
                child: Text(agent.emoji, style: const TextStyle(fontSize: 22)),
              ),
            ),
            const SizedBox(width: 14),

            // Name + description
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    agent.name,
                    style: TextStyle(
                      color: isSelected ? AuroraColors.accent : AuroraColors.textPrimary,
                      fontSize: 15,
                      fontWeight: isSelected ? FontWeight.w600 : FontWeight.normal,
                    ),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    agent.description,
                    style: const TextStyle(
                      color: AuroraColors.textSecondary,
                      fontSize: 12,
                    ),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                ],
              ),
            ),

            // Trailing: edit button for custom, checkmark for selected
            if (agent.isCustom && onEdit != null)
              IconButton(
                icon: const Icon(Icons.edit_outlined, size: 16, color: AuroraColors.textSecondary),
                onPressed: onEdit,
                padding: EdgeInsets.zero,
                constraints: const BoxConstraints(minWidth: 32, minHeight: 32),
              )
            else if (isSelected)
              const Icon(Icons.check_circle_rounded, color: AuroraColors.accent, size: 20),
          ],
        ),
      ),
    );
  }
}
