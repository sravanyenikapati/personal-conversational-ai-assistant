/// Aurora Dark theme — confirmed palette:
///   Accent:     #3DF5B8  (mint green)
///   Background: #080D12  (deep navy)
///   Surface:    #0F1923  (card/surface)
///   Surface2:   #162130  (input / elevated)
///   Text:       #E8F4F0  (primary)
///   TextMuted:  #6B8FA0  (secondary / timestamps)
///   Error:      #FF5A5A

import 'package:flutter/material.dart';

class AuroraColors {
  AuroraColors._();

  static const Color accent     = Color(0xFF3DF5B8);
  static const Color accentDim  = Color(0xFF27A87D);
  static const Color background = Color(0xFF080D12);
  static const Color surface    = Color(0xFF0F1923);
  static const Color surface2   = Color(0xFF162130);
  static const Color border     = Color(0xFF1E3042);
  static const Color textPrimary   = Color(0xFFE8F4F0);
  static const Color textSecondary = Color(0xFF6B8FA0);
  static const Color error      = Color(0xFFFF5A5A);
  static const Color userBubble = Color(0xFF1A3F5C);
}

ThemeData buildAuroraTheme() {
  const colorScheme = ColorScheme.dark(
    primary:   AuroraColors.accent,
    secondary: AuroraColors.accentDim,
    surface:   AuroraColors.surface,
    error:     AuroraColors.error,
    onPrimary: AuroraColors.background,
    onSecondary: AuroraColors.background,
    onSurface: AuroraColors.textPrimary,
    onError:   AuroraColors.textPrimary,
  );

  return ThemeData(
    useMaterial3: true,
    colorScheme: colorScheme,
    scaffoldBackgroundColor: AuroraColors.background,

    appBarTheme: const AppBarTheme(
      backgroundColor: AuroraColors.background,
      foregroundColor: AuroraColors.textPrimary,
      elevation: 0,
      centerTitle: false,
    ),

    cardTheme: CardThemeData(
      color: AuroraColors.surface,
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
        side: const BorderSide(color: AuroraColors.border),
      ),
    ),

    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: AuroraColors.surface2,
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(24),
        borderSide: const BorderSide(color: AuroraColors.border),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(24),
        borderSide: const BorderSide(color: AuroraColors.border),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(24),
        borderSide: const BorderSide(color: AuroraColors.accent, width: 1.5),
      ),
      hintStyle: const TextStyle(color: AuroraColors.textSecondary),
      contentPadding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
    ),

    textTheme: const TextTheme(
      bodyLarge:   TextStyle(color: AuroraColors.textPrimary,   fontSize: 15, height: 1.5),
      bodyMedium:  TextStyle(color: AuroraColors.textPrimary,   fontSize: 14, height: 1.5),
      bodySmall:   TextStyle(color: AuroraColors.textSecondary, fontSize: 12),
      labelSmall:  TextStyle(color: AuroraColors.textSecondary, fontSize: 11),
      titleMedium: TextStyle(color: AuroraColors.textPrimary,   fontSize: 16, fontWeight: FontWeight.w600),
      titleLarge:  TextStyle(color: AuroraColors.textPrimary,   fontSize: 20, fontWeight: FontWeight.w700),
    ),

    dividerTheme: const DividerThemeData(
      color: AuroraColors.border,
      thickness: 1,
    ),

    elevatedButtonTheme: ElevatedButtonThemeData(
      style: ElevatedButton.styleFrom(
        backgroundColor: AuroraColors.accent,
        foregroundColor: AuroraColors.background,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(24)),
        padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 14),
      ),
    ),
  );
}
