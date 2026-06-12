import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:frontend/features/form_builder/providers/form_builder_provider.dart';
import 'package:frontend/features/form_builder/presentation/widgets/canvas.dart';
import 'package:frontend/features/form_builder/presentation/widgets/properties_panel.dart';

void main() {
  testWidgets('Inline Popover and Help Tooltip System Tests', (WidgetTester tester) async {
    // Set surface size to avoid overflow and offscreen tapping errors
    await tester.binding.setSurfaceSize(const Size(1280, 1024));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    final container = ProviderContainer(
      overrides: [
        formBuilderProvider.overrideWith(() => TestFormBuilderNotifier()),
      ],
    );

    // Setup the widget tree containing both BuilderCanvas and PropertiesPanel
    await tester.pumpWidget(
      UncontrolledProviderScope(
        container: container,
        child: MaterialApp(
          home: Scaffold(
            body: Row(
              children: [
                Expanded(
                  child: BuilderCanvas(
                    activeSubSectionId: 'subsec_1',
                    onSubSectionActivated: (id) {},
                  ),
                ),
                const SizedBox(width: 320, child: PropertiesPanel()),
              ],
            ),
          ),
        ),
      ),
    );

    await tester.pumpAndSettle();

    // 1. Initial State: No popover open
    expect(find.byKey(const ValueKey('popover-label-input')), findsNothing);

    // Select the question by tapping on it
    await tester.tap(find.text('Text Input Question'));
    await tester.pumpAndSettle();

    // 2. Popover opens anchored above the selected field
    expect(find.byKey(const ValueKey('popover-label-input')), findsOneWidget);
    expect(find.byKey(const ValueKey('popover-required-switch')), findsOneWidget);

    // 3. Edit label inline via popover
    await tester.enterText(find.byKey(const ValueKey('popover-label-input')), 'Updated Inline Label');
    await tester.pumpAndSettle();

    // Verify state synchronizes with properties provider
    var state = container.read(formBuilderProvider);
    expect(state.sections[0].subSections[0].questions[0].label, equals('Updated Inline Label'));

    // 4. Toggle required field inline via popover
    expect(state.sections[0].subSections[0].questions[0].required, isFalse);
    await tester.tap(find.byKey(const ValueKey('popover-required-switch')));
    await tester.pumpAndSettle();

    state = container.read(formBuilderProvider);
    expect(state.sections[0].subSections[0].questions[0].required, isTrue);

    // 5. Sidebar sync verification: check if technical keys (Slug, Elevation, FLE/PII) exist in Sidebar
    expect(find.byKey(const ValueKey('sidebar-slug-input')), findsOneWidget);
    expect(find.byKey(const ValueKey('sidebar-elevation-input')), findsOneWidget);
    expect(find.byKey(const ValueKey('sidebar-fle-pii-switch')), findsOneWidget);

    // Verify info icon tooltips exist for all technical labels
    expect(find.byKey(const ValueKey('tooltip-slug')), findsOneWidget);
    expect(find.byKey(const ValueKey('tooltip-elevation')), findsOneWidget);
    expect(find.byKey(const ValueKey('tooltip-fle-pii')), findsOneWidget);

    // 6. Dismiss inline popover by clicking the close button
    await tester.tap(find.byKey(const ValueKey('popover-close-button')));
    await tester.pumpAndSettle();

    // Verify popover is gone
    expect(find.byKey(const ValueKey('popover-label-input')), findsNothing);
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
      sections: [
        FormSection(
          id: 'sec_1',
          title: 'Section 1',
          subSections: [
            FormSubSection(
              id: 'subsec_1',
              title: 'Sub-section 1',
              questions: [
                FormQuestion(
                  id: 'q_text',
                  type: 'text_input',
                  label: 'Text Input Question',
                  required: false,
                  properties: const {},
                ),
              ],
            ),
          ],
        ),
      ],
    );
  }
}
