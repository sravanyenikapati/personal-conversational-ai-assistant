/// Animated microphone button — the centrepiece of the voice UI.
///
/// States:
///   idle       -> mint outline circle, mic icon
///   listening  -> pulsing glow rings, animated waveform
///   processing -> spinning arc

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../providers/chat_provider.dart';
import '../theme/aurora_theme.dart';

class MicButton extends StatefulWidget {
  const MicButton({super.key});

  @override
  State<MicButton> createState() => _MicButtonState();
}

class _MicButtonState extends State<MicButton> with TickerProviderStateMixin {
  late final AnimationController _pulseCtrl;
  late final AnimationController _spinCtrl;

  @override
  void initState() {
    super.initState();
    _pulseCtrl = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1200),
    )..repeat(reverse: true);

    _spinCtrl = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1000),
    )..repeat();
  }

  @override
  void dispose() {
    _pulseCtrl.dispose();
    _spinCtrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final provider = context.watch<ChatProvider>();
    final state    = provider.listeningState;

    return GestureDetector(
      onTap: () {
        if (state == ListeningState.idle) {
          provider.startListening();
        } else {
          provider.stopListening();
        }
      },
      child: SizedBox(
        width: 72,
        height: 72,
        child: Stack(
          alignment: Alignment.center,
          children: [
            if (state == ListeningState.listening) ...[
              _PulseRing(controller: _pulseCtrl, radius: 36, opacity: 0.25),
              _PulseRing(controller: _pulseCtrl, radius: 44, opacity: 0.12, delay: 0.3),
            ],
            if (state == ListeningState.processing)
              RotationTransition(
                turns: _spinCtrl,
                child: CustomPaint(
                  size: const Size(64, 64),
                  painter: _SpinArcPainter(),
                ),
              ),
            _ButtonCore(state: state),
          ],
        ),
      ),
    );
  }
}

class _ButtonCore extends StatelessWidget {
  const _ButtonCore({required this.state});
  final ListeningState state;

  @override
  Widget build(BuildContext context) {
    final isActive = state != ListeningState.idle;

    return AnimatedContainer(
      duration: const Duration(milliseconds: 200),
      width: 56,
      height: 56,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        color: isActive ? AuroraColors.accent : Colors.transparent,
        border: Border.all(
          color: AuroraColors.accent,
          width: isActive ? 0 : 2,
        ),
        boxShadow: isActive
            ? [BoxShadow(color: AuroraColors.accent.withOpacity(0.4), blurRadius: 16, spreadRadius: 2)]
            : [],
      ),
      child: Icon(
        state == ListeningState.idle ? Icons.mic_none_rounded : Icons.mic_rounded,
        color: isActive ? AuroraColors.background : AuroraColors.accent,
        size: 26,
      ),
    );
  }
}

class _PulseRing extends StatelessWidget {
  const _PulseRing({required this.controller, required this.radius, required this.opacity, this.delay = 0.0});

  final AnimationController controller;
  final double radius;
  final double opacity;
  final double delay;

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: controller,
      builder: (_, __) {
        final t = ((controller.value + delay) % 1.0);
        return Container(
          width:  radius * 2 * (0.85 + 0.15 * t),
          height: radius * 2 * (0.85 + 0.15 * t),
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            border: Border.all(
              color: AuroraColors.accent.withOpacity(opacity * (1 - t)),
              width: 1.5,
            ),
          ),
        );
      },
    );
  }
}

class _SpinArcPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = AuroraColors.accent
      ..strokeWidth = 2.5
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round;

    canvas.drawArc(
      Rect.fromCenter(center: Offset(size.width / 2, size.height / 2), width: size.width, height: size.height),
      0, 4.2,
      false,
      paint,
    );
  }

  @override
  bool shouldRepaint(_) => false;
}
