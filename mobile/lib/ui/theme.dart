import 'package:flutter/material.dart';

/// Brand palette shared with the web app's design tokens.
class Brand {
  static const radius = 12.0;
  static const pagePadding = 20.0;
  static const sectionGap = 24.0;
  static const green25 = Color(0xFFF7FBF8);
  static const green50 = Color(0xFFEFF7F1);
  static const green100 = Color(0xFFE1F0E5);
  static const green300 = Color(0xFF9CCFAE);
  static const green500 = Color(0xFF2E9E5B);
  static const green600 = Color(0xFF23834A);
  static const green700 = Color(0xFF1B6B3C);
  static const green900 = Color(0xFF0F3D24);
  static const ink = Color(0xFF1D2621);
  static const ink2 = Color(0xFF47524C);
  static const ink3 = Color(0xFF59665E);
  static const line = Color(0xFFE5E8E3);
  static const canvas = Color(0xFFFAFAF7);
  static const amber50 = Color(0xFFFDF6E7);
  static const amber700 = Color(0xFF8A520E);
  static const red50 = Color(0xFFFDF0ED);
  static const red600 = Color(0xFFB42318);
  static const teal50 = Color(0xFFEDF5F7);
  static const teal600 = Color(0xFF2B6A80);
}

ThemeData buildTheme() {
  final scheme = ColorScheme.fromSeed(
    seedColor: Brand.green700,
    brightness: Brightness.light,
    primary: Brand.green700,
    surface: Colors.white,
  );
  final radius = BorderRadius.circular(Brand.radius);
  final base = ThemeData(
    fontFamily: 'DMSans',
    useMaterial3: true,
    colorScheme: scheme,
    scaffoldBackgroundColor: Brand.canvas,
  );
  return base.copyWith(
    textTheme: base.textTheme
        .apply(bodyColor: Brand.ink, displayColor: Brand.ink)
        .copyWith(
          headlineMedium: const TextStyle(
            fontFamily: 'DMSans',
            fontSize: 26,
            fontWeight: FontWeight.w600,
            color: Brand.ink,
            height: 1.15,
          ),
          titleLarge: const TextStyle(
            fontFamily: 'DMSans',
            fontSize: 20,
            fontWeight: FontWeight.w600,
            color: Brand.ink,
          ),
          bodyLarge: const TextStyle(
            fontFamily: 'DMSans',
            fontSize: 16,
            height: 1.5,
            color: Brand.ink,
          ),
          bodyMedium: const TextStyle(
            fontFamily: 'DMSans',
            fontSize: 14,
            height: 1.5,
            color: Brand.ink,
          ),
          bodySmall: const TextStyle(
            fontFamily: 'DMSans',
            fontSize: 12,
            height: 1.4,
            color: Brand.ink3,
          ),
          titleMedium: const TextStyle(
            fontFamily: 'DMSans',
            fontSize: 16,
            fontWeight: FontWeight.w600,
            color: Brand.ink,
          ),
        ),
    bottomSheetTheme: const BottomSheetThemeData(
      backgroundColor: Colors.white,
      showDragHandle: true,
      elevation: 0,
    ),
    dialogTheme: DialogThemeData(
      backgroundColor: Colors.white,
      shape: RoundedRectangleBorder(borderRadius: radius),
    ),
    snackBarTheme: SnackBarThemeData(
      behavior: SnackBarBehavior.floating,
      backgroundColor: Brand.ink,
      shape: RoundedRectangleBorder(borderRadius: radius),
    ),
    textButtonTheme: TextButtonThemeData(
      style: TextButton.styleFrom(
        minimumSize: const Size(48, 48),
        textStyle: const TextStyle(
          fontFamily: 'DMSans',
          fontWeight: FontWeight.w600,
        ),
      ),
    ),
    appBarTheme: const AppBarTheme(
      backgroundColor: Colors.white,
      foregroundColor: Brand.ink,
      elevation: 0,
      scrolledUnderElevation: 0.5,
      centerTitle: false,
      titleTextStyle: TextStyle(
        fontFamily: 'DMSans',
        fontSize: 18,
        fontWeight: FontWeight.w700,
        color: Brand.ink,
      ),
    ),
    cardTheme: CardThemeData(
      color: Colors.white,
      elevation: 0,
      margin: EdgeInsets.zero,
      shape: RoundedRectangleBorder(
        borderRadius: radius,
        side: const BorderSide(color: Brand.line),
      ),
    ),
    filledButtonTheme: FilledButtonThemeData(
      style: FilledButton.styleFrom(
        backgroundColor: Brand.green700,
        foregroundColor: Colors.white,
        minimumSize: const Size.fromHeight(52),
        shape: RoundedRectangleBorder(borderRadius: radius),
        textStyle: const TextStyle(fontSize: 16, fontWeight: FontWeight.w600),
      ),
    ),
    outlinedButtonTheme: OutlinedButtonThemeData(
      style: OutlinedButton.styleFrom(
        foregroundColor: Brand.ink,
        minimumSize: const Size.fromHeight(52),
        side: const BorderSide(color: Color(0xFFD4D9D2)),
        shape: RoundedRectangleBorder(borderRadius: radius),
        textStyle: const TextStyle(fontSize: 16, fontWeight: FontWeight.w600),
      ),
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: Colors.white,
      contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
      border: OutlineInputBorder(
        borderRadius: radius,
        borderSide: const BorderSide(color: Color(0xFFD4D9D2)),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: radius,
        borderSide: const BorderSide(color: Color(0xFFD4D9D2)),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: radius,
        borderSide: const BorderSide(color: Brand.green600, width: 1.5),
      ),
    ),
    chipTheme: base.chipTheme.copyWith(
      backgroundColor: Colors.white,
      selectedColor: Brand.green50,
      side: const BorderSide(color: Brand.line),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
    ),
    navigationBarTheme: NavigationBarThemeData(
      backgroundColor: Colors.white,
      indicatorColor: Brand.green100,
      labelTextStyle: WidgetStateProperty.all(
        const TextStyle(fontSize: 12, fontWeight: FontWeight.w600),
      ),
    ),
    dividerTheme: const DividerThemeData(color: Brand.line, space: 1),
  );
}
