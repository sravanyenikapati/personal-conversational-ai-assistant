/// Profile screen — user preferences, voice settings, backend config, app info.

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../providers/chat_provider.dart';
import '../theme/aurora_theme.dart';

class ProfileScreen extends StatefulWidget {
  const ProfileScreen({super.key});

  @override
  State<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends State<ProfileScreen> {
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

  Future<void> _saveUrl() async {
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
        title: const Text('Profile'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_ios_new_rounded),
          onPressed: () => Navigator.pop(context),
        ),
      ),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          // ── Avatar header ────────────────────────────────────────────────
          Center(
            child: Column(
              children: [
                Container(
                  width: 80,
                  height: 80,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: AuroraColors.accent.withOpacity(0.15),
                    border: Border.all(color: AuroraColors.accent, width: 2),
                  ),
                  child: const Center(
                    child: Text(
                      'S',
                      style: TextStyle(
                        color: AuroraColors.accent,
                        fontSize: 32,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ),
                ),
                const SizedBox(height: 12),
                const Text(
                  'Sravan',
                  style: TextStyle(
                    color: AuroraColors.textPrimary,
                    fontSize: 18,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                const SizedBox(height: 4),
                const Text(
                  'sravankumaryenikapati@gmail.com',
                  style: TextStyle(color: AuroraColors.textSecondary, fontSize: 13),
                ),
                const SizedBox(height: 4),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
                  decoration: BoxDecoration(
                    color: AuroraColors.accent.withOpacity(0.1),
                    borderRadius: BorderRadius.circular(20),
                    border: Border.all(color: AuroraColors.accent.withOpacity(0.3)),
                  ),
                  child: const Text(
                    'Free Plan',
                    style: TextStyle(color: AuroraColors.accent, fontSize: 11, fontWeight: FontWeight.w600),
                  ),
                ),
              ],
            ),
          ),

          const SizedBox(height: 32),

          // ── Voice ────────────────────────────────────────────────────────
          _SectionHeader('Voice'),
          const SizedBox(height: 12),
          _ToggleTile(
            label: 'Text-to-speech',
            subtitle: 'Read AI responses aloud (voice input only)',
            value: provider.ttsEnabled,
            onChanged: (_) => provider.toggleTts(),
          ),

          const SizedBox(height: 28),

          // ── Backend ──────────────────────────────────────────────────────
          _SectionHeader('Backend'),
          const SizedBox(height: 12),
          Container(
            decoration: BoxDecoration(
              color: AuroraColors.surface,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: AuroraColors.border),
            ),
            padding: const EdgeInsets.fromLTRB(16, 4, 16, 16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                TextField(
                  controller: _urlCtrl,
                  style: const TextStyle(color: AuroraColors.textPrimary, fontSize: 13),
                  decoration: const InputDecoration(
                    labelText: 'API URL',
                    labelStyle: TextStyle(color: AuroraColors.textSecondary, fontSize: 13),
                    border: InputBorder.none,
                    focusedBorder: InputBorder.none,
                    enabledBorder: InputBorder.none,
                    filled: false,
                    contentPadding: EdgeInsets.symmetric(vertical: 12),
                  ),
                ),
                const Divider(height: 1),
                const SizedBox(height: 10),
                Row(
                  children: [
                    AnimatedContainer(
                      duration: const Duration(milliseconds: 400),
                      width: 8,
                      height: 8,
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        color: provider.backendOnline ? AuroraColors.accent : AuroraColors.error,
                      ),
                    ),
                    const SizedBox(width: 8),
                    Text(
                      provider.backendOnline ? 'Connected' : 'Offline',
                      style: TextStyle(
                        color: provider.backendOnline ? AuroraColors.accent : AuroraColors.error,
                        fontSize: 12,
                      ),
                    ),
                    const Spacer(),
                    ElevatedButton(
                      onPressed: _saving ? null : _saveUrl,
                      style: ElevatedButton.styleFrom(
                        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 10),
                        minimumSize: Size.zero,
                        tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                      ),
                      child: _saving
                          ? const SizedBox(
                              width: 16,
                              height: 16,
                              child: CircularProgressIndicator(strokeWidth: 2, color: AuroraColors.background),
                            )
                          : const Text('Connect', style: TextStyle(fontSize: 13)),
                    ),
                  ],
                ),
              ],
            ),
          ),

          const SizedBox(height: 28),

          // ── Session ──────────────────────────────────────────────────────
          _SectionHeader('Session'),
          const SizedBox(height: 12),
          _DangerTile(
            icon: Icons.delete_outline_rounded,
            label: 'Clear all history',
            subtitle: 'Removes all messages across agents',
            onTap: _confirmClearHistory,
          ),

          const SizedBox(height: 28),

          // ── App ──────────────────────────────────────────────────────────
          _SectionHeader('App'),
          const SizedBox(height: 12),
          Container(
            decoration: BoxDecoration(
              color: AuroraColors.surface,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: AuroraColors.border),
            ),
            child: Column(
              children: [
                _InfoTile(label: 'Version', value: '0.5.0'),
                const Divider(height: 1, indent: 16),
                _InfoTile(label: 'Build', value: 'Aurora Dark'),
                const Divider(height: 1, indent: 16),
                _InfoTile(label: 'Backend', value: 'Railway (FastAPI)'),
              ],
            ),
          ),

          const SizedBox(height: 40),
        ],
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Reusable small widgets
// ---------------------------------------------------------------------------

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
          title: Text(label, style: const TextStyle(color: AuroraColors.textPrimary, fontSize: 14)),
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

class _DangerTile extends StatelessWidget {
  const _DangerTile({required this.icon, required this.label, required this.subtitle, required this.onTap});

  final IconData icon;
  final String label;
  final String subtitle;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => Container(
        decoration: BoxDecoration(
          color: AuroraColors.surface,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: AuroraColors.border),
        ),
        child: ListTile(
          leading: Icon(icon, color: AuroraColors.error, size: 20),
          title: Text(label, style: const TextStyle(color: AuroraColors.textPrimary, fontSize: 14)),
          subtitle: Text(subtitle, style: const TextStyle(color: AuroraColors.textSecondary, fontSize: 12)),
          onTap: onTap,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        ),
      );
}

class _InfoTile extends StatelessWidget {
  const _InfoTile({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
        child: Row(
          children: [
            Text(label, style: const TextStyle(color: AuroraColors.textSecondary, fontSize: 13)),
            const Spacer(),
            Text(value, style: const TextStyle(color: AuroraColors.textPrimary, fontSize: 13)),
          ],
        ),
      );
}
