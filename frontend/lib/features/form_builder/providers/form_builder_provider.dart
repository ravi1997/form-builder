import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../shared/json_ui_engine/models/validation_rule.dart';
import '../../../shared/json_ui_engine/models/visibility_rule.dart';
import '../../../core/formula/formula_parser.dart';
import 'logic_validator.dart';

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

class FormStyle {
  final String? themeId;
  final String primaryColor;
  final String backgroundColor;
  final String fontFamily;
  final double borderRadius;
  final String inputStyle;
  final String customCss;

  FormStyle({
    this.themeId,
    this.primaryColor = '#2196F3',
    this.backgroundColor = '#FFFFFF',
    this.fontFamily = 'Roboto',
    this.borderRadius = 8.0,
    this.inputStyle = 'outlined',
    this.customCss = '',
  });

  FormStyle copyWith({
    String? themeId,
    String? primaryColor,
    String? backgroundColor,
    String? fontFamily,
    double? borderRadius,
    String? inputStyle,
    String? customCss,
    bool clearThemeId = false,
  }) {
    return FormStyle(
      themeId: clearThemeId ? null : (themeId ?? this.themeId),
      primaryColor: primaryColor ?? this.primaryColor,
      backgroundColor: backgroundColor ?? this.backgroundColor,
      fontFamily: fontFamily ?? this.fontFamily,
      borderRadius: borderRadius ?? this.borderRadius,
      inputStyle: inputStyle ?? this.inputStyle,
      customCss: customCss ?? this.customCss,
    );
  }
}

class FormNotifications {
  final bool emailEnabled;
  final String emailTriggerEvent;
  final List<String> emailRecipients;
  final bool emailIncludePayload;
  final bool emailIncludeAttachments;

  final bool webhookEnabled;
  final String webhookUrl;
  final String webhookSecret;
  final String webhookContentType;

  final bool internalEnabled;
  final List<String> internalUserIds;
  final List<String> internalTeamIds;

  final int retryAttempts;
  final bool alertOwnerOnFailure;

  FormNotifications({
    this.emailEnabled = false,
    this.emailTriggerEvent = 'on_submission',
    this.emailRecipients = const [],
    this.emailIncludePayload = true,
    this.emailIncludeAttachments = false,
    this.webhookEnabled = false,
    this.webhookUrl = '',
    this.webhookSecret = '',
    this.webhookContentType = 'application/json',
    this.internalEnabled = false,
    this.internalUserIds = const [],
    this.internalTeamIds = const [],
    this.retryAttempts = 3,
    this.alertOwnerOnFailure = true,
  });

  FormNotifications copyWith({
    bool? emailEnabled,
    String? emailTriggerEvent,
    List<String>? emailRecipients,
    bool? emailIncludePayload,
    bool? emailIncludeAttachments,
    bool? webhookEnabled,
    String? webhookUrl,
    String? webhookSecret,
    String? webhookContentType,
    bool? internalEnabled,
    List<String>? internalUserIds,
    List<String>? internalTeamIds,
    int? retryAttempts,
    bool? alertOwnerOnFailure,
  }) {
    return FormNotifications(
      emailEnabled: emailEnabled ?? this.emailEnabled,
      emailTriggerEvent: emailTriggerEvent ?? this.emailTriggerEvent,
      emailRecipients: emailRecipients ?? this.emailRecipients,
      emailIncludePayload: emailIncludePayload ?? this.emailIncludePayload,
      emailIncludeAttachments: emailIncludeAttachments ?? this.emailIncludeAttachments,
      webhookEnabled: webhookEnabled ?? this.webhookEnabled,
      webhookUrl: webhookUrl ?? this.webhookUrl,
      webhookSecret: webhookSecret ?? this.webhookSecret,
      webhookContentType: webhookContentType ?? this.webhookContentType,
      internalEnabled: internalEnabled ?? this.internalEnabled,
      internalUserIds: internalUserIds ?? this.internalUserIds,
      internalTeamIds: internalTeamIds ?? this.internalTeamIds,
      retryAttempts: retryAttempts ?? this.retryAttempts,
      alertOwnerOnFailure: alertOwnerOnFailure ?? this.alertOwnerOnFailure,
    );
  }
}

class FormAnalyticsSettings {
  final bool enabled;
  final String startEventType; // 'form_load', 'first_interaction', 'first_input'
  final String endEventType; // 'submit_success', 'submit_attempt'
  final bool dropOffEnabled;
  final bool timingEnabled;
  final bool utmCaptureEnabled;

  FormAnalyticsSettings({
    this.enabled = true,
    this.startEventType = 'first_interaction',
    this.endEventType = 'submit_success',
    this.dropOffEnabled = true,
    this.timingEnabled = true,
    this.utmCaptureEnabled = true,
  });

  FormAnalyticsSettings copyWith({
    bool? enabled,
    String? startEventType,
    String? endEventType,
    bool? dropOffEnabled,
    bool? timingEnabled,
    bool? utmCaptureEnabled,
  }) {
    return FormAnalyticsSettings(
      enabled: enabled ?? this.enabled,
      startEventType: startEventType ?? this.startEventType,
      endEventType: endEventType ?? this.endEventType,
      dropOffEnabled: dropOffEnabled ?? this.dropOffEnabled,
      timingEnabled: timingEnabled ?? this.timingEnabled,
      utmCaptureEnabled: utmCaptureEnabled ?? this.utmCaptureEnabled,
    );
  }
}

enum FormCanvasMode { edit, play, split }

class FormPlayState {
  final Map<String, dynamic> answers;
  final Map<String, String> validationErrors;

  FormPlayState({
    this.answers = const {},
    this.validationErrors = const {},
  });

  FormPlayState copyWith({
    Map<String, dynamic>? answers,
    Map<String, String>? validationErrors,
  }) {
    return FormPlayState(
      answers: answers ?? this.answers,
      validationErrors: validationErrors ?? this.validationErrors,
    );
  }
}

class FormPlayNotifier extends Notifier<FormPlayState> {
  @override
  FormPlayState build() {
    return FormPlayState();
  }

  void setAnswer(String questionId, dynamic value) {
    final newAnswers = Map<String, dynamic>.from(state.answers);
    if (value == null) {
      newAnswers.remove(questionId);
    } else {
      newAnswers[questionId] = value;
    }
    state = state.copyWith(answers: newAnswers);

    try {
      final sections = ref.read(formBuilderProvider).sections;
      evaluateFormulas(sections);
    } catch (_) {}
  }

  void evaluateFormulas(List<FormSection> sections) {
    final variables = <String, double>{};
    state.answers.forEach((key, val) {
      if (val is num) {
        variables[key] = val.toDouble();
      } else if (val is String) {
        final parsed = double.tryParse(val);
        if (parsed != null) {
          variables[key] = parsed;
        }
      }
    });

    final newAnswers = Map<String, dynamic>.from(state.answers);
    bool changed = false;

    // Run up to 5 iterations for cascading/dependent formulas
    for (int iter = 0; iter < 5; iter++) {
      bool localChanged = false;
      for (final sec in sections) {
        for (final subSec in sec.subSections) {
          for (final q in subSec.questions) {
            if (q.calculations.isNotEmpty) {
              for (final calc in q.calculations) {
                if (calc is Map && calc.containsKey('formula')) {
                  final formula = calc['formula'] as String;
                  try {
                    final parser = FormulaParser(formula);
                    final ast = parser.parse();
                    final computed = ast.evaluate(variables);
                    
                    final oldVal = newAnswers[q.id];
                    if (oldVal != computed) {
                      newAnswers[q.id] = computed;
                      variables[q.id] = computed;
                      localChanged = true;
                      changed = true;
                    }
                  } catch (_) {}
                }
              }
            }
          }
        }
      }
      if (!localChanged) break;
    }

    if (changed) {
      state = state.copyWith(answers: newAnswers);
    }
  }

  void setError(String questionId, String error) {
    final newErrors = Map<String, String>.from(state.validationErrors);
    newErrors[questionId] = error;
    state = state.copyWith(validationErrors: newErrors);
  }

  void clearError(String questionId) {
    final newErrors = Map<String, String>.from(state.validationErrors);
    newErrors.remove(questionId);
    state = state.copyWith(validationErrors: newErrors);
  }

  void reset() {
    state = FormPlayState();
  }
}

final formPlayProvider = NotifierProvider<FormPlayNotifier, FormPlayState>(() {
  return FormPlayNotifier();
});

class FormBuilderState {
  final String formId;
  final String name;
  final String description;
  final List<FormSection> sections;
  final String? selectedElementId; // Currently selected Section/SubSection/Question ID
  final FormStyle style;
  final FormCanvasMode canvasMode;
  final List<LogicValidationIssue> logicIssues;
  final FormNotifications notifications;
  final FormAnalyticsSettings analytics;

  FormBuilderState({
    required this.formId,
    required this.name,
    this.description = '',
    required this.sections,
    this.selectedElementId,
    required this.style,
    this.canvasMode = FormCanvasMode.edit,
    this.logicIssues = const [],
    FormNotifications? notifications,
    FormAnalyticsSettings? analytics,
  }) : notifications = notifications ?? FormNotifications(),
       analytics = analytics ?? FormAnalyticsSettings();

  FormBuilderState copyWith({
    String? formId,
    String? name,
    String? description,
    List<FormSection>? sections,
    String? selectedElementId,
    FormStyle? style,
    FormCanvasMode? canvasMode,
    bool clearSelectedElementId = false,
    List<LogicValidationIssue>? logicIssues,
    FormNotifications? notifications,
    FormAnalyticsSettings? analytics,
  }) {
    return FormBuilderState(
      formId: formId ?? this.formId,
      name: name ?? this.name,
      description: description ?? this.description,
      sections: sections ?? List<FormSection>.from(this.sections),
      selectedElementId: clearSelectedElementId ? null : (selectedElementId ?? this.selectedElementId),
      style: style ?? this.style,
      canvasMode: canvasMode ?? this.canvasMode,
      logicIssues: logicIssues ?? this.logicIssues,
      notifications: notifications ?? this.notifications,
      analytics: analytics ?? this.analytics,
    );
  }
}

class FormBuilderNotifier extends Notifier<FormBuilderState> {
  @override
  FormBuilderState build() {
    final initialState = FormBuilderState(
      formId: 'default',
      name: 'My Custom Form',
      style: FormStyle(),
      canvasMode: FormCanvasMode.edit,
      notifications: FormNotifications(),
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
    final issues = LogicGraphValidator.validate(initialState);
    return initialState.copyWith(logicIssues: issues);
  }

  @override
  set state(FormBuilderState value) {
    final issues = LogicGraphValidator.validate(value);
    super.state = value.copyWith(logicIssues: issues);
  }

  void setCanvasMode(FormCanvasMode mode) {
    state = state.copyWith(canvasMode: mode);
  }

  void updateStyle({
    String? themeId,
    String? primaryColor,
    String? backgroundColor,
    String? fontFamily,
    double? borderRadius,
    String? inputStyle,
    String? customCss,
    bool clearThemeId = false,
  }) {
    state = state.copyWith(
      style: state.style.copyWith(
        themeId: themeId,
        primaryColor: primaryColor,
        backgroundColor: backgroundColor,
        fontFamily: fontFamily,
        borderRadius: borderRadius,
        inputStyle: inputStyle,
        customCss: customCss,
        clearThemeId: clearThemeId,
      ),
    );
  }

  void updateNotifications({
    bool? emailEnabled,
    String? emailTriggerEvent,
    List<String>? emailRecipients,
    bool? emailIncludePayload,
    bool? emailIncludeAttachments,
    bool? webhookEnabled,
    String? webhookUrl,
    String? webhookSecret,
    String? webhookContentType,
    bool? internalEnabled,
    List<String>? internalUserIds,
    List<String>? internalTeamIds,
    int? retryAttempts,
    bool? alertOwnerOnFailure,
  }) {
    state = state.copyWith(
      notifications: state.notifications.copyWith(
        emailEnabled: emailEnabled,
        emailTriggerEvent: emailTriggerEvent,
        emailRecipients: emailRecipients,
        emailIncludePayload: emailIncludePayload,
        emailIncludeAttachments: emailIncludeAttachments,
        webhookEnabled: webhookEnabled,
        webhookUrl: webhookUrl,
        webhookSecret: webhookSecret,
        webhookContentType: webhookContentType,
        internalEnabled: internalEnabled,
        internalUserIds: internalUserIds,
        internalTeamIds: internalTeamIds,
        retryAttempts: retryAttempts,
        alertOwnerOnFailure: alertOwnerOnFailure,
      ),
    );
  }

  void updateAnalytics({
    bool? enabled,
    String? startEventType,
    String? endEventType,
    bool? dropOffEnabled,
    bool? timingEnabled,
    bool? utmCaptureEnabled,
  }) {
    state = state.copyWith(
      analytics: state.analytics.copyWith(
        enabled: enabled,
        startEventType: startEventType,
        endEventType: endEventType,
        dropOffEnabled: dropOffEnabled,
        timingEnabled: timingEnabled,
        utmCaptureEnabled: utmCaptureEnabled,
      ),
    );
  }

  void selectElement(String? id) {
    state = state.copyWith(
      selectedElementId: id,
      clearSelectedElementId: id == null,
    );
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

  void insertQuestion(String subSecId, int index, FormQuestion question) {
    state = state.copyWith(
      sections: state.sections.map((sec) {
        return sec.copyWith(
          subSections: sec.subSections.map((sub) {
            if (sub.id != subSecId) return sub;
            final qs = [...sub.questions];
            if (index < 0) {
              qs.add(question);
            } else {
              qs.insert(index.clamp(0, qs.length), question);
            }
            return sub.copyWith(questions: qs);
          }).toList(),
        );
      }).toList(),
    );
  }

  void moveQuestion({
    required String fromSubSecId,
    required String toSubSecId,
    required String questionId,
    required int toIndex,
  }) {
    FormQuestion? targetQ;
    for (final sec in state.sections) {
      for (final sub in sec.subSections) {
        if (sub.id == fromSubSecId) {
          for (final q in sub.questions) {
            if (q.id == questionId) {
              targetQ = q;
              break;
            }
          }
        }
      }
    }
    if (targetQ == null) return;

    state = state.copyWith(
      sections: state.sections.map((sec) {
        return sec.copyWith(
          subSections: sec.subSections.map((sub) {
            if (sub.id != fromSubSecId) return sub;
            return sub.copyWith(
              questions: sub.questions.where((q) => q.id != questionId).toList(),
            );
          }).toList(),
        );
      }).toList(),
    );

    insertQuestion(toSubSecId, toIndex, targetQ);
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
    VisibilityRules? visibilityRules,
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
                  visibilityRules: visibilityRules ?? q.visibilityRules,
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
        clearSelectedElementId: state.selectedElementId == id,
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
        clearSelectedElementId: state.selectedElementId == id,
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
      clearSelectedElementId: state.selectedElementId == id,
    );
  }
}

final formBuilderProvider =
    NotifierProvider<FormBuilderNotifier, FormBuilderState>(() {
      return FormBuilderNotifier();
    });
