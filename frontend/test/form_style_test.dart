import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:frontend/features/form_builder/providers/form_builder_provider.dart';
import 'package:frontend/features/form_builder/presentation/widgets/properties_panel.dart';

void main() {
  testWidgets('FormStyle updates and preset selection widget test', (WidgetTester tester) async {
    await tester.pumpWidget(
      const ProviderScope(
        child: MaterialApp(
          home: Scaffold(
            body: PropertiesPanel(),
          ),
        ),
      ),
    );

    // Initial render when no element is selected should show Global Form Properties
    expect(find.text('Global Form Properties'), findsOneWidget);

    // Switch to Style tab
    await tester.tap(find.text('Style'));
    await tester.pumpAndSettle();

    // Verify Presets are displayed
    expect(find.text('Sleek Dark'), findsOneWidget);
    expect(find.text('Glassmorphism'), findsOneWidget);

    // Click on Sleek Dark card
    await tester.tap(find.text('Sleek Dark'));
    await tester.pumpAndSettle();

    // Dialog should show up
    expect(find.text('Apply Preset?'), findsOneWidget);

    // Confirm apply
    await tester.tap(find.text('Apply'));
    await tester.pumpAndSettle();

    // Tap Advanced Mode in SegmentedButton
    await tester.tap(find.text('Advanced'));
    await tester.pumpAndSettle();

    // Check custom CSS warning is present
    expect(find.textContaining('Warning: Custom CSS rule changes'), findsOneWidget);
  });
}
