import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../shared/json_ui_engine/models/validation_rule.dart';
import '../../../shared/json_ui_engine/models/visibility_rule.dart';

class FormQuestion {
  final String id;
  final String type;
  final String label;
  final String description;
  final bool required;
  final Map<String, dynamic> properties;
  final VisibilityRules visibilityRules;
  final List<ValidationRule> validationRules;
  final List<dynamic> calculations;
  final dynamic fetchAction;
  final dynamic skipLogic;

  FormQuestion({
    required this.id,
    required this.type,
    required this.label,
    this.description = '',
    this.required = false,
    required this.properties,
    this.visibilityRules = const VisibilityRules(operator: LogicalOperator.and, conditions: []),
    this.validationRules = const [],
    this.calculations = const [],
    this.fetchAction,
    this.skipLogic,
  });

  FormQuestion copyWith({
    String? id,
    String? type,
    String? label,
    String? description,
    bool? required,
    Map<String, dynamic>? properties,
    VisibilityRules? visibilityRules,
    List<ValidationRule>? validationRules,
    List<dynamic>? calculations,
    dynamic fetchAction,
    dynamic skipLogic,
  }) {
    return FormQuestion(
      id: id ?? this.id,
      type: type ?? this.type,
      label: label ?? this.label,
      description: description ?? this.description,
      required: required ?? this.required,
      properties: properties ?? Map<String, dynamic>.from(this.properties),
      visibilityRules: visibilityRules ?? this.visibilityRules,
      validationRules: validationRules ?? this.validationRules,
      calculations: calculations ?? this.calculations,
      fetchAction: fetchAction ?? this.fetchAction,
      skipLogic: skipLogic ?? this.skipLogic,
    );
  }
}

class FormSubSection {
  final String id;
  final String title;
  final bool repeatable;
  final List<FormQuestion> questions;

  FormSubSection({
    required this.id,
    required this.title,
    this.repeatable = false,
    required this.questions,
  });

  FormSubSection copyWith({
    String? id,
    String? title,
    bool? repeatable,
    List<FormQuestion>? questions,
  }) {
    return FormSubSection(
      id: id ?? this.id,
      title: title ?? this.title,
      repeatable: repeatable ?? this.repeatable,
      questions: questions ?? List<FormQuestion>.from(this.questions),
    );
  }
}

class FormSection {
  final String id;
  final String title;
  final String description;
  final bool repeatable;
  final List<FormSubSection> subSections;

  FormSection({
    required this.id,
    required this.title,
    this.description = '',
    this.repeatable = false,
    required this.subSections,
  });

  FormSection copyWith({
    String? id,
    String? title,
    String? description,
    bool? repeatable,
    List<FormSubSection>? subSections,
  }) {
    return FormSection(
      id: id ?? this.id,
      title: title ?? this.title,
      description: description ?? this.description,
      repeatable: repeatable ?? this.repeatable,
      subSections: subSections ?? List<FormSubSection>.from(this.subSections),
    );
  }
}

class FormBuilderState {
  final String formId;
  final String name;
  final String description;
  final List<FormSection> sections;
  final String? selectedElementId; // Currently selected Section/SubSection/Question ID

  FormBuilderState({
    required this.formId,
    required this.name,
    this.description = '',
    required this.sections,
    this.selectedElementId,
  });

  FormBuilderState copyWith({
    String? formId,
    String? name,
    String? description,
    List<FormSection>? sections,
    String? selectedElementId,
  }) {
    return FormBuilderState(
      formId: formId ?? this.formId,
      name: name ?? this.name,
      description: description ?? this.description,
      sections: sections ?? List<FormSection>.from(this.sections),
      selectedElementId: selectedElementId ?? this.selectedElementId,
    );
  }
}

class FormBuilderNotifier extends Notifier<FormBuilderState> {
  @override
  FormBuilderState build() {
    return FormBuilderState(
      formId: 'default',
      name: 'My Custom Form',
      sections: [
        FormSection(
          id: 'sec_1',
          title: 'Section 1',
          subSections: [
            FormSubSection(
              id: 'subsec_1',
              title: 'Sub-section 1',
              questions: [],
            ),
          ],
        ),
      ],
    );
  }

  void selectElement(String? id) {
    state = state.copyWith(selectedElementId: id);
  }

  void addSection() {
    final newSec = FormSection(
      id: 'sec_${DateTime.now().millisecondsSinceEpoch}',
      title: 'New Section',
      subSections: [
        FormSubSection(
          id: 'subsec_${DateTime.now().millisecondsSinceEpoch}',
          title: 'Sub-section 1',
          questions: [],
        ),
      ],
    );
    state = state.copyWith(sections: [...state.sections, newSec]);
  }

  void updateSection(String id, {String? title, String? description, bool? repeatable}) {
    state = state.copyWith(
      sections: state.sections.map((sec) {
        if (sec.id != id) return sec;
        return sec.copyWith(
          title: title ?? sec.title,
          description: description ?? sec.description,
          repeatable: repeatable ?? sec.repeatable,
        );
      }).toList(),
    );
  }

  void addSubSection(String sectionId) {
    state = state.copyWith(
      sections: state.sections.map((sec) {
        if (sec.id != sectionId) return sec;
        final newSub = FormSubSection(
          id: 'subsec_${DateTime.now().millisecondsSinceEpoch}',
          title: 'New Sub-section',
          questions: [],
        );
        return sec.copyWith(subSections: [...sec.subSections, newSub]);
      }).toList(),
    );
  }

  void updateSubSection(String subSecId, {String? title, bool? repeatable}) {
    state = state.copyWith(
      sections: state.sections.map((sec) {
        return sec.copyWith(
          subSections: sec.subSections.map((sub) {
            if (sub.id != subSecId) return sub;
            return sub.copyWith(
              title: title ?? sub.title,
              repeatable: repeatable ?? sub.repeatable,
            );
          }).toList(),
        );
      }).toList(),
    );
  }

  void addQuestion(String subSecId, String type) {
    final qId = 'q_${DateTime.now().millisecondsSinceEpoch}';
    final newQ = FormQuestion(
      id: qId,
      type: type,
      label: 'New Question (${type})',
      properties: {
        'placeholder': 'Enter value',
      },
    );

    state = state.copyWith(
      sections: state.sections.map((sec) {
        return sec.copyWith(
          subSections: sec.subSections.map((sub) {
            if (sub.id != subSecId) return sub;
            return sub.copyWith(questions: [...sub.questions, newQ]);
          }).toList(),
        );
      }).toList(),
      selectedElementId: qId,
    );
  }

  void updateQuestion(String qId, {String? label, String? description, bool? required, Map<String, dynamic>? properties}) {
    state = state.copyWith(
      sections: state.sections.map((sec) {
        return sec.copyWith(
          subSections: sec.subSections.map((sub) {
            return sub.copyWith(
              questions: sub.questions.map((q) {
                if (q.id != qId) return q;
                return q.copyWith(
                  label: label ?? q.label,
                  description: description ?? q.description,
                  required: required ?? q.required,
                  properties: properties ?? q.properties,
                );
              }).toList(),
            );
          }).toList(),
        );
      }).toList(),
    );
  }

  void deleteElement(String id) {
    // Attempt deleting question
    var foundAndDeleted = false;
    final newSections = state.sections.map((sec) {
      final newSubs = sec.subSections.map((sub) {
        final initialLen = sub.questions.length;
        final filteredQs = sub.questions.where((q) => q.id != id).toList();
        if (filteredQs.length != initialLen) foundAndDeleted = true;
        return sub.copyWith(questions: filteredQs);
      }).toList();
      return sec.copyWith(subSections: newSubs);
    }).toList();

    if (foundAndDeleted) {
      state = state.copyWith(
        sections: newSections,
        selectedElementId: state.selectedElementId == id ? null : state.selectedElementId,
      );
      return;
    }

    // Attempt deleting subsection
    final newSections2 = state.sections.map((sec) {
      final initialLen = sec.subSections.length;
      final filteredSubs = sec.subSections.where((sub) => sub.id != id).toList();
      if (filteredSubs.length != initialLen) foundAndDeleted = true;
      return sec.copyWith(subSections: filteredSubs);
    }).toList();

    if (foundAndDeleted) {
      state = state.copyWith(
        sections: newSections2,
        selectedElementId: state.selectedElementId == id ? null : state.selectedElementId,
      );
      return;
    }

    // Attempt deleting section
    final filteredSecs = state.sections.where((sec) => sec.id != id).toList();
    state = state.copyWith(
      sections: filteredSecs,
      selectedElementId: state.selectedElementId == id ? null : state.selectedElementId,
    );
  }
}

final formBuilderProvider = NotifierProvider<FormBuilderNotifier, FormBuilderState>(() {
  return FormBuilderNotifier();
});
