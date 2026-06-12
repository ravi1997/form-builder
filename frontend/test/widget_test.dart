import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:frontend/main.dart';

void main() {
  testWidgets('Auth screens rendering and navigation smoke test', (WidgetTester tester) async {
    // Set surface size to avoid overflow errors
    await tester.binding.setSurfaceSize(const Size(1280, 1024));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    // Build our app and trigger a frame.
    await tester.pumpWidget(const ProviderScope(child: MyApp()));
    await tester.pump(const Duration(milliseconds: 500));
    await tester.pumpAndSettle();

    // Verify that the login page is shown initially.
    expect(find.text('Welcome Back'), findsOneWidget);
    expect(find.text('LOGIN'), findsWidgets);
  });
}
