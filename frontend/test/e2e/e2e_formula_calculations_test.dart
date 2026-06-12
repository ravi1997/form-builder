import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:frontend/core/formula/formula_parser.dart';
import 'package:frontend/features/form_builder/providers/form_builder_provider.dart';

void main() {
  group('FormulaParser Unit Tests (Tiers 1-2)', () {
    test('T11: Simple mathematical operators and precedence', () {
      // 3 + (5 * 2) - 3 = 10
      final parser = FormulaParser('3 + 5 * 2 - 3');
      final ast = parser.parse();
      expect(ast.evaluate({}), equals(10.0));
    });

    test('T11: Modulo calculations', () {
      final parser = FormulaParser('10 % 3');
      final ast = parser.parse();
      expect(ast.evaluate({}), equals(1.0));
    });

    test('T17: Deeply nested parentheses', () {
      final parser = FormulaParser('((((5 + 5) * (2 + 2))))');
      final ast = parser.parse();
      expect(ast.evaluate({}), equals(40.0));
    });

    test('T16: Division by zero returns 0.0 fallback', () {
      final parser = FormulaParser('10 / 0');
      final ast = parser.parse();
      expect(ast.evaluate({}), equals(0.0));
    });

    test('T16: Modulo by zero returns 0.0 fallback', () {
      final parser = FormulaParser('10 % 0');
      final ast = parser.parse();
      expect(ast.evaluate({}), equals(0.0));
    });

    test('T20: Missing/null variables default to 0.0', () {
      final parser = FormulaParser('q1 + q2 * q3');
      final ast = parser.parse();
      // q1, q2, q3 missing => 0.0 + 0.0 * 0.0 = 0.0
      expect(ast.evaluate({}), equals(0.0));
      // q1=5.0, others missing => 5.0 + 0.0 = 5.0
      expect(ast.evaluate({'q1': 5.0}), equals(5.0));
    });
  });

  group('Cascading & Integration Formula Tests (Tiers 1-2)', () {
    test('T12: Cascading recalculation works correctly', () {
      final container = ProviderContainer(
        overrides: [
          formBuilderProvider.overrideWith(() => CascadingTestFormNotifier()),
        ],
      );

      // Initial state
      var playState = container.read(formPlayProvider);
      expect(playState.answers['q_final'], isNull);

      // Set input q_start = 10
      container.read(formPlayProvider.notifier).setAnswer('q_start', 10.0);
      playState = container.read(formPlayProvider);

      // Cascading evaluation should propagate:
      // q_start = 10.0
      // q_mid1 = q_start * 2 = 20.0
      // q_mid2 = q_mid1 + 5 = 25.0
      // q_final = q_mid2 / 2 = 12.5
      expect(playState.answers['q_start'], equals(10.0));
      expect(playState.answers['q_mid1'], equals(20.0));
      expect(playState.answers['q_mid2'], equals(25.0));
      expect(playState.answers['q_final'], equals(12.5));
    });

    test('T18: Circular reference detection breaks after 5 iterations', () {
      final container = ProviderContainer(
        overrides: [
          formBuilderProvider.overrideWith(() => CircularTestFormNotifier()),
        ],
      );

      // Seed start value
      container.read(formPlayProvider.notifier).setAnswer('q_a', 2.0);
      final playState = container.read(formPlayProvider);

      // If it loops infinitely, the code would hang/stack overflow.
      // Since it limits to 5 iterations:
      // It should terminate and not crash.
      expect(playState.answers['q_a'], isNotNull);
      expect(playState.answers['q_b'], isNotNull);
    });

    test('T19: Coercion of string inputs to doubles before evaluation', () {
      final container = ProviderContainer(
        overrides: [
          formBuilderProvider.overrideWith(() => SimpleMathFormNotifier()),
        ],
      );

      // Set string inputs
      container.read(formPlayProvider.notifier).setAnswer('q_x', '15.5');
      container.read(formPlayProvider.notifier).setAnswer('q_y', '4.5');
      final playState = container.read(formPlayProvider);

      // formula is q_x + q_y => 15.5 + 4.5 = 20.0
      expect(playState.answers['q_sum'], equals(20.0));
    });
  });
}

class CascadingTestFormNotifier extends FormBuilderNotifier {
  @override
  FormBuilderState build() {
    return FormBuilderState(
      formId: 'cascading_form',
      name: 'Cascading Test Form',
      style: FormStyle(),
      canvasMode: FormCanvasMode.play,
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
                  id: 'q_start',
                  type: 'number_input',
                  label: 'Start',
                  properties: const {},
                ),
                FormQuestion(
                  id: 'q_mid1',
                  type: 'calculation',
                  label: 'Mid 1',
                  properties: const {},
                  calculations: const [
                    {'formula': 'q_start * 2'}
                  ],
                ),
                FormQuestion(
                  id: 'q_mid2',
                  type: 'calculation',
                  label: 'Mid 2',
                  properties: const {},
                  calculations: const [
                    {'formula': 'q_mid1 + 5'}
                  ],
                ),
                FormQuestion(
                  id: 'q_final',
                  type: 'calculation',
                  label: 'Final',
                  properties: const {},
                  calculations: const [
                    {'formula': 'q_mid2 / 2'}
                  ],
                ),
              ],
            ),
          ],
        ),
      ],
    );
  }
}

class CircularTestFormNotifier extends FormBuilderNotifier {
  @override
  FormBuilderState build() {
    return FormBuilderState(
      formId: 'circular_form',
      name: 'Circular Test Form',
      style: FormStyle(),
      canvasMode: FormCanvasMode.play,
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
                  id: 'q_a',
                  type: 'calculation',
                  label: 'A',
                  properties: const {},
                  calculations: const [
                    {'formula': 'q_b + 1'}
                  ],
                ),
                FormQuestion(
                  id: 'q_b',
                  type: 'calculation',
                  label: 'B',
                  properties: const {},
                  calculations: const [
                    {'formula': 'q_a + 1'}
                  ],
                ),
              ],
            ),
          ],
        ),
      ],
    );
  }
}

class SimpleMathFormNotifier extends FormBuilderNotifier {
  @override
  FormBuilderState build() {
    return FormBuilderState(
      formId: 'simple_math_form',
      name: 'Simple Math Form',
      style: FormStyle(),
      canvasMode: FormCanvasMode.play,
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
                  id: 'q_x',
                  type: 'text_input',
                  label: 'X',
                  properties: const {},
                ),
                FormQuestion(
                  id: 'q_y',
                  type: 'text_input',
                  label: 'Y',
                  properties: const {},
                ),
                FormQuestion(
                  id: 'q_sum',
                  type: 'calculation',
                  label: 'Sum',
                  properties: const {},
                  calculations: const [
                    {'formula': 'q_x + q_y'}
                  ],
                ),
              ],
            ),
          ],
        ),
      ],
    );
  }
}
