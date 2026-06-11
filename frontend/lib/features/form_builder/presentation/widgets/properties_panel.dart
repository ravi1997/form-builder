import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/design_system.dart';
import '../../../../core/theme/tokens.dart';
import '../../providers/form_builder_provider.dart';

class PropertiesPanel extends ConsumerStatefulWidget {
  const PropertiesPanel({super.key});

  @override
  ConsumerState<PropertiesPanel> createState() => _PropertiesPanelState();
}

class _PropertiesPanelState extends ConsumerState<PropertiesPanel> {
  String? _selectedId;
  FormSection? _selectedSection;
  FormSubSection? _selectedSubSection;
  FormQuestion? _selectedQuestion;

  final _sectionTitle = TextEditingController();
  final _sectionSubtitle = TextEditingController();
  final _sectionDescription = TextEditingController();
  final _sectionInternalNote = TextEditingController();
  final _sectionKey = TextEditingController();
  final _sectionTags = TextEditingController();
  final _sectionBackground = TextEditingController();
  final _sectionAccent = TextEditingController();
  final _sectionHeaderImage = TextEditingController();
  final _sectionVisibilityRule = TextEditingController();
  final _sectionSkipTo = TextEditingController();
  final _sectionAnalyticsTag = TextEditingController();
  final _sectionOwner = TextEditingController();
  final _sectionDueDate = TextEditingController();
  final _sectionTemplateName = TextEditingController();
  final _sectionNotes = TextEditingController();
  final _sectionCssClass = TextEditingController();
  final _sectionHeaderAction = TextEditingController();
  final _sectionCompletionNote = TextEditingController();
  final _sectionValidationSummary = TextEditingController();
  final _sectionVisibleTo = TextEditingController();
  final _sectionEditableBy = TextEditingController();
  final _subSectionTitle = TextEditingController();
  final _fieldLabel = TextEditingController();
  final _fieldDescription = TextEditingController();
  final _fieldPlaceholder = TextEditingController();
  final _fieldOptions = TextEditingController();

  @override
  void dispose() {
    _sectionTitle.dispose();
    _sectionSubtitle.dispose();
    _sectionDescription.dispose();
    _sectionInternalNote.dispose();
    _sectionKey.dispose();
    _sectionTags.dispose();
    _sectionBackground.dispose();
    _sectionAccent.dispose();
    _sectionHeaderImage.dispose();
    _sectionVisibilityRule.dispose();
    _sectionSkipTo.dispose();
    _sectionAnalyticsTag.dispose();
    _sectionOwner.dispose();
    _sectionDueDate.dispose();
    _sectionTemplateName.dispose();
    _sectionNotes.dispose();
    _sectionCssClass.dispose();
    _sectionHeaderAction.dispose();
    _sectionCompletionNote.dispose();
    _sectionValidationSummary.dispose();
    _sectionVisibleTo.dispose();
    _sectionEditableBy.dispose();
    _subSectionTitle.dispose();
    _fieldLabel.dispose();
    _fieldDescription.dispose();
    _fieldPlaceholder.dispose();
    _fieldOptions.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final builderState = ref.watch(formBuilderProvider);
    final selectedId = builderState.selectedElementId;
    final theme = Theme.of(context);

    _syncSelection(builderState.sections, selectedId);

    if (selectedId == null) {
      return Container(
        decoration: AppSurfaceStyles.card(),
        child: const Center(
          child: Padding(
            padding: EdgeInsets.all(AppSpacing.xl),
            child: Text(
              'Select a section, sub-section, or question to edit its properties.',
              textAlign: TextAlign.center,
              style: TextStyle(color: AppColors.textMuted),
            ),
          ),
        ),
      );
    }

    return Container(
      decoration: AppSurfaceStyles.card(),
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.lg),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Properties',
                        style: theme.textTheme.titleLarge?.copyWith(
                          fontWeight: FontWeight.w800,
                        ),
                      ),
                      const SizedBox(height: AppSpacing.xs),
                      Text(
                        'Editing $selectedId',
                        style: theme.textTheme.bodySmall?.copyWith(
                          color: AppColors.textMuted,
                        ),
                      ),
                    ],
                  ),
                ),
                IconButton.filledTonal(
                  icon: const Icon(Icons.delete_outline),
                  tooltip: 'Delete selected element',
                  onPressed: () {
                    ref
                        .read(formBuilderProvider.notifier)
                        .deleteElement(selectedId);
                  },
                ),
              ],
            ),
            const SizedBox(height: AppSpacing.md),
            Container(height: 1, color: AppColors.builderDivider),
            const SizedBox(height: AppSpacing.md),
            Expanded(
              child: Scrollbar(
                child: SingleChildScrollView(
                  child: Builder(
                    builder: (context) {
                      if (_selectedSection != null) {
                        return _SectionEditor(
                          section: _selectedSection!,
                          titleController: _sectionTitle,
                          subtitleController: _sectionSubtitle,
                          descriptionController: _sectionDescription,
                          internalNoteController: _sectionInternalNote,
                          sectionKeyController: _sectionKey,
                          tagsController: _sectionTags,
                          backgroundController: _sectionBackground,
                          accentController: _sectionAccent,
                          headerImageController: _sectionHeaderImage,
                          visibilityRuleController: _sectionVisibilityRule,
                          skipToController: _sectionSkipTo,
                          analyticsTagController: _sectionAnalyticsTag,
                          ownerController: _sectionOwner,
                          dueDateController: _sectionDueDate,
                          templateNameController: _sectionTemplateName,
                          notesController: _sectionNotes,
                          cssClassController: _sectionCssClass,
                          headerActionController: _sectionHeaderAction,
                          completionNoteController: _sectionCompletionNote,
                          validationSummaryController:
                              _sectionValidationSummary,
                          visibleToController: _sectionVisibleTo,
                          editableByController: _sectionEditableBy,
                        );
                      }
                      if (_selectedSubSection != null) {
                        return _SubSectionEditor(
                          subSection: _selectedSubSection!,
                          titleController: _subSectionTitle,
                        );
                      }
                      if (_selectedQuestion != null) {
                        return _QuestionEditor(
                          question: _selectedQuestion!,
                          labelController: _fieldLabel,
                          descriptionController: _fieldDescription,
                          placeholderController: _fieldPlaceholder,
                          optionsController: _fieldOptions,
                        );
                      }
                      return const Text(
                        'Element details not found.',
                        style: TextStyle(color: AppColors.textMuted),
                      );
                    },
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  void _syncSelection(List<FormSection> sections, String? selectedId) {
    if (_selectedId == selectedId) return;
    _selectedId = selectedId;
    _selectedSection = null;
    _selectedSubSection = null;
    _selectedQuestion = null;
    if (selectedId == null) return;

    for (final sec in sections) {
      if (sec.id == selectedId) {
        _selectedSection = sec;
        _syncSectionControllers(sec);
        return;
      }
      for (final sub in sec.subSections) {
        if (sub.id == selectedId) {
          _selectedSubSection = sub;
          _subSectionTitle.text = sub.title;
          return;
        }
        for (final q in sub.questions) {
          if (q.id == selectedId) {
            _selectedQuestion = q;
            _syncQuestionControllers(q);
            return;
          }
        }
      }
    }
  }

  void _syncSectionControllers(FormSection sec) {
    _sectionTitle.text = sec.title;
    _sectionSubtitle.text = sec.subtitle;
    _sectionDescription.text = sec.description;
    _sectionInternalNote.text = sec.internalNote ?? '';
    _sectionKey.text = sec.sectionKey;
    _sectionTags.text = sec.tags.join(', ');
    _sectionBackground.text = sec.backgroundColor ?? '';
    _sectionAccent.text = sec.accentColor ?? '';
    _sectionHeaderImage.text = sec.headerImage ?? '';
    _sectionVisibilityRule.text = sec.visibilityRule ?? '';
    _sectionSkipTo.text = sec.skipToSectionId ?? '';
    _sectionAnalyticsTag.text = sec.analyticsTag ?? '';
    _sectionOwner.text = sec.owner ?? '';
    _sectionDueDate.text = sec.dueDate ?? '';
    _sectionTemplateName.text = sec.templateName ?? '';
    _sectionNotes.text = sec.notes ?? '';
    _sectionCssClass.text = sec.cssClass ?? '';
    _sectionHeaderAction.text = sec.headerActionLabel ?? '';
    _sectionCompletionNote.text = sec.completionNote ?? '';
    _sectionValidationSummary.text = sec.validationSummary ?? '';
    _sectionVisibleTo.text = sec.visibleToRoles.join(', ');
    _sectionEditableBy.text = sec.editableByRoles.join(', ');
  }

  void _syncQuestionControllers(FormQuestion q) {
    _fieldLabel.text = q.label;
    _fieldDescription.text = q.description;
    _fieldPlaceholder.text = q.properties['placeholder']?.toString() ?? '';
    final rawOpts = q.properties['options'];
    if (rawOpts is List) {
      _fieldOptions.text = rawOpts
          .whereType<Map>()
          .map((o) => (o['label'] ?? o['value'] ?? '').toString())
          .where((s) => s.isNotEmpty)
          .join(', ');
    } else {
      _fieldOptions.text = '';
    }
  }
}

class _SectionEditor extends StatelessWidget {
  final FormSection section;
  final TextEditingController titleController;
  final TextEditingController subtitleController;
  final TextEditingController descriptionController;
  final TextEditingController internalNoteController;
  final TextEditingController sectionKeyController;
  final TextEditingController tagsController;
  final TextEditingController backgroundController;
  final TextEditingController accentController;
  final TextEditingController headerImageController;
  final TextEditingController visibilityRuleController;
  final TextEditingController skipToController;
  final TextEditingController analyticsTagController;
  final TextEditingController ownerController;
  final TextEditingController dueDateController;
  final TextEditingController templateNameController;
  final TextEditingController notesController;
  final TextEditingController cssClassController;
  final TextEditingController headerActionController;
  final TextEditingController completionNoteController;
  final TextEditingController validationSummaryController;
  final TextEditingController visibleToController;
  final TextEditingController editableByController;

  const _SectionEditor({
    required this.section,
    required this.titleController,
    required this.subtitleController,
    required this.descriptionController,
    required this.internalNoteController,
    required this.sectionKeyController,
    required this.tagsController,
    required this.backgroundController,
    required this.accentController,
    required this.headerImageController,
    required this.visibilityRuleController,
    required this.skipToController,
    required this.analyticsTagController,
    required this.ownerController,
    required this.dueDateController,
    required this.templateNameController,
    required this.notesController,
    required this.cssClassController,
    required this.headerActionController,
    required this.completionNoteController,
    required this.validationSummaryController,
    required this.visibleToController,
    required this.editableByController,
  });

  @override
  Widget build(BuildContext context) {
    final notifier = context.findAncestorStateOfType<_PropertiesPanelState>();
    if (notifier == null) return const SizedBox.shrink();
    final controller = notifier.ref.read(formBuilderProvider.notifier);
    final sectionChoices = notifier.ref
        .read(formBuilderProvider)
        .sections
        .where((candidate) => candidate.id != section.id)
        .toList();

    return DefaultTabController(
      length: 4,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _sectionHeader(context, 'Section properties'),
          const SizedBox(height: AppSpacing.sm),
          Text(
            'Summary: ${section.repeatable ? 'repeatable' : 'single'} · ${section.collapsible ? 'collapsible' : 'fixed'} · ${section.columns} column${section.columns == 1 ? '' : 's'}',
            style: Theme.of(
              context,
            ).textTheme.bodySmall?.copyWith(color: AppColors.textMuted),
          ),
          const SizedBox(height: AppSpacing.sm),
          Wrap(
            spacing: AppSpacing.xs,
            runSpacing: AppSpacing.xs,
            children: [
              _InfoChip(label: section.density),
              _InfoChip(label: section.displayMode),
              if (section.accessLevel != null)
                _InfoChip(label: section.accessLevel!),
              if (section.isTemplate) const _InfoChip(label: 'template'),
              if (section.archived) const _InfoChip(label: 'archived'),
              if (section.allowPartialSave)
                const _InfoChip(label: 'partial save'),
              if (section.showBreadcrumb) const _InfoChip(label: 'breadcrumb'),
            ],
          ),
          const SizedBox(height: AppSpacing.sm),
          if (section.templateName != null)
            Padding(
              padding: const EdgeInsets.only(bottom: AppSpacing.sm),
              child: _InfoChip(label: section.templateName!),
            ),
          const SizedBox(height: AppSpacing.md),
          const TabBar(
            isScrollable: true,
            tabs: [
              Tab(text: 'General'),
              Tab(text: 'Layout'),
              Tab(text: 'Style'),
              Tab(text: 'Logic'),
            ],
          ),
          const SizedBox(height: AppSpacing.md),
          SizedBox(
            height: 420,
            child: TabBarView(
              children: [
                ListView(
                  children: [
                    _groupCard(
                      context,
                      title: 'Content',
                      children: [
                        TextField(
                          controller: titleController,
                          decoration: const InputDecoration(
                            labelText: 'Section title',
                          ),
                          onChanged: (val) =>
                              controller.updateSection(section.id, title: val),
                        ),
                        const SizedBox(height: AppSpacing.md),
                        TextField(
                          controller: subtitleController,
                          decoration: const InputDecoration(
                            labelText: 'Subtitle',
                          ),
                          onChanged: (val) => controller.updateSection(
                            section.id,
                            subtitle: val,
                          ),
                        ),
                        const SizedBox(height: AppSpacing.md),
                        TextField(
                          controller: descriptionController,
                          decoration: const InputDecoration(
                            labelText: 'Description',
                          ),
                          minLines: 2,
                          maxLines: 4,
                          onChanged: (val) => controller.updateSection(
                            section.id,
                            description: val,
                          ),
                        ),
                        const SizedBox(height: AppSpacing.md),
                        TextField(
                          controller: internalNoteController,
                          decoration: const InputDecoration(
                            labelText: 'Internal note',
                          ),
                          onChanged: (val) => controller.updateSection(
                            section.id,
                            internalNote: val,
                          ),
                        ),
                        const SizedBox(height: AppSpacing.md),
                        TextField(
                          controller: tagsController,
                          decoration: const InputDecoration(
                            labelText: 'Tags',
                            hintText: 'intake, medical, step-1',
                          ),
                          onChanged: (val) => controller.updateSection(
                            section.id,
                            tags: val
                                .split(',')
                                .map((e) => e.trim())
                                .where((e) => e.isNotEmpty)
                                .toList(),
                          ),
                        ),
                        const SizedBox(height: AppSpacing.md),
                        TextField(
                          controller: ownerController,
                          decoration: const InputDecoration(
                            labelText: 'Owner',
                            hintText: 'team or person',
                          ),
                          onChanged: (val) => controller.updateSection(
                            section.id,
                            owner: val.isEmpty ? null : val,
                          ),
                        ),
                        const SizedBox(height: AppSpacing.md),
                        TextField(
                          controller: dueDateController,
                          decoration: const InputDecoration(
                            labelText: 'Due date',
                            hintText: 'YYYY-MM-DD',
                          ),
                          onChanged: (val) => controller.updateSection(
                            section.id,
                            dueDate: val.isEmpty ? null : val,
                          ),
                        ),
                        const SizedBox(height: AppSpacing.md),
                        TextField(
                          controller: templateNameController,
                          decoration: const InputDecoration(
                            labelText: 'Template name',
                            hintText: 'Intake template',
                          ),
                          onChanged: (val) => controller.updateSection(
                            section.id,
                            templateName: val.isEmpty ? null : val,
                            isTemplate: val.isNotEmpty,
                          ),
                        ),
                        const SizedBox(height: AppSpacing.md),
                        TextField(
                          controller: headerActionController,
                          decoration: const InputDecoration(
                            labelText: 'Header action label',
                            hintText: 'Edit instructions',
                          ),
                          onChanged: (val) => controller.updateSection(
                            section.id,
                            headerActionLabel: val.isEmpty ? null : val,
                          ),
                        ),
                        const SizedBox(height: AppSpacing.md),
                        TextField(
                          controller: completionNoteController,
                          decoration: const InputDecoration(
                            labelText: 'Completion note',
                            hintText:
                                'What users should know before continuing',
                          ),
                          minLines: 2,
                          maxLines: 4,
                          onChanged: (val) => controller.updateSection(
                            section.id,
                            completionNote: val.isEmpty ? null : val,
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: AppSpacing.md),
                    _groupCard(
                      context,
                      title: 'Subsections',
                      children: [
                        ...section.subSections.map(
                          (sub) => Padding(
                            padding: const EdgeInsets.only(
                              bottom: AppSpacing.md,
                            ),
                            child: _SubSectionCard(
                              subSection: sub,
                              onTitleChanged: (val) => controller
                                  .updateSubSection(sub.id, title: val),
                              onRepeatableChanged: (val) => controller
                                  .updateSubSection(sub.id, repeatable: val),
                              onDelete: () => controller.deleteElement(sub.id),
                            ),
                          ),
                        ),
                        FilledButton.icon(
                          onPressed: () => controller.addSubSection(section.id),
                          icon: const Icon(Icons.add),
                          label: const Text('Add sub-section'),
                        ),
                      ],
                    ),
                    const SizedBox(height: AppSpacing.md),
                    _groupCard(
                      context,
                      title: 'Behavior',
                      children: [
                        _toggleTile(
                          title: 'Repeatable section',
                          subtitle: 'Allow users to add multiple copies.',
                          value: section.repeatable,
                          onChanged: (val) => controller.updateSection(
                            section.id,
                            repeatable: val,
                          ),
                        ),
                        _toggleTile(
                          title: 'Collapsible',
                          subtitle:
                              'Allow the section to be expanded or collapsed.',
                          value: section.collapsible,
                          onChanged: (val) => controller.updateSection(
                            section.id,
                            collapsible: val,
                          ),
                        ),
                        _toggleTile(
                          title: 'Default collapsed',
                          subtitle: 'Start collapsed when the form loads.',
                          value: section.defaultCollapsed,
                          onChanged: (val) => controller.updateSection(
                            section.id,
                            defaultCollapsed: val,
                          ),
                        ),
                        _toggleTile(
                          title: 'Sticky in navigation',
                          subtitle:
                              'Show this section in side navigation and progress.',
                          value: section.showInNavigation,
                          onChanged: (val) => controller.updateSection(
                            section.id,
                            showInNavigation: val,
                          ),
                        ),
                        _toggleTile(
                          title: 'Hide title',
                          subtitle:
                              'Keep the content but remove the visible header.',
                          value: section.hideTitle,
                          onChanged: (val) => controller.updateSection(
                            section.id,
                            hideTitle: val,
                          ),
                        ),
                        _toggleTile(
                          title: 'Hide from progress',
                          subtitle:
                              'Keep the section but remove it from progress indicators.',
                          value: section.hideFromProgress,
                          onChanged: (val) => controller.updateSection(
                            section.id,
                            hideFromProgress: val,
                          ),
                        ),
                        _toggleTile(
                          title: 'Lock section',
                          subtitle:
                              'Make this section read-only for non-admin roles.',
                          value: section.lockSection,
                          onChanged: (val) => controller.updateSection(
                            section.id,
                            lockSection: val,
                          ),
                        ),
                        _toggleTile(
                          title: 'Show breadcrumb',
                          subtitle:
                              'Display this section in breadcrumb navigation.',
                          value: section.showBreadcrumb,
                          onChanged: (val) => controller.updateSection(
                            section.id,
                            showBreadcrumb: val,
                          ),
                        ),
                        _toggleTile(
                          title: 'Show progress step',
                          subtitle:
                              'Include this section in step progress markers.',
                          value: section.showProgressStep,
                          onChanged: (val) => controller.updateSection(
                            section.id,
                            showProgressStep: val,
                          ),
                        ),
                        _toggleTile(
                          title: 'Archived',
                          subtitle:
                              'Keep it available in data, but hide from active editing.',
                          value: section.archived,
                          onChanged: (val) => controller.updateSection(
                            section.id,
                            archived: val,
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
                ListView(
                  children: [
                    _groupCard(
                      context,
                      title: 'Structure',
                      children: [
                        TextField(
                          controller: sectionKeyController,
                          decoration: const InputDecoration(
                            labelText: 'Internal key',
                          ),
                          onChanged: (val) => controller.updateSection(
                            section.id,
                            sectionKey: val,
                          ),
                        ),
                        const SizedBox(height: AppSpacing.md),
                        DropdownButtonFormField<String?>(
                          initialValue: section.parentSectionId,
                          decoration: const InputDecoration(
                            labelText: 'Parent section',
                          ),
                          items: [
                            const DropdownMenuItem<String?>(
                              value: null,
                              child: Text('No parent'),
                            ),
                            ...sectionChoices.map(
                              (choice) => DropdownMenuItem<String?>(
                                value: choice.id == section.id
                                    ? null
                                    : choice.id,
                                enabled: choice.id != section.id,
                                child: Text(choice.title),
                              ),
                            ),
                          ],
                          onChanged: (val) => controller.updateSection(
                            section.id,
                            parentSectionId: val,
                          ),
                        ),
                        const SizedBox(height: AppSpacing.md),
                        DropdownButtonFormField<int>(
                          initialValue: section.columns.clamp(1, 3).toInt(),
                          decoration: const InputDecoration(
                            labelText: 'Columns',
                          ),
                          items: const [
                            DropdownMenuItem(value: 1, child: Text('1 column')),
                            DropdownMenuItem(
                              value: 2,
                              child: Text('2 columns'),
                            ),
                            DropdownMenuItem(
                              value: 3,
                              child: Text('3 columns'),
                            ),
                          ],
                          onChanged: (val) => controller.updateSection(
                            section.id,
                            columns: val ?? 1,
                          ),
                        ),
                        const SizedBox(height: AppSpacing.md),
                        DropdownButtonFormField<String>(
                          initialValue: section.density,
                          decoration: const InputDecoration(
                            labelText: 'Density',
                          ),
                          items: const [
                            DropdownMenuItem(
                              value: 'compact',
                              child: Text('Compact'),
                            ),
                            DropdownMenuItem(
                              value: 'normal',
                              child: Text('Normal'),
                            ),
                            DropdownMenuItem(
                              value: 'spacious',
                              child: Text('Spacious'),
                            ),
                          ],
                          onChanged: (val) => controller.updateSection(
                            section.id,
                            density: val ?? 'normal',
                          ),
                        ),
                        const SizedBox(height: AppSpacing.md),
                        DropdownButtonFormField<String>(
                          initialValue: section.displayMode,
                          decoration: const InputDecoration(
                            labelText: 'Display mode',
                          ),
                          items: const [
                            DropdownMenuItem(
                              value: 'plain',
                              child: Text('Plain'),
                            ),
                            DropdownMenuItem(
                              value: 'card',
                              child: Text('Card'),
                            ),
                            DropdownMenuItem(
                              value: 'divider',
                              child: Text('Divider'),
                            ),
                          ],
                          onChanged: (val) => controller.updateSection(
                            section.id,
                            displayMode: val ?? 'plain',
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: AppSpacing.md),
                    _groupCard(
                      context,
                      title: 'Workflow',
                      children: [
                        DropdownButtonFormField<String>(
                          initialValue: section.accessLevel ?? 'editor',
                          decoration: const InputDecoration(
                            labelText: 'Access level',
                          ),
                          items: const [
                            DropdownMenuItem(
                              value: 'viewer',
                              child: Text('Viewer'),
                            ),
                            DropdownMenuItem(
                              value: 'editor',
                              child: Text('Editor'),
                            ),
                            DropdownMenuItem(
                              value: 'reviewer',
                              child: Text('Reviewer'),
                            ),
                            DropdownMenuItem(
                              value: 'admin',
                              child: Text('Admin'),
                            ),
                          ],
                          onChanged: (val) => controller.updateSection(
                            section.id,
                            accessLevel: val,
                          ),
                        ),
                        const SizedBox(height: AppSpacing.md),
                        _toggleTile(
                          title: 'Approval required',
                          subtitle:
                              'Require approval before the section can be finalized.',
                          value: section.approvalRequired,
                          onChanged: (val) => controller.updateSection(
                            section.id,
                            approvalRequired: val,
                          ),
                        ),
                        const SizedBox(height: AppSpacing.md),
                        TextField(
                          controller: skipToController,
                          decoration: const InputDecoration(
                            labelText: 'Skip to section',
                            hintText: 'sec_2',
                          ),
                          onChanged: (val) => controller.updateSection(
                            section.id,
                            skipToSectionId: val.isEmpty ? null : val,
                          ),
                        ),
                        const SizedBox(height: AppSpacing.md),
                        TextField(
                          controller: visibilityRuleController,
                          decoration: const InputDecoration(
                            labelText: 'Visibility rule',
                            hintText: 'Show when age > 18',
                          ),
                          minLines: 2,
                          maxLines: 3,
                          onChanged: (val) => controller.updateSection(
                            section.id,
                            visibilityRule: val.isEmpty ? null : val,
                          ),
                        ),
                        const SizedBox(height: AppSpacing.md),
                        TextField(
                          controller: notesController,
                          decoration: const InputDecoration(
                            labelText: 'Advanced notes',
                            hintText: 'Internal implementation notes',
                          ),
                          minLines: 2,
                          maxLines: 4,
                          onChanged: (val) => controller.updateSection(
                            section.id,
                            notes: val.isEmpty ? null : val,
                          ),
                        ),
                        const SizedBox(height: AppSpacing.md),
                        TextField(
                          controller: validationSummaryController,
                          decoration: const InputDecoration(
                            labelText: 'Validation summary',
                            hintText: 'Must answer 3 of 5 questions',
                          ),
                          minLines: 2,
                          maxLines: 4,
                          onChanged: (val) => controller.updateSection(
                            section.id,
                            validationSummary: val.isEmpty ? null : val,
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: AppSpacing.md),
                    _groupCard(
                      context,
                      title: 'Analytics',
                      children: [
                        _toggleTile(
                          title: 'Track open',
                          subtitle: 'Measure when this section is opened.',
                          value: section.trackOpen,
                          onChanged: (val) => controller.updateSection(
                            section.id,
                            trackOpen: val,
                          ),
                        ),
                        _toggleTile(
                          title: 'Track completion time',
                          subtitle: 'Measure how long users spend here.',
                          value: section.trackCompletionTime,
                          onChanged: (val) => controller.updateSection(
                            section.id,
                            trackCompletionTime: val,
                          ),
                        ),
                        const SizedBox(height: AppSpacing.md),
                        TextField(
                          controller: analyticsTagController,
                          decoration: const InputDecoration(
                            labelText: 'Analytics tag',
                            hintText: 'intake-step-1',
                          ),
                          onChanged: (val) => controller.updateSection(
                            section.id,
                            analyticsTag: val.isEmpty ? null : val,
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: AppSpacing.md),
                    _groupCard(
                      context,
                      title: 'Actions',
                      children: [
                        Wrap(
                          spacing: AppSpacing.sm,
                          runSpacing: AppSpacing.sm,
                          children: [
                            FilledButton.tonalIcon(
                              onPressed: () =>
                                  controller.duplicateSection(section.id),
                              icon: const Icon(Icons.copy),
                              label: const Text('Duplicate'),
                            ),
                            OutlinedButton.icon(
                              onPressed: () =>
                                  controller.moveSection(section.id, -1),
                              icon: const Icon(Icons.arrow_upward),
                              label: const Text('Move up'),
                            ),
                            OutlinedButton.icon(
                              onPressed: () =>
                                  controller.moveSection(section.id, 1),
                              icon: const Icon(Icons.arrow_downward),
                              label: const Text('Move down'),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ],
                ),
                ListView(
                  children: [
                    _groupCard(
                      context,
                      title: 'Visuals',
                      children: [
                        TextField(
                          controller: backgroundController,
                          decoration: const InputDecoration(
                            labelText: 'Background color',
                          ),
                          onChanged: (val) => controller.updateSection(
                            section.id,
                            backgroundColor: val.isEmpty ? null : val,
                          ),
                        ),
                        const SizedBox(height: AppSpacing.md),
                        TextField(
                          controller: accentController,
                          decoration: const InputDecoration(
                            labelText: 'Accent color',
                          ),
                          onChanged: (val) => controller.updateSection(
                            section.id,
                            accentColor: val.isEmpty ? null : val,
                          ),
                        ),
                        const SizedBox(height: AppSpacing.md),
                        TextField(
                          controller: headerImageController,
                          decoration: const InputDecoration(
                            labelText: 'Header image URL',
                          ),
                          onChanged: (val) => controller.updateSection(
                            section.id,
                            headerImage: val.isEmpty ? null : val,
                          ),
                        ),
                        const SizedBox(height: AppSpacing.md),
                        TextField(
                          controller: cssClassController,
                          decoration: const InputDecoration(
                            labelText: 'CSS class',
                            hintText: 'section-intake',
                          ),
                          onChanged: (val) => controller.updateSection(
                            section.id,
                            cssClass: val.isEmpty ? null : val,
                          ),
                        ),
                        const SizedBox(height: AppSpacing.md),
                        TextField(
                          controller: visibleToController,
                          decoration: const InputDecoration(
                            labelText: 'Visible to roles',
                            hintText: 'admin, reviewer',
                          ),
                          onChanged: (val) => controller.updateSection(
                            section.id,
                            visibleToRoles: val
                                .split(',')
                                .map((e) => e.trim())
                                .where((e) => e.isNotEmpty)
                                .toList(),
                          ),
                        ),
                        const SizedBox(height: AppSpacing.md),
                        TextField(
                          controller: editableByController,
                          decoration: const InputDecoration(
                            labelText: 'Editable by roles',
                            hintText: 'admin',
                          ),
                          onChanged: (val) => controller.updateSection(
                            section.id,
                            editableByRoles: val
                                .split(',')
                                .map((e) => e.trim())
                                .where((e) => e.isNotEmpty)
                                .toList(),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: AppSpacing.md),
                    _groupCard(
                      context,
                      title: 'Template',
                      children: [
                        _toggleTile(
                          title: 'Use as template',
                          subtitle:
                              'Mark this section as reusable for new forms.',
                          value: section.isTemplate,
                          onChanged: (val) => controller.updateSection(
                            section.id,
                            isTemplate: val,
                          ),
                        ),
                        const SizedBox(height: AppSpacing.md),
                        TextField(
                          controller: templateNameController,
                          decoration: const InputDecoration(
                            labelText: 'Template name',
                            hintText: 'Intake template',
                          ),
                          onChanged: (val) => controller.updateSection(
                            section.id,
                            templateName: val.isEmpty ? null : val,
                            isTemplate: val.isNotEmpty,
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
                ListView(
                  children: [
                    _groupCard(
                      context,
                      title: 'Logic',
                      children: [
                        const Text(
                          'Use visibility rules and skip targets to shape flow.',
                        ),
                        const SizedBox(height: AppSpacing.md),
                        TextField(
                          controller: visibilityRuleController,
                          decoration: const InputDecoration(
                            labelText: 'Rule summary',
                            hintText: 'Show when ...',
                          ),
                          minLines: 2,
                          maxLines: 4,
                          onChanged: (val) => controller.updateSection(
                            section.id,
                            visibilityRule: val.isEmpty ? null : val,
                          ),
                        ),
                        const SizedBox(height: AppSpacing.md),
                        TextField(
                          controller: skipToController,
                          decoration: const InputDecoration(
                            labelText: 'Skip target section',
                          ),
                          onChanged: (val) => controller.updateSection(
                            section.id,
                            skipToSectionId: val.isEmpty ? null : val,
                          ),
                        ),
                        const SizedBox(height: AppSpacing.md),
                        TextField(
                          controller: visibilityRuleController,
                          decoration: const InputDecoration(
                            labelText: 'Rule summary',
                            hintText: 'Show when ...',
                          ),
                          minLines: 2,
                          maxLines: 4,
                          onChanged: (val) => controller.updateSection(
                            section.id,
                            visibilityRule: val.isEmpty ? null : val,
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _SubSectionEditor extends StatelessWidget {
  final FormSubSection subSection;
  final TextEditingController titleController;

  const _SubSectionEditor({
    required this.subSection,
    required this.titleController,
  });

  @override
  Widget build(BuildContext context) {
    final controller = context.findAncestorStateOfType<_PropertiesPanelState>();
    if (controller == null) return const SizedBox.shrink();
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _sectionHeader(context, 'Sub-section properties'),
        const SizedBox(height: AppSpacing.md),
        TextField(
          controller: titleController,
          decoration: const InputDecoration(labelText: 'Sub-section title'),
          onChanged: (val) => controller.ref
              .read(formBuilderProvider.notifier)
              .updateSubSection(subSection.id, title: val),
        ),
        const SizedBox(height: AppSpacing.md),
        SwitchListTile(
          contentPadding: EdgeInsets.zero,
          title: const Text('Repeatable sub-section'),
          value: subSection.repeatable,
          onChanged: (val) => controller.ref
              .read(formBuilderProvider.notifier)
              .updateSubSection(subSection.id, repeatable: val),
        ),
      ],
    );
  }
}

class _QuestionEditor extends StatelessWidget {
  final FormQuestion question;
  final TextEditingController labelController;
  final TextEditingController descriptionController;
  final TextEditingController placeholderController;
  final TextEditingController optionsController;

  const _QuestionEditor({
    required this.question,
    required this.labelController,
    required this.descriptionController,
    required this.placeholderController,
    required this.optionsController,
  });

  @override
  Widget build(BuildContext context) {
    final controller = context.findAncestorStateOfType<_PropertiesPanelState>();
    if (controller == null) return const SizedBox.shrink();
    final showOptions =
        question.type == 'dropdown' || question.type == 'multi_select';
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _sectionHeader(context, 'Field properties'),
        const SizedBox(height: AppSpacing.md),
        TextField(
          controller: labelController,
          decoration: const InputDecoration(labelText: 'Field label'),
          onChanged: (val) => controller.ref
              .read(formBuilderProvider.notifier)
              .updateQuestion(question.id, label: val),
        ),
        const SizedBox(height: AppSpacing.md),
        TextField(
          controller: descriptionController,
          decoration: const InputDecoration(labelText: 'Description or hint'),
          onChanged: (val) => controller.ref
              .read(formBuilderProvider.notifier)
              .updateQuestion(question.id, description: val),
        ),
        const SizedBox(height: AppSpacing.md),
        SwitchListTile(
          contentPadding: EdgeInsets.zero,
          title: const Text('Required field'),
          value: question.required,
          onChanged: (val) => controller.ref
              .read(formBuilderProvider.notifier)
              .updateQuestion(question.id, required: val),
        ),
        const SizedBox(height: AppSpacing.md),
        TextField(
          controller: placeholderController,
          decoration: const InputDecoration(labelText: 'Placeholder hint'),
          onChanged: (val) {
            final props = Map<String, dynamic>.from(question.properties);
            props['placeholder'] = val;
            controller.ref
                .read(formBuilderProvider.notifier)
                .updateQuestion(question.id, properties: props);
          },
        ),
        if (showOptions) ...[
          const SizedBox(height: AppSpacing.md),
          Text(
            'Options list',
            style: Theme.of(
              context,
            ).textTheme.labelLarge?.copyWith(fontWeight: FontWeight.w700),
          ),
          const SizedBox(height: AppSpacing.xs),
          TextField(
            controller: optionsController,
            decoration: const InputDecoration(
              hintText: 'e.g. Male, Female, Other',
            ),
            onChanged: (val) {
              final parts = val
                  .split(',')
                  .map((e) => e.trim())
                  .where((e) => e.isNotEmpty)
                  .toList();
              final props = Map<String, dynamic>.from(question.properties);
              props['options'] = [
                for (final p in parts)
                  {'value': p.toLowerCase().replaceAll(' ', '_'), 'label': p},
              ];
              controller.ref
                  .read(formBuilderProvider.notifier)
                  .updateQuestion(question.id, properties: props);
            },
          ),
        ],
      ],
    );
  }
}

class _SubSectionCard extends StatelessWidget {
  final FormSubSection subSection;
  final ValueChanged<String> onTitleChanged;
  final ValueChanged<bool> onRepeatableChanged;
  final VoidCallback onDelete;

  const _SubSectionCard({
    required this.subSection,
    required this.onTitleChanged,
    required this.onRepeatableChanged,
    required this.onDelete,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(AppSpacing.md),
      decoration: BoxDecoration(
        color: Theme.of(
          context,
        ).colorScheme.surfaceContainerHighest.withValues(alpha: 0.45),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: AppColors.builderDivider),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  subSection.title,
                  style: Theme.of(
                    context,
                  ).textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w800),
                ),
              ),
              IconButton(
                tooltip: 'Delete sub-section',
                onPressed: onDelete,
                icon: const Icon(Icons.delete_outline),
              ),
            ],
          ),
          const SizedBox(height: AppSpacing.sm),
          TextField(
            controller: TextEditingController(text: subSection.title)
              ..selection = TextSelection.collapsed(
                offset: subSection.title.length,
              ),
            decoration: const InputDecoration(labelText: 'Sub-section title'),
            onChanged: onTitleChanged,
          ),
          const SizedBox(height: AppSpacing.sm),
          SwitchListTile(
            contentPadding: EdgeInsets.zero,
            title: const Text('Repeatable sub-section'),
            value: subSection.repeatable,
            onChanged: onRepeatableChanged,
          ),
        ],
      ),
    );
  }
}

class _InfoChip extends StatelessWidget {
  final String label;

  const _InfoChip({required this.label});

  @override
  Widget build(BuildContext context) {
    return Chip(
      label: Text(label),
      visualDensity: VisualDensity.compact,
      side: const BorderSide(color: AppColors.builderDivider),
      backgroundColor: Theme.of(context).colorScheme.surfaceContainerHighest,
    );
  }
}

Widget _groupCard(
  BuildContext context, {
  required String title,
  required List<Widget> children,
}) {
  return Container(
    width: double.infinity,
    padding: const EdgeInsets.all(AppSpacing.md),
    decoration: BoxDecoration(
      color: Theme.of(context).colorScheme.surface,
      borderRadius: BorderRadius.circular(12),
      border: Border.all(color: AppColors.builderDivider),
    ),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _sectionHeader(context, title),
        const SizedBox(height: AppSpacing.md),
        ...children,
      ],
    ),
  );
}

Widget _sectionHeader(BuildContext context, String title) {
  return Text(
    title,
    style: Theme.of(
      context,
    ).textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w800),
  );
}

Widget _toggleTile({
  required String title,
  required String subtitle,
  required bool value,
  required ValueChanged<bool> onChanged,
}) {
  return SwitchListTile(
    contentPadding: EdgeInsets.zero,
    title: Text(title),
    subtitle: Text(subtitle),
    value: value,
    onChanged: onChanged,
  );
}
