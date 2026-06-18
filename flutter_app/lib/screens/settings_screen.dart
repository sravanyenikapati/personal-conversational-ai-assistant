/// Settings screen — backend URL and voice preferences.

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../providers/chat_provider.dart';
import '../theme/aurora_theme.dart';

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  late final TextEditingController _urlCtrl;
  bool _saving = false;

  @override
  void initState() {
    super.initState();
    final provider = context.read<ChatProvider>();
    _urlCtrl = TextEditingController(text: provider.apiService.baseUrl);
  }

  @override
  void dispose() {
    _urlCtrl.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    setState(() => _saving = true);
    await context.read<ChatProvider>().updateBackendUrl(_urlCtrl.text.trim());
    setState(() => _saving = false);
    if (!mounted) return;
    final online = context.read<ChatProvider>().backendOnline;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(online ? '✅ Connected to backend' : '❌ Backend unreachable'),
        backgroundColor: online ? AuroraColors.accentDim : AuroraColors.error,
        behavior: SnackBarBehavior.floating,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
      ),
    );
  }

  Future<void> _confirmClearHistory() async {
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
      await context.read<ChatProvider>().clearHistory();
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: const Text('History cleared'),
          backgroundColor: AuroraColors.surface2,
          behavior: SnackBarBehavior.floating,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final provider = context.watch<ChatProvider>();

    return Scaffold(
      appBar: AppBar(
        title: const Text('Settings'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_ios_new_rounded),
          onPressed: () => Navigator.pop(context),
        ),
      ),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          _SectionHeader('Backend'),
          const SizedBox(height: 12),
          TextField(
            controller: _urlCtrl,
            style: const TextStyle(color: AuroraColors.textPrimary, fontSize: 14),
            decoration: const InputDecoration(
              labelText: 'API URL',
              labelStyle: TextStyle(color: AuroraColors.textSecondary),
              hintText: 'https://your-backend.up.railway.app',
            ),
          ),
          const SizedBox(height: 8),
          const Text(
            'Leave as-is to use the production backend.\n'
            'Change only if running a local dev server.',
            style: TextStyle(color: AuroraColors.textSecondary, fontSize: 12, height: 1.6),
          ),
          const SizedBox(height: 16),
          ElevatedButton(
            onPressed: _saving ? null : _save,
            child: _saving
                ? const SizedBox(
                    width: 18,
                    height: 18,
                    child: CircularProgressIndicator(strokeWidth: 2, color: AuroraColors.background),
                  )
                : const Text('Connect'),
          ),
          const SizedBox(height: 32),
          _SectionHeader('Voice'),
          const SizedBox(height: 12),
          _ToggleTile(
            label: 'Text-to-speech',
            subtitle: 'Read AI responses aloud (voice input only)',
            value: provider.ttsEnabled,
            onChanged: (_) => provider.toggleTts(),
          ),
          const SizedBox(height: 32),
          _SectionHeader('Session'),
          const SizedBox(height: 12),
          ListTile(
            tileColor: AuroraColors.surface,
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(12),
              side: const BorderSide(color: AuroraColors.border),
            ),
            leading: const Icon(Icons.delete_outline_rounded, color: AuroraColors.error, size: 20),
            title: const Text('Clear all history', style: TextStyle(color: AuroraColors.textPrimary)),
            subtitle: const Text(
              'Removes messages for all agents',
              style: TextStyle(color: AuroraColors.textSecondary, fontSize: 12),
            ),
            onTap: _confirmClearHistory,
          ),
        ],
      ),
    );
  }
}

class _SectionHeader extends StatelessWidget {
  const _SectionHeader(this.title);
  final String title;

  @override
  Widget build(BuildContext context) => Text(
        title.toUpperCase(),
        style: const TextStyle(
          color: AuroraColors.accent,
          fontSize: 11,
          fontWeight: FontWeight.w700,
          letterSpacing: 1.4,
        ),
      );
}

class _ToggleTile extends StatelessWidget {
  const _ToggleTile({required this.label, required this.subtitle, required this.value, required this.onChanged});

  final String label;
  final String subtitle;
  final bool value;
  final ValueChanged<bool> onChanged;

  @override
  Widget build(BuildContext context) => Container(
        decoration: BoxDecoration(
          color: AuroraColors.surface,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: AuroraColors.border),
        ),
        child: SwitchListTile(
          title: Text(label, style: const TextStyle(color: AuroraColors.textPrimary)),
          subtitle: Text(subtitle, style: const TextStyle(color: AuroraColors.textSecondary, fontSize: 12)),
          value: value,
          onChanged: onChanged,
          activeColor: AuroraColors.accent,
          activeTrackColor: AuroraColors.accent.withOpacity(0.3),
          inactiveTrackColor: AuroraColors.surface2,
          inactiveThumbColor: AuroraColors.textSecondary,
        ),
      );
}
