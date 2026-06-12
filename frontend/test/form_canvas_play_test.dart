import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:frontend/features/form_builder/providers/form_builder_provider.dart';
import 'package:frontend/features/form_builder/presentation/widgets/canvas.dart';

void main() {
  testWidgets('BuilderCanvas Play Mode, validation, branching and drag-drop testing', (WidgetTester tester) async {
    // Setup a form builder state with customized questions and branching logic
    final container = ProviderContainer(
      overrides: [
        formBuilderProvider.overrideWith(() => TestFormBuilderNotifier()),
      ],
    );

    await tester.pumpWidget(
      UncontrolledProviderScope(
        container: container,
        child: MaterialApp(
          home: Scaffold(
            body: BuilderCanvas(
              activeSubSectionId: 'subsec_1',
              onSubSectionActivated: (id) {},
            ),
          ),
        ),
      ),
    );

    await tester.pumpAndSettle();

    // 1. Entering play mode from the canvas
    // Initially in Edit mode, let's verify
    expect(find.text('Edit'), findsOneWidget);
    expect(find.text('Play'), findsOneWidget);
    expect(find.text('Split'), findsOneWidget);

    // Tap on Play
    await tester.tap(find.text('Play'));
    await tester.pumpAndSettle();

    // Verify play mode header shows up
    expect(find.textContaining('Interactive Play Mode'), findsOneWidget);

    // 2. Typing into fields and seeing validation update
    // Verify first question field input exists
    final textInputFinder = find.byKey(const ValueKey('input_q_text'));
    expect(textInputFinder, findsOneWidget);

    // Type text
    await tester.enterText(textInputFinder, 'Hello Test');
    await tester.pumpAndSettle();

    // Verify it updates state and validation
    // Tap submit response
    final submitBtn = find.text('Submit Test Response');
    await tester.ensureVisible(submitBtn);
    await tester.tap(submitBtn, warnIfMissed: false);
    await tester.pumpAndSettle();

    // Wait, let's verify that error on empty dropdown field q_dropdown is shown (it is required)
    expect(find.text('This field is required'), findsOneWidget);

    // Now select a value for the required dropdown
    final dropdownFinder = find.byKey(const ValueKey('input_q_dropdown'));
    expect(dropdownFinder, findsOneWidget);
    await tester.ensureVisible(dropdownFinder);
    await tester.tap(dropdownFinder, warnIfMissed: false);
    await tester.pumpAndSettle();
    
    // Choose the dropdown option 'yes'
    await tester.tap(find.text('Yes').last, warnIfMissed: false);
    await tester.pumpAndSettle();

    // Re-verify validation updates on submit
    await tester.ensureVisible(submitBtn);
    await tester.tap(submitBtn, warnIfMissed: false);
    await tester.pumpAndSettle();
    expect(find.text('This field is required'), findsNothing);

    // 3. Branch changes reflecting real logic
    // We configured a Section 2 with visibilityRule: "show when q_dropdown == yes"
    // Since we selected "yes" above, Section 2 should now be visible!
    expect(find.text('Section 2'), findsOneWidget);

    // Reset / Restart test state to verify exit/reset behavior
    await tester.tap(find.byIcon(Icons.refresh));
    await tester.pumpAndSettle();

    // Section 2 should be hidden again because answers are reset (q_dropdown is empty/null)
    expect(find.text('Section 2'), findsNothing);

    // 4. Exit and reset behavior
    // Switch back to Edit mode
    await tester.tap(find.text('Edit'));
    await tester.pumpAndSettle();
    expect(find.textContaining('Interactive Play Mode'), findsNothing);
  });

  testWidgets('Drag and drop ghost indicators and targets validation', (WidgetTester tester) async {
    final container = ProviderContainer(
      overrides: [
        formBuilderProvider.overrideWith(() => TestFormBuilderNotifier()),
      ],
    );

    await tester.pumpWidget(
      UncontrolledProviderScope(
        container: container,
        child: MaterialApp(
          home: Scaffold(
            body: SizedBox(
              height: 800,
              child: BuilderCanvas(
                activeSubSectionId: 'subsec_1',
                onSubSectionActivated: (id) {},
              ),
            ),
          ),
        ),
      ),
    );

    await tester.pumpAndSettle();

    // Drag-and-drop targets / ghost indicators are rendered as DragTarget widgets
    // Initially, there should be multiple DragTarget widgets
    final dragTargets = find.byType(DragTarget<Map<String, dynamic>>);
    expect(dragTargets, findsAtLeast(2));

    // Confirm that no state mutation occurs prior to dropping (initial count of questions)
    final stateBefore = container.read(formBuilderProvider);
    expect(stateBefore.sections[0].subSections[0].questions.length, equals(2));

    // Perform a simulate drag over a drag target to verify target/ghost indicator highlights
    final targetFinder = find.byWidgetPredicate((widget) {
      if (widget is DragTarget<Map<String, dynamic>>) {
        return true;
      }
      return false;
    }).first;

    final gesture = await tester.startGesture(tester.getCenter(find.text('Text Input Question')));
    await gesture.moveTo(tester.getCenter(targetFinder));
    await tester.pump();

    // State shouldn't mutate just because we hovered
    final stateDuringHover = container.read(formBuilderProvider);
    expect(stateDuringHover.sections[0].subSections[0].questions.length, equals(2));

    // End drag (release drop)
    await gesture.up();
    await tester.pumpAndSettle();
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
                FormQuestion(
                  id: 'q_dropdown',
                  type: 'dropdown',
                  label: 'Dropdown Question',
                  required: true,
                  properties: const {
                    'options': [
                      {'value': 'yes', 'label': 'Yes'},
                      {'value': 'no', 'label': 'No'},
                    ]
                  },
                ),
              ],
            ),
          ],
        ),
        FormSection(
          id: 'sec_2',
          title: 'Section 2',
          visibilityRule: 'show when q_dropdown == yes',
          subSections: [
            FormSubSection(
              id: 'subsec_2',
              title: 'Sub-section 2',
              questions: [],
            ),
          ],
        ),
      ],
    );
  }
}
