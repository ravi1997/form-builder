import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:frontend/features/form_builder/providers/form_builder_provider.dart';

void main() {
  test('Form Play Mode math calculations automatic integration', () {
    final container = ProviderContainer(
      overrides: [
        formBuilderProvider.overrideWith(() => FormulaTestFormBuilderNotifier()),
      ],
    );

    // Initial play state is empty
    var playState = container.read(formPlayProvider);
    expect(playState.answers['q_calc'], isNull);

    // Set value for q1
    container.read(formPlayProvider.notifier).setAnswer('q1', 5.0);
    playState = container.read(formPlayProvider);
    expect(playState.answers['q1'], equals(5.0));
    expect(playState.answers['q_calc'], equals(5.0)); // q2 defaults to 0.0

    // Set value for q2
    container.read(formPlayProvider.notifier).setAnswer('q2', 2.0);
    playState = container.read(formPlayProvider);
    expect(playState.answers['q2'], equals(2.0));
    // formula is: q1 + q2 * 10 => 5.0 + 2.0 * 10.0 = 25.0
    expect(playState.answers['q_calc'], equals(25.0));
  });
  test('Form Play Mode conditional calculations automatic integration', () {
    final container = ProviderContainer(
      overrides: [
        formBuilderProvider.overrideWith(() => FormulaConditionalTestFormBuilderNotifier()),
      ],
    );

    // Initial play state is empty
    var playState = container.read(formPlayProvider);
    expect(playState.answers['q_calc'], isNull);

    // Set value for q1 (<= 10) and q2
    container.read(formPlayProvider.notifier).setAnswer('q1', 8.0);
    container.read(formPlayProvider.notifier).setAnswer('q2', 5.0);
    playState = container.read(formPlayProvider);
    // Since q1 <= 10, q_calc should evaluate to q2 => 5.0
    expect(playState.answers['q_calc'], equals(5.0));

    // Set value for q1 (> 10)
    container.read(formPlayProvider.notifier).setAnswer('q1', 12.0);
    playState = container.read(formPlayProvider);
    // Since q1 > 10, q_calc should evaluate to q2 * 2 => 5.0 * 2 = 10.0
    expect(playState.answers['q_calc'], equals(10.0));
  });
}

class FormulaTestFormBuilderNotifier extends FormBuilderNotifier {
  @override
  FormBuilderState build() {
    return FormBuilderState(
      formId: 'test_form',
      name: 'Formula Test Form',
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
                  id: 'q1',
                  type: 'number_input',
                  label: 'Value 1',
                  properties: const {},
                ),
                FormQuestion(
                  id: 'q2',
                  type: 'number_input',
                  label: 'Value 2',
                  properties: const {},
                ),
                FormQuestion(
                  id: 'q_calc',
                  type: 'calculation',
                  label: 'Calculation Result',
                  properties: const {},
                  calculations: const [
                    {'formula': 'q1 + q2 * 10'}
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

class FormulaConditionalTestFormBuilderNotifier extends FormBuilderNotifier {
  @override
  FormBuilderState build() {
    return FormBuilderState(
      formId: 'test_conditional_form',
      name: 'Formula Conditional Test Form',
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
                  id: 'q1',
                  type: 'number_input',
                  label: 'Value 1',
                  properties: const {},
                ),
                FormQuestion(
                  id: 'q2',
                  type: 'number_input',
                  label: 'Value 2',
                  properties: const {},
                ),
                FormQuestion(
                  id: 'q_calc',
                  type: 'calculation',
                  label: 'Calculation Result',
                  properties: const {},
                  calculations: const [
                    {'formula': 'IF(q1 > 10, q2 * 2, q2)'}
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
