import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'app/router.dart';
import 'core/theme/theme_presets.dart';

void main() {
  runApp(
    const ProviderScope(
      child: MyApp(),
    ),
  );
}

class MyApp extends ConsumerWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final activeTheme = ref.watch(themePresetProvider);

    return MaterialApp.router(
      title: 'Form Builder',
      theme: ThemeData(
        useMaterial3: true,
        brightness: activeTheme.brightness,
        colorScheme: ColorScheme.fromSeed(
          seedColor: activeTheme.seedColor,
          brightness: activeTheme.brightness,
        ),
      ),
      routerConfig: appRouter,
      debugShowCheckedModeBanner: false,
    );
  }
}
