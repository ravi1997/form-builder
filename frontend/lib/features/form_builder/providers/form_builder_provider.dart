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
    this.visibilityRules = const VisibilityRules(
      operator: LogicalOperator.and,
      conditions: [],
    ),
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
  final String subtitle;
  final String sectionKey;
  final String? icon;
  final String? parentSectionId;
  final bool repeatable;
  final bool collapsible;
  final bool defaultCollapsed;
  final bool showInNavigation;
  final bool hideTitle;
  final int columns;
  final String density;
  final String displayMode;
  final String? backgroundColor;
  final String? accentColor;
  final String? headerImage;
  final String? internalNote;
  final String? accessLevel;
  final bool approvalRequired;
  final bool trackOpen;
  final bool trackCompletionTime;
  final String? visibilityRule;
  final String? skipToSectionId;
  final String? analyticsTag;
  final bool hideFromProgress;
  final bool lockSection;
  final String? owner;
  final String? dueDate;
  final String? templateName;
  final bool isTemplate;
  final bool archived;
  final bool showBreadcrumb;
  final bool showProgressStep;
  final String? notes;
  final String? cssClass;
  final String? headerActionLabel;
  final bool allowPartialSave;
  final int minQuestionsRequired;
  final String? completionNote;
  final String? validationSummary;
  final List<String> visibleToRoles;
  final List<String> editableByRoles;
  final List<String> tags;
  final List<FormSubSection> subSections;

  FormSection({
    required this.id,
    required this.title,
    this.description = '',
    this.subtitle = '',
    String? sectionKey,
    this.icon,
    this.parentSectionId,
    this.repeatable = false,
    this.collapsible = false,
    this.defaultCollapsed = false,
    this.showInNavigation = true,
    this.hideTitle = false,
    this.columns = 1,
    this.density = 'normal',
    this.displayMode = 'plain',
    this.backgroundColor,
    this.accentColor,
    this.headerImage,
    this.internalNote,
    this.accessLevel,
    this.approvalRequired = false,
    this.trackOpen = false,
    this.trackCompletionTime = false,
    this.visibilityRule,
    this.skipToSectionId,
    this.analyticsTag,
    this.hideFromProgress = false,
    this.lockSection = false,
    this.owner,
    this.dueDate,
    this.templateName,
    this.isTemplate = false,
    this.archived = false,
    this.showBreadcrumb = true,
    this.showProgressStep = true,
    this.notes,
    this.cssClass,
    this.headerActionLabel,
    this.allowPartialSave = true,
    this.minQuestionsRequired = 0,
    this.completionNote,
    this.validationSummary,
    this.visibleToRoles = const [],
    this.editableByRoles = const [],
    this.tags = const [],
    required this.subSections,
  }) : sectionKey = sectionKey ?? _slugify(title);

  FormSection copyWith({
    String? id,
    String? title,
    String? description,
    String? subtitle,
    String? sectionKey,
    String? icon,
    String? parentSectionId,
    bool? repeatable,
    bool? collapsible,
    bool? defaultCollapsed,
    bool? showInNavigation,
    bool? hideTitle,
    int? columns,
    String? density,
    String? displayMode,
    String? backgroundColor,
    String? accentColor,
    String? headerImage,
    String? internalNote,
    String? accessLevel,
    bool? approvalRequired,
    bool? trackOpen,
    bool? trackCompletionTime,
    String? visibilityRule,
    String? skipToSectionId,
    String? analyticsTag,
    bool? hideFromProgress,
    bool? lockSection,
    String? owner,
    String? dueDate,
    String? templateName,
    bool? isTemplate,
    bool? archived,
    bool? showBreadcrumb,
    bool? showProgressStep,
    String? notes,
    String? cssClass,
    String? headerActionLabel,
    bool? allowPartialSave,
    int? minQuestionsRequired,
    String? completionNote,
    String? validationSummary,
    List<String>? visibleToRoles,
    List<String>? editableByRoles,
    List<String>? tags,
    List<FormSubSection>? subSections,
  }) {
    return FormSection(
      id: id ?? this.id,
      title: title ?? this.title,
      description: description ?? this.description,
      subtitle: subtitle ?? this.subtitle,
      sectionKey: sectionKey ?? this.sectionKey,
      icon: icon ?? this.icon,
      parentSectionId: parentSectionId ?? this.parentSectionId,
      repeatable: repeatable ?? this.repeatable,
      collapsible: collapsible ?? this.collapsible,
      defaultCollapsed: defaultCollapsed ?? this.defaultCollapsed,
      showInNavigation: showInNavigation ?? this.showInNavigation,
      hideTitle: hideTitle ?? this.hideTitle,
      columns: columns ?? this.columns,
      density: density ?? this.density,
      displayMode: displayMode ?? this.displayMode,
      backgroundColor: backgroundColor ?? this.backgroundColor,
      accentColor: accentColor ?? this.accentColor,
      headerImage: headerImage ?? this.headerImage,
      internalNote: internalNote ?? this.internalNote,
      accessLevel: accessLevel ?? this.accessLevel,
      approvalRequired: approvalRequired ?? this.approvalRequired,
      trackOpen: trackOpen ?? this.trackOpen,
      trackCompletionTime: trackCompletionTime ?? this.trackCompletionTime,
      visibilityRule: visibilityRule ?? this.visibilityRule,
      skipToSectionId: skipToSectionId ?? this.skipToSectionId,
      analyticsTag: analyticsTag ?? this.analyticsTag,
      hideFromProgress: hideFromProgress ?? this.hideFromProgress,
      lockSection: lockSection ?? this.lockSection,
      owner: owner ?? this.owner,
      dueDate: dueDate ?? this.dueDate,
      templateName: templateName ?? this.templateName,
      isTemplate: isTemplate ?? this.isTemplate,
      archived: archived ?? this.archived,
      showBreadcrumb: showBreadcrumb ?? this.showBreadcrumb,
      showProgressStep: showProgressStep ?? this.showProgressStep,
      notes: notes ?? this.notes,
      cssClass: cssClass ?? this.cssClass,
      headerActionLabel: headerActionLabel ?? this.headerActionLabel,
      allowPartialSave: allowPartialSave ?? this.allowPartialSave,
      minQuestionsRequired: minQuestionsRequired ?? this.minQuestionsRequired,
      completionNote: completionNote ?? this.completionNote,
      validationSummary: validationSummary ?? this.validationSummary,
      visibleToRoles: visibleToRoles ?? List<String>.from(this.visibleToRoles),
      editableByRoles:
          editableByRoles ?? List<String>.from(this.editableByRoles),
      tags: tags ?? List<String>.from(this.tags),
      subSections: subSections ?? List<FormSubSection>.from(this.subSections),
    );
  }
}

String _slugify(String input) {
  final slug = input
      .toLowerCase()
      .trim()
      .replaceAll(RegExp(r'[^a-z0-9]+'), '_')
      .replaceAll(RegExp(r'_+'), '_')
      .replaceAll(RegExp(r'^_+|_+$'), '');
  return slug.isEmpty ? 'section' : slug;
}

class FormBuilderState {
  final String formId;
  final String name;
  final String description;
  final List<FormSection> sections;
  final String?
  selectedElementId; // Currently selected Section/SubSection/Question ID

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

  void updateSection(
    String id, {
    String? title,
    String? description,
    String? subtitle,
    String? sectionKey,
    String? icon,
    String? parentSectionId,
    bool? repeatable,
    bool? collapsible,
    bool? defaultCollapsed,
    bool? showInNavigation,
    bool? hideTitle,
    int? columns,
    String? density,
    String? displayMode,
    String? backgroundColor,
    String? accentColor,
    String? headerImage,
    String? internalNote,
    String? accessLevel,
    bool? approvalRequired,
    bool? trackOpen,
    bool? trackCompletionTime,
    String? visibilityRule,
    String? skipToSectionId,
    String? analyticsTag,
    bool? hideFromProgress,
    bool? lockSection,
    String? owner,
    String? dueDate,
    String? templateName,
    bool? isTemplate,
    bool? archived,
    bool? showBreadcrumb,
    bool? showProgressStep,
    String? notes,
    String? cssClass,
    String? headerActionLabel,
    bool? allowPartialSave,
    int? minQuestionsRequired,
    String? completionNote,
    String? validationSummary,
    List<String>? visibleToRoles,
    List<String>? editableByRoles,
    List<String>? tags,
  }) {
    state = state.copyWith(
      sections: state.sections.map((sec) {
        if (sec.id != id) return sec;
        return sec.copyWith(
          title: title ?? sec.title,
          description: description ?? sec.description,
          subtitle: subtitle ?? sec.subtitle,
          sectionKey: sectionKey ?? sec.sectionKey,
          icon: icon ?? sec.icon,
          parentSectionId: parentSectionId ?? sec.parentSectionId,
          repeatable: repeatable ?? sec.repeatable,
          collapsible: collapsible ?? sec.collapsible,
          defaultCollapsed: defaultCollapsed ?? sec.defaultCollapsed,
          showInNavigation: showInNavigation ?? sec.showInNavigation,
          hideTitle: hideTitle ?? sec.hideTitle,
          columns: columns ?? sec.columns,
          density: density ?? sec.density,
          displayMode: displayMode ?? sec.displayMode,
          backgroundColor: backgroundColor ?? sec.backgroundColor,
          accentColor: accentColor ?? sec.accentColor,
          headerImage: headerImage ?? sec.headerImage,
          internalNote: internalNote ?? sec.internalNote,
          accessLevel: accessLevel ?? sec.accessLevel,
          approvalRequired: approvalRequired ?? sec.approvalRequired,
          trackOpen: trackOpen ?? sec.trackOpen,
          trackCompletionTime: trackCompletionTime ?? sec.trackCompletionTime,
          visibilityRule: visibilityRule ?? sec.visibilityRule,
          skipToSectionId: skipToSectionId ?? sec.skipToSectionId,
          analyticsTag: analyticsTag ?? sec.analyticsTag,
          hideFromProgress: hideFromProgress ?? sec.hideFromProgress,
          lockSection: lockSection ?? sec.lockSection,
          owner: owner ?? sec.owner,
          dueDate: dueDate ?? sec.dueDate,
          templateName: templateName ?? sec.templateName,
          isTemplate: isTemplate ?? sec.isTemplate,
          archived: archived ?? sec.archived,
          showBreadcrumb: showBreadcrumb ?? sec.showBreadcrumb,
          showProgressStep: showProgressStep ?? sec.showProgressStep,
          notes: notes ?? sec.notes,
          cssClass: cssClass ?? sec.cssClass,
          headerActionLabel: headerActionLabel ?? sec.headerActionLabel,
          allowPartialSave: allowPartialSave ?? sec.allowPartialSave,
          minQuestionsRequired:
              minQuestionsRequired ?? sec.minQuestionsRequired,
          completionNote: completionNote ?? sec.completionNote,
          validationSummary: validationSummary ?? sec.validationSummary,
          visibleToRoles: visibleToRoles ?? sec.visibleToRoles,
          editableByRoles: editableByRoles ?? sec.editableByRoles,
          tags: tags ?? sec.tags,
        );
      }).toList(),
    );
  }

  void duplicateSection(String id) {
    final index = state.sections.indexWhere((sec) => sec.id == id);
    if (index == -1) return;
    final original = state.sections[index];
    final duplicate = original.copyWith(
      id: 'sec_${DateTime.now().millisecondsSinceEpoch}',
      title: '${original.title} copy',
      sectionKey: '${original.sectionKey}_copy',
    );
    final next = [...state.sections];
    next.insert(index + 1, duplicate);
    state = state.copyWith(sections: next, selectedElementId: duplicate.id);
  }

  void moveSection(String id, int delta) {
    final index = state.sections.indexWhere((sec) => sec.id == id);
    if (index == -1) return;
    final target = index + delta;
    if (target < 0 || target >= state.sections.length) return;
    final next = [...state.sections];
    final item = next.removeAt(index);
    next.insert(target, item);
    state = state.copyWith(sections: next);
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

  void addQuestion(String subSecId, String type) {
    final qId = 'q_${DateTime.now().millisecondsSinceEpoch}';
    final newQ = FormQuestion(
      id: qId,
      type: type,
      label: 'New Question ($type)',
      properties: {'placeholder': 'Enter value'},
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

  void updateQuestion(
    String qId, {
    String? label,
    String? description,
    bool? required,
    Map<String, dynamic>? properties,
  }) {
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
        selectedElementId: state.selectedElementId == id
            ? null
            : state.selectedElementId,
      );
      return;
    }

    // Attempt deleting subsection
    final newSections2 = state.sections.map((sec) {
      final initialLen = sec.subSections.length;
      final filteredSubs = sec.subSections
          .where((sub) => sub.id != id)
          .toList();
      if (filteredSubs.length != initialLen) foundAndDeleted = true;
      return sec.copyWith(subSections: filteredSubs);
    }).toList();

    if (foundAndDeleted) {
      state = state.copyWith(
        sections: newSections2,
        selectedElementId: state.selectedElementId == id
            ? null
            : state.selectedElementId,
      );
      return;
    }

    // Attempt deleting section
    final filteredSecs = state.sections.where((sec) => sec.id != id).toList();
    state = state.copyWith(
      sections: filteredSecs,
      selectedElementId: state.selectedElementId == id
          ? null
          : state.selectedElementId,
    );
  }
}

final formBuilderProvider =
    NotifierProvider<FormBuilderNotifier, FormBuilderState>(() {
      return FormBuilderNotifier();
    });
