import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:frontend/features/form_builder/providers/form_builder_provider.dart';
import 'package:frontend/features/form_builder/providers/logic_validator.dart';
import 'package:frontend/features/form_builder/presentation/widgets/properties_panel.dart';
import 'package:frontend/features/form_builder/presentation/widgets/logic_graph_editor.dart';
import 'package:frontend/shared/json_ui_engine/models/visibility_rule.dart';

void main() {
  testWidgets('Advanced Logic and Validation Graph & Warnings Test', (WidgetTester tester) async {
    await tester.binding.setSurfaceSize(const Size(1400, 1000));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    final notifier = TestAdvancedLogicNotifier();
    final container = ProviderContainer(
      overrides: [
        formBuilderProvider.overrideWith(() => notifier),
      ],
    );

    await tester.pumpWidget(
      UncontrolledProviderScope(
        container: container,
        child: MaterialApp(
          home: Scaffold(
            body: Row(
              children: [
                Expanded(
                  child: Container(), // Empty canvas replacement for simplicity
                ),
                const SizedBox(width: 320, child: PropertiesPanel()),
              ],
            ),
          ),
        ),
      ),
    );

    await tester.pumpAndSettle();

    // 1. Initially, select Section 1 to open its editor in properties panel
    ref(container).selectElement('sec_1');
    await tester.pumpAndSettle();

    // Tap the 'Logic' tab to open logic panel
    final logicTab = find.text('Logic').first;
    await tester.ensureVisible(logicTab);
    await tester.tap(logicTab);
    await tester.pumpAndSettle();

    // Verify List-based editors are present
    expect(find.byKey(const ValueKey('logic-visibility-input')), findsOneWidget);
    expect(find.byKey(const ValueKey('logic-skipto-input')), findsOneWidget);

    // 2. Test input syncing: Change visibility rule in List view
    await tester.enterText(find.byKey(const ValueKey('logic-visibility-input')), 'show when q_dropdown == yes');
    await tester.pumpAndSettle();

    var state = container.read(formBuilderProvider);
    expect(state.sections[0].visibilityRule, equals('show when q_dropdown == yes'));

    // 3. Switch to Graph view
    await tester.tap(find.text('Graph'));
    await tester.pumpAndSettle();

    // Verify visual logic graph preview card/placeholder is shown
    expect(find.text('Visual Logic Graph'), findsOneWidget);

    // 4. Open visual logic canvas modal
    // Scroll the properties panel SingleChildScrollView to ensure the button is fully inside the viewport
    final scrollable = find.byType(Scrollable).first;
    await tester.drag(scrollable, const Offset(0, -300));
    await tester.pumpAndSettle();

    final openCanvasButton = find.byKey(const ValueKey('btn-open-logic-canvas'));
    await tester.ensureVisible(openCanvasButton);
    await tester.tap(openCanvasButton);
    await tester.pumpAndSettle();

    // Verify visual logic canvas shows node widgets
    expect(find.text('Visual Logic Canvas'), findsOneWidget);
    expect(find.byKey(const ValueKey('node_sec_1')), findsOneWidget);

    // Inspect Section 1 by tapping on its node in the canvas
    await tester.tap(find.byKey(const ValueKey('node_sec_1')));
    await tester.pumpAndSettle();

    // In the inspector, edit visibility rule on the visual canvas
    await tester.enterText(find.byKey(const ValueKey('canvas-visibility-input')), 'show when q_text == test');
    await tester.pumpAndSettle();

    state = container.read(formBuilderProvider);
    expect(state.sections[0].visibilityRule, equals('show when q_text == test'));

    // Close Visual Logic Canvas
    await tester.tap(find.byKey(const ValueKey('btn-close-canvas')));
    await tester.pumpAndSettle();

    // 5. Test Contradiction Warning: Set section visibility rule to depend on its own field q_text
    // which belongs to sec_1.
    // Self-contradiction: Section "Section 1" visibility depends on its own field "q_text"
    ref(container).updateSection('sec_1', visibilityRule: 'show when q_text == something');
    await tester.pumpAndSettle();

    state = container.read(formBuilderProvider);
    expect(state.logicIssues.any((issue) => issue.id.startsWith('self_dep_')), isTrue);
    expect(find.textContaining('Self-contradiction: Section'), findsOneWidget);

    // 6. Test Cycle Detection Warning: Add a direct logic dependency loop
    // Field q_text depends on Field q_dropdown, and Field q_dropdown depends on Field q_text.
    ref(container).updateQuestion('q_text', visibilityRules: const VisibilityRules(
      operator: LogicalOperator.and,
      conditions: [
        AnswerCondition(fieldId: 'q_dropdown', operator: AnswerOperator.equals, value: 'yes')
      ],
    ));
    ref(container).updateQuestion('q_dropdown', visibilityRules: const VisibilityRules(
      operator: LogicalOperator.and,
      conditions: [
        AnswerCondition(fieldId: 'q_text', operator: AnswerOperator.equals, value: 'hello')
      ],
    ));
    await tester.pumpAndSettle();

    state = container.read(formBuilderProvider);
    expect(state.logicIssues.any((issue) => issue.id.startsWith('cycle_')), isTrue);
  });

  testWidgets('Properties Panel Input Overwrite and Style Hex Validation Test', (WidgetTester tester) async {
    final notifier = TestAdvancedLogicNotifier();
    final container = ProviderContainer(
      overrides: [
        formBuilderProvider.overrideWith(() => notifier),
      ],
    );

    await tester.pumpWidget(
      UncontrolledProviderScope(
        container: container,
        child: MaterialApp(
          home: Scaffold(
            body: const PropertiesPanel(),
          ),
        ),
      ),
    );

    await tester.pumpAndSettle();

    // 1. Initially, select Question 'q_text' to show its details in properties panel
    ref(container).selectElement('q_text');
    await tester.pumpAndSettle();

    // Verify slug input is present and overwrite works cleanly
    final slugFinder = find.byKey(const ValueKey('sidebar-slug-input'));
    expect(slugFinder, findsOneWidget);
    await tester.enterText(slugFinder, 'new_slug');
    await tester.pumpAndSettle();

    var state = container.read(formBuilderProvider);
    expect(state.sections[0].subSections[0].questions[0].properties['slug'], equals('new_slug'));

    // 2. Select null (goes to global form details/style properties)
    ref(container).selectElement(null);
    await tester.pumpAndSettle();

    // Tap Style tab
    await tester.tap(find.text('Style'));
    await tester.pumpAndSettle();

    // Tap 'Advanced' segment to show Theme Tokens
    await tester.tap(find.text('Advanced'));
    await tester.pumpAndSettle();

    // Verify hex fields exist and display validation
    final primaryColorInput = find.byKey(const ValueKey('sidebar-primary-color-input'));
    expect(primaryColorInput, findsOneWidget);

    // Enter invalid color code
    await tester.enterText(primaryColorInput, 'invalid');
    await tester.pumpAndSettle();

    // Verify error text is displayed
    expect(find.text('Invalid hex color (e.g. #3949AB)'), findsOneWidget);

    // Enter valid color code
    await tester.enterText(primaryColorInput, '#3949AB');
    await tester.pumpAndSettle();

    // Error text should be gone
    expect(find.text('Invalid hex color (e.g. #3949AB)'), findsNothing);

    // Verify style is updated in provider state
    state = container.read(formBuilderProvider);
    expect(state.style.primaryColor, equals('#3949AB'));
  });
}

// Helper function to read/write provider state inside tests
FormBuilderNotifier ref(ProviderContainer container) {
  return container.read(formBuilderProvider.notifier);
}

class TestAdvancedLogicNotifier extends FormBuilderNotifier {
  @override
  FormBuilderState build() {
    return FormBuilderState(
      formId: 'advanced_test_form',
      name: 'Advanced logic Form',
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
                  label: 'Text Question',
                  required: false,
                  properties: const {},
                ),
                FormQuestion(
                  id: 'q_dropdown',
                  type: 'dropdown',
                  label: 'Dropdown Question',
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
