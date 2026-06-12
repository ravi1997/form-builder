import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:frontend/features/form_builder/providers/form_builder_provider.dart';
import 'package:frontend/features/form_builder/presentation/widgets/properties_panel.dart';

void main() {
  testWidgets('Form Analytics Tab and Fields State Sync Test', (WidgetTester tester) async {
    // Set surface size to avoid overflow and offscreen tapping errors
    await tester.binding.setSurfaceSize(const Size(1280, 1024));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    final container = ProviderContainer(
      overrides: [
        formBuilderProvider.overrideWith(() => TestFormBuilderNotifier()),
      ],
    );

    // Render the PropertiesPanel (since selectedElementId is null, it shows Global Form Properties)
    await tester.pumpWidget(
      UncontrolledProviderScope(
        container: container,
        child: const MaterialApp(
          home: Scaffold(
            body: SizedBox(
              width: 400,
              child: PropertiesPanel(),
            ),
          ),
        ),
      ),
    );

    await tester.pumpAndSettle();

    // Verify TabBar has 'Analytics' tab
    expect(find.text('General'), findsOneWidget);
    expect(find.text('Style'), findsOneWidget);
    expect(find.text('Notifications'), findsOneWidget);
    expect(find.text('Analytics'), findsOneWidget);

    // Switch to Analytics tab
    await tester.tap(find.text('Analytics'));
    await tester.pumpAndSettle();

    // 1. Initial State Checks
    // Analytics is enabled by default
    expect(container.read(formBuilderProvider).analytics.enabled, isTrue);
    expect(find.byKey(const ValueKey('analytics-enabled-switch')), findsOneWidget);
    expect(find.byKey(const ValueKey('analytics-start-event-dropdown')), findsOneWidget);
    expect(find.byKey(const ValueKey('analytics-end-event-dropdown')), findsOneWidget);

    // 2. Disable Analytics Collection
    final enabledSwitch = find.byKey(const ValueKey('analytics-enabled-switch'));
    await tester.ensureVisible(enabledSwitch);
    await tester.tap(enabledSwitch);
    await tester.pumpAndSettle();

    expect(container.read(formBuilderProvider).analytics.enabled, isFalse);
    // Dropdowns should hide when disabled
    expect(find.byKey(const ValueKey('analytics-start-event-dropdown')), findsNothing);
    expect(find.byKey(const ValueKey('analytics-end-event-dropdown')), findsNothing);

    // Re-enable
    await tester.tap(enabledSwitch);
    await tester.pumpAndSettle();
    expect(container.read(formBuilderProvider).analytics.enabled, isTrue);

    // 3. Select Start Event dropdown option
    final startDropdown = find.byKey(const ValueKey('analytics-start-event-dropdown'));
    await tester.ensureVisible(startDropdown);
    await tester.tap(startDropdown);
    await tester.pumpAndSettle();
    // Select Form Loaded
    await tester.tap(find.text('Form Loaded (Initial Page Open)').last);
    await tester.pumpAndSettle();
    expect(container.read(formBuilderProvider).analytics.startEventType, equals('form_load'));

    // 4. Select End Event dropdown option
    final endDropdown = find.byKey(const ValueKey('analytics-end-event-dropdown'));
    await tester.ensureVisible(endDropdown);
    await tester.tap(endDropdown);
    await tester.pumpAndSettle();
    // Select Submission Attempt
    await tester.tap(find.text('Submission Attempt (Click Submit)').last);
    await tester.pumpAndSettle();
    expect(container.read(formBuilderProvider).analytics.endEventType, equals('submit_attempt'));

    // 5. Test Toggles for Drop-off, Timing and UTM capture
    final dropOffSwitch = find.byKey(const ValueKey('analytics-drop-off-switch'));
    final timingSwitch = find.byKey(const ValueKey('analytics-timing-switch'));
    final utmSwitch = find.byKey(const ValueKey('analytics-utm-capture-switch'));

    expect(container.read(formBuilderProvider).analytics.dropOffEnabled, isTrue);
    expect(container.read(formBuilderProvider).analytics.timingEnabled, isTrue);
    expect(container.read(formBuilderProvider).analytics.utmCaptureEnabled, isTrue);

    await tester.ensureVisible(dropOffSwitch);
    await tester.tap(dropOffSwitch);
    await tester.ensureVisible(timingSwitch);
    await tester.tap(timingSwitch);
    await tester.ensureVisible(utmSwitch);
    await tester.tap(utmSwitch);
    await tester.pumpAndSettle();

    expect(container.read(formBuilderProvider).analytics.dropOffEnabled, isFalse);
    expect(container.read(formBuilderProvider).analytics.timingEnabled, isFalse);
    expect(container.read(formBuilderProvider).analytics.utmCaptureEnabled, isFalse);
  });
}

class TestFormBuilderNotifier extends FormBuilderNotifier {
  @override
  FormBuilderState build() {
    return FormBuilderState(
      formId: 'test_form',
      name: 'Test Form Name',
      style: FormStyle(),
      canvasMode: FormCanvasMode.edit,
      analytics: FormAnalyticsSettings(),
      sections: [],
    );
  }
}
