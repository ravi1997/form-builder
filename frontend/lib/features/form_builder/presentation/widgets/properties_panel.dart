import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/design_system.dart';
import '../../../../core/theme/tokens.dart';
import '../../providers/form_builder_provider.dart';
import '../../../../core/theme/css_injector.dart';
import 'logic_graph_editor.dart';

class PropertiesPanel extends ConsumerStatefulWidget {
  final VoidCallback? onClosePanel;

  const PropertiesPanel({super.key, this.onClosePanel});

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
  final _fieldSlug = TextEditingController();
  final _fieldElevation = TextEditingController();

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
    _fieldSlug.dispose();
    _fieldElevation.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final builderState = ref.watch(formBuilderProvider);
    final selectedId = builderState.selectedElementId;
    final theme = Theme.of(context);

    _syncSelection(builderState.sections, selectedId);

    if (selectedId == null) {
      return const _FormPropertiesEditor();
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
                const SizedBox(width: AppSpacing.xs),
                IconButton.filledTonal(
                  icon: const Icon(Icons.close),
                  tooltip: 'Close properties panel',
                  onPressed: () {
                    ref.read(formBuilderProvider.notifier).selectElement(null);
                    widget.onClosePanel?.call();
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
                          onClosePanel: widget.onClosePanel,
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
                          onClosePanel: widget.onClosePanel,
                          titleController: _subSectionTitle,
                        );
                      }
                      if (_selectedQuestion != null) {
                        return _QuestionEditor(
                          question: _selectedQuestion!,
                          onClosePanel: widget.onClosePanel,
                          labelController: _fieldLabel,
                          descriptionController: _fieldDescription,
                          placeholderController: _fieldPlaceholder,
                          optionsController: _fieldOptions,
                          slugController: _fieldSlug,
                          elevationController: _fieldElevation,
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
    _fieldSlug.text = q.properties['slug']?.toString() ?? q.id;
    _fieldElevation.text = (q.properties['elevation'] ?? 0.0).toString();
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
  final VoidCallback? onClosePanel;
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
    this.onClosePanel,
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
          _headerWithClose(
            context,
            'Section properties',
            onClose: () {
            notifier.ref.read(formBuilderProvider.notifier).selectElement(null);
            onClosePanel?.call();
          },
          ),
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
                    SectionLogicEditor(section: section),
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
  final VoidCallback? onClosePanel;
  final TextEditingController titleController;

  const _SubSectionEditor({
    required this.subSection,
    this.onClosePanel,
    required this.titleController,
  });

  @override
  Widget build(BuildContext context) {
    final controller = context.findAncestorStateOfType<_PropertiesPanelState>();
    if (controller == null) return const SizedBox.shrink();
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _headerWithClose(
          context,
          'Sub-section properties',
          onClose: () {
            controller.ref.read(formBuilderProvider.notifier).selectElement(null);
            onClosePanel?.call();
          },
        ),
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
  final VoidCallback? onClosePanel;
  final TextEditingController labelController;
  final TextEditingController descriptionController;
  final TextEditingController placeholderController;
  final TextEditingController optionsController;
  final TextEditingController slugController;
  final TextEditingController elevationController;

  const _QuestionEditor({
    required this.question,
    this.onClosePanel,
    required this.labelController,
    required this.descriptionController,
    required this.placeholderController,
    required this.optionsController,
    required this.slugController,
    required this.elevationController,
  });

  @override
  Widget build(BuildContext context) {
    final controller = context.findAncestorStateOfType<_PropertiesPanelState>();
    if (controller == null) return const SizedBox.shrink();
    final theme = Theme.of(context);
    final showOptions =
        question.type == 'dropdown' || question.type == 'multi_select';
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _headerWithClose(
          context,
          'Field properties',
          onClose: () {
            controller.ref.read(formBuilderProvider.notifier).selectElement(null);
            onClosePanel?.call();
          },
        ),
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
        Material(
          color: Colors.transparent,
          child: SwitchListTile(
            contentPadding: EdgeInsets.zero,
            title: const Text('Required field'),
            value: question.required,
            onChanged: (val) => controller.ref
                .read(formBuilderProvider.notifier)
                .updateQuestion(question.id, required: val),
          ),
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
        const SizedBox(height: AppSpacing.md),
        Row(
          children: [
            const Expanded(child: Text('Slug Key')),
            const SizedBox(width: 4),
            Tooltip(
              key: const ValueKey('tooltip-slug'),
              message: 'Technical identifier for API and formulas',
              child: Icon(Icons.info_outline, size: 16, color: theme.colorScheme.onSurfaceVariant),
            ),
          ],
        ),
        const SizedBox(height: AppSpacing.xs),
        TextField(
          key: const ValueKey('sidebar-slug-input'),
          controller: slugController,
          decoration: const InputDecoration(labelText: 'Slug'),
          onChanged: (val) {
            final props = Map<String, dynamic>.from(question.properties);
            props['slug'] = val;
            controller.ref.read(formBuilderProvider.notifier).updateQuestion(question.id, properties: props);
          },
        ),
        const SizedBox(height: AppSpacing.md),
        Row(
          children: [
            const Expanded(child: Text('Card Elevation')),
            const SizedBox(width: 4),
            Tooltip(
              key: const ValueKey('tooltip-elevation'),
              message: 'Shadow depth for visual card layout rendering',
              child: Icon(Icons.info_outline, size: 16, color: theme.colorScheme.onSurfaceVariant),
            ),
          ],
        ),
        const SizedBox(height: AppSpacing.xs),
        TextField(
          key: const ValueKey('sidebar-elevation-input'),
          controller: elevationController,
          decoration: const InputDecoration(labelText: 'Elevation'),
          onChanged: (val) {
            final props = Map<String, dynamic>.from(question.properties);
            props['elevation'] = double.tryParse(val) ?? 0.0;
            controller.ref.read(formBuilderProvider.notifier).updateQuestion(question.id, properties: props);
          },
        ),
        const SizedBox(height: AppSpacing.md),
        Row(
          children: [
            const Expanded(child: Text('FLE / PII Encryption')),
            const SizedBox(width: 4),
            Tooltip(
              key: const ValueKey('tooltip-fle-pii'),
              message: 'Encrypt field content at rest to protect sensitive inputs',
              child: Icon(Icons.info_outline, size: 16, color: theme.colorScheme.onSurfaceVariant),
            ),
          ],
        ),
        const SizedBox(height: AppSpacing.xs),
        Material(
          color: Colors.transparent,
          child: SwitchListTile(
            key: const ValueKey('sidebar-fle-pii-switch'),
            contentPadding: EdgeInsets.zero,
            title: const Text('Field Level Encryption / PII'),
            value: question.properties['fle_pii'] == true,
            onChanged: (val) {
              final props = Map<String, dynamic>.from(question.properties);
              props['fle_pii'] = val;
              controller.ref.read(formBuilderProvider.notifier).updateQuestion(question.id, properties: props);
            },
          ),
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

Widget _headerWithClose(
  BuildContext context,
  String title, {
  required VoidCallback onClose,
}) {
  return Row(
    children: [
      Expanded(
        child: Text(
          title,
          style: Theme.of(
            context,
          ).textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w800),
        ),
      ),
      IconButton(
        tooltip: 'Close $title',
        icon: const Icon(Icons.close),
        onPressed: onClose,
      ),
    ],
  );
}

Widget _toggleTile({
  Key? key,
  required String title,
  required String subtitle,
  required bool value,
  required ValueChanged<bool> onChanged,
}) {
  return Material(
    color: Colors.transparent,
    child: SwitchListTile(
      key: key,
      contentPadding: EdgeInsets.zero,
      title: Text(title),
      subtitle: Text(subtitle),
      value: value,
      onChanged: onChanged,
    ),
  );
}

class _FormPropertiesEditor extends ConsumerStatefulWidget {
  const _FormPropertiesEditor();

  @override
  ConsumerState<_FormPropertiesEditor> createState() => _FormPropertiesEditorState();
}

class _FormPropertiesEditorState extends ConsumerState<_FormPropertiesEditor> {
  late TextEditingController _nameController;
  late TextEditingController _descController;
  late TextEditingController _primaryColorController;
  late TextEditingController _bgColorController;
  late TextEditingController _fontFamilyController;
  late TextEditingController _borderRadiusController;
  late TextEditingController _cssController;

  late TextEditingController _emailRecipientsController;
  late TextEditingController _webhookUrlController;
  late TextEditingController _webhookSecretController;
  late TextEditingController _internalUsersController;
  late TextEditingController _internalTeamsController;

  bool _isAdvancedMode = false;

  @override
  void initState() {
    super.initState();
    final state = ref.read(formBuilderProvider);
    _nameController = TextEditingController(text: state.name);
    _descController = TextEditingController(text: state.description);
    _primaryColorController = TextEditingController(text: state.style.primaryColor);
    _bgColorController = TextEditingController(text: state.style.backgroundColor);
    _fontFamilyController = TextEditingController(text: state.style.fontFamily);
    _borderRadiusController = TextEditingController(text: state.style.borderRadius.toString());
    _cssController = TextEditingController(text: state.style.customCss);

    _emailRecipientsController = TextEditingController(text: state.notifications.emailRecipients.join(', '));
    _webhookUrlController = TextEditingController(text: state.notifications.webhookUrl);
    _webhookSecretController = TextEditingController(text: state.notifications.webhookSecret);
    _internalUsersController = TextEditingController(text: state.notifications.internalUserIds.join(', '));
    _internalTeamsController = TextEditingController(text: state.notifications.internalTeamIds.join(', '));
    
    // Inject initial custom CSS
    WidgetsBinding.instance.addPostFrameCallback((_) {
      injectCss(state.style.customCss);
    });
  }

  @override
  void dispose() {
    _nameController.dispose();
    _descController.dispose();
    _primaryColorController.dispose();
    _bgColorController.dispose();
    _fontFamilyController.dispose();
    _borderRadiusController.dispose();
    _cssController.dispose();

    _emailRecipientsController.dispose();
    _webhookUrlController.dispose();
    _webhookSecretController.dispose();
    _internalUsersController.dispose();
    _internalTeamsController.dispose();
    super.dispose();
  }

  void _applyPreset(String id, String name, String primary, String bg, String font, double radius, String input, String css) {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Apply Preset?'),
        content: Text('Are you sure you want to apply the "$name" preset? This will overwrite your current styling configuration.'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () {
              Navigator.pop(ctx);
              ref.read(formBuilderProvider.notifier).updateStyle(
                themeId: id,
                primaryColor: primary,
                backgroundColor: bg,
                fontFamily: font,
                borderRadius: radius,
                inputStyle: input,
                customCss: css,
              );
              setState(() {
                _primaryColorController.text = primary;
                _bgColorController.text = bg;
                _fontFamilyController.text = font;
                _borderRadiusController.text = radius.toString();
                _cssController.text = css;
              });
              injectCss(css);
            },
            child: const Text('Apply'),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final builderState = ref.watch(formBuilderProvider);
    final theme = Theme.of(context);

    bool isValidHexColor(String hex) {
      final regExp = RegExp(r'^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$');
      return regExp.hasMatch(hex);
    }

    ref.listen<FormBuilderState>(formBuilderProvider, (previous, next) {
      if (next.name != _nameController.text) {
        _nameController.text = next.name;
      }
      if (next.description != _descController.text) {
        _descController.text = next.description;
      }
      if (next.style.primaryColor != _primaryColorController.text) {
        _primaryColorController.text = next.style.primaryColor;
      }
      if (next.style.backgroundColor != _bgColorController.text) {
        _bgColorController.text = next.style.backgroundColor;
      }
      if (next.style.fontFamily != _fontFamilyController.text) {
        _fontFamilyController.text = next.style.fontFamily;
      }
      if (next.style.borderRadius.toString() != _borderRadiusController.text) {
        _borderRadiusController.text = next.style.borderRadius.toString();
      }
      if (next.style.customCss != _cssController.text) {
        _cssController.text = next.style.customCss;
      }

      final prevRecipients = previous?.notifications.emailRecipients.join(', ') ?? '';
      final nextRecipients = next.notifications.emailRecipients.join(', ');
      if (nextRecipients != _emailRecipientsController.text && nextRecipients != prevRecipients) {
        _emailRecipientsController.text = nextRecipients;
      }
      if (next.notifications.webhookUrl != _webhookUrlController.text && next.notifications.webhookUrl != (previous?.notifications.webhookUrl ?? '')) {
        _webhookUrlController.text = next.notifications.webhookUrl;
      }
      if (next.notifications.webhookSecret != _webhookSecretController.text && next.notifications.webhookSecret != (previous?.notifications.webhookSecret ?? '')) {
        _webhookSecretController.text = next.notifications.webhookSecret;
      }
      final prevUsers = previous?.notifications.internalUserIds.join(', ') ?? '';
      final nextUsers = next.notifications.internalUserIds.join(', ');
      if (nextUsers != _internalUsersController.text && nextUsers != prevUsers) {
        _internalUsersController.text = nextUsers;
      }
      final prevTeams = previous?.notifications.internalTeamIds.join(', ') ?? '';
      final nextTeams = next.notifications.internalTeamIds.join(', ');
      if (nextTeams != _internalTeamsController.text && nextTeams != prevTeams) {
        _internalTeamsController.text = nextTeams;
      }
    });

    return DefaultTabController(
      length: 4,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _sectionHeader(context, 'Global Form Properties'),
          const SizedBox(height: AppSpacing.sm),
          Text(
            'Modify form settings, apply templates, and style the preview layout.',
            style: theme.textTheme.bodySmall?.copyWith(color: AppColors.textMuted),
          ),
          const SizedBox(height: AppSpacing.md),
          const TabBar(
            tabs: [
              Tab(text: 'General'),
              Tab(text: 'Style'),
              Tab(text: 'Notifications'),
              Tab(text: 'Analytics'),
            ],
          ),
          const SizedBox(height: AppSpacing.md),
          Expanded(
            child: TabBarView(
              children: [
                ListView(
                  children: [
                    _groupCard(
                      context,
                      title: 'Form Details',
                      children: [
                        TextField(
                          controller: _nameController,
                          decoration: const InputDecoration(labelText: 'Form Name'),
                          onChanged: (val) {
                            // update Form Name in provider (could create updateForm metadata method)
                          },
                        ),
                        const SizedBox(height: AppSpacing.md),
                        TextField(
                          controller: _descController,
                          decoration: const InputDecoration(labelText: 'Description'),
                          minLines: 2,
                          maxLines: 4,
                          onChanged: (val) {
                            // update Form Description
                          },
                        ),
                      ],
                    ),
                  ],
                ),
                ListView(
                  children: [
                    SegmentedButton<bool>(
                      segments: const [
                        ButtonSegment(value: false, label: Text('Presets'), icon: Icon(Icons.palette_outlined)),
                        ButtonSegment(value: true, label: Text('Advanced'), icon: Icon(Icons.tune_outlined)),
                      ],
                      selected: {_isAdvancedMode},
                      onSelectionChanged: (val) {
                        setState(() {
                          _isAdvancedMode = val.first;
                        });
                      },
                    ),
                    const SizedBox(height: AppSpacing.md),
                    if (!_isAdvancedMode)
                      _groupCard(
                        context,
                        title: 'Style Presets',
                        children: [
                          _PresetCard(
                            name: 'Sleek Dark',
                            description: 'Premium high-contrast dark theme.',
                            primaryColor: const Color(0xFFBB86FC),
                            backgroundColor: const Color(0xFF121212),
                            isSelected: builderState.style.themeId == 'sleek_dark',
                            onTap: () => _applyPreset(
                              'sleek_dark',
                              'Sleek Dark',
                              '#BB86FC',
                              '#121212',
                              'Inter',
                              8.0,
                              'filled',
                              '/* Sleek Dark Presets */\n.form-container {\n  background-color: #121212;\n  color: #FFFFFF;\n}\n.form-input {\n  background-color: #1E1E1E;\n  color: #FFFFFF;\n  border-color: #BB86FC;\n}',
                            ),
                          ),
                          const SizedBox(height: AppSpacing.sm),
                          _PresetCard(
                            name: 'Glassmorphism',
                            description: 'Modern frosted-glass look.',
                            primaryColor: const Color(0xFFE91E63),
                            backgroundColor: const Color(0xFFF0F3F6),
                            isSelected: builderState.style.themeId == 'glassmorphism',
                            onTap: () => _applyPreset(
                              'glassmorphism',
                              'Glassmorphism',
                              '#E91E63',
                              '#F0F3F6',
                              'Outfit',
                              16.0,
                              'outlined',
                              '/* Glassmorphism Presets */\n.form-container {\n  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);\n}\n.form-card {\n  background: rgba(255, 255, 255, 0.25);\n  backdrop-filter: blur(4px);\n  -webkit-backdrop-filter: blur(4px);\n  border: 1px solid rgba(255, 255, 255, 0.18);\n  border-radius: 16px;\n}',
                            ),
                          ),
                          const SizedBox(height: AppSpacing.sm),
                          _PresetCard(
                            name: 'Warm Professional',
                            description: 'Clean corporate warmth.',
                            primaryColor: const Color(0xFFFF9800),
                            backgroundColor: const Color(0xFFFFFDE7),
                            isSelected: builderState.style.themeId == 'warm_professional',
                            onTap: () => _applyPreset(
                              'warm_professional',
                              'Warm Professional',
                              '#FF9800',
                              '#FFFDE7',
                              'Roboto',
                              4.0,
                              'outlined',
                              '/* Warm Professional Presets */\n.form-container {\n  background-color: #FFFDE7;\n  color: #3E2723;\n}\n.form-input {\n  border-color: #FF9800;\n}',
                            ),
                          ),
                        ],
                      )
                    else ...[
                      _groupCard(
                        context,
                        title: 'Theme Tokens',
                        children: [
                          TextField(
                            key: const ValueKey('sidebar-primary-color-input'),
                            controller: _primaryColorController,
                            decoration: InputDecoration(
                              labelText: 'Primary Color (Hex)',
                              errorText: isValidHexColor(_primaryColorController.text) ? null : 'Invalid hex color (e.g. #3949AB)',
                            ),
                            onChanged: (val) {
                              setState(() {});
                              if (isValidHexColor(val)) {
                                ref.read(formBuilderProvider.notifier).updateStyle(primaryColor: val, clearThemeId: true);
                              }
                            },
                          ),
                          const SizedBox(height: AppSpacing.md),
                          TextField(
                            key: const ValueKey('sidebar-bg-color-input'),
                            controller: _bgColorController,
                            decoration: InputDecoration(
                              labelText: 'Background Color (Hex)',
                              errorText: isValidHexColor(_bgColorController.text) ? null : 'Invalid hex color (e.g. #FFFDF9)',
                            ),
                            onChanged: (val) {
                              setState(() {});
                              if (isValidHexColor(val)) {
                                ref.read(formBuilderProvider.notifier).updateStyle(backgroundColor: val, clearThemeId: true);
                              }
                            },
                          ),
                          const SizedBox(height: AppSpacing.md),
                          TextField(
                            controller: _fontFamilyController,
                            decoration: const InputDecoration(labelText: 'Font Family'),
                            onChanged: (val) {
                              ref.read(formBuilderProvider.notifier).updateStyle(fontFamily: val, clearThemeId: true);
                            },
                          ),
                          const SizedBox(height: AppSpacing.md),
                          Row(
                            children: [
                              const Text('Border Radius'),
                              Expanded(
                                child: Slider(
                                  value: double.tryParse(_borderRadiusController.text) ?? 8.0,
                                  min: 0.0,
                                  max: 24.0,
                                  divisions: 6,
                                  label: _borderRadiusController.text,
                                  onChanged: (val) {
                                    setState(() {
                                      _borderRadiusController.text = val.toString();
                                    });
                                    ref.read(formBuilderProvider.notifier).updateStyle(borderRadius: val, clearThemeId: true);
                                  },
                                ),
                              ),
                            ],
                          ),
                        ],
                      ),
                      const SizedBox(height: AppSpacing.md),
                      _groupCard(
                        context,
                        title: 'Custom CSS (Advanced)',
                        children: [
                          const Text(
                            'Warning: Custom CSS rule changes take effect live, but may distort the layout preview if invalid.',
                            style: TextStyle(color: Colors.amber, fontSize: 11),
                          ),
                          const SizedBox(height: AppSpacing.sm),
                          TextField(
                            controller: _cssController,
                            maxLines: null,
                            minLines: 6,
                            style: const TextStyle(fontFamily: 'monospace', fontSize: 12),
                            decoration: const InputDecoration(
                              hintText: '.form-container {\n  border: 2px solid red;\n}',
                              border: OutlineInputBorder(),
                            ),
                            onChanged: (val) {
                              ref.read(formBuilderProvider.notifier).updateStyle(customCss: val, clearThemeId: true);
                              injectCss(val);
                            },
                          ),
                          const SizedBox(height: AppSpacing.sm),
                          Row(
                            mainAxisAlignment: MainAxisAlignment.end,
                            children: [
                              TextButton.icon(
                                  onPressed: () {
                                    _cssController.clear();
                                    ref.read(formBuilderProvider.notifier).updateStyle(customCss: '', clearThemeId: true);
                                    injectCss('');
                                  },
                                  icon: const Icon(Icons.refresh),
                                  label: const Text('Reset CSS'),
                                ),
                              ],
                            )
                          ],
                        ),
                      ],
                    ],
                  ),
                ListView(
                  children: [
                    _groupCard(
                      context,
                      title: 'Email Submission Alerts',
                      children: [
                        _toggleTile(
                          key: const ValueKey('notifications-email-switch'),
                          title: 'Enable Email Alerts',
                          subtitle: 'Send email notifications on submission.',
                          value: builderState.notifications.emailEnabled,
                          onChanged: (val) {
                            ref.read(formBuilderProvider.notifier).updateNotifications(emailEnabled: val);
                          },
                        ),
                        if (builderState.notifications.emailEnabled) ...[
                          const SizedBox(height: AppSpacing.md),
                          DropdownButtonFormField<String>(
                            key: const ValueKey('notifications-email-trigger-dropdown'),
                            isExpanded: true,
                            value: builderState.notifications.emailTriggerEvent,
                            decoration: const InputDecoration(labelText: 'Trigger Event'),
                            items: const [
                              DropdownMenuItem(value: 'on_submission', child: Text('On Submission')),
                              DropdownMenuItem(value: 'on_first_save', child: Text('On First Save')),
                            ],
                            onChanged: (val) {
                              if (val != null) {
                                ref.read(formBuilderProvider.notifier).updateNotifications(emailTriggerEvent: val);
                              }
                            },
                          ),
                          const SizedBox(height: AppSpacing.md),
                          TextField(
                            key: const ValueKey('notifications-email-recipients-input'),
                            controller: _emailRecipientsController,
                            decoration: const InputDecoration(
                              labelText: 'Recipients Emails',
                              hintText: 'user@example.com, admin@company.org',
                            ),
                            onChanged: (val) {
                              final list = val.split(',').map((e) => e.trim()).where((e) => e.isNotEmpty).toList();
                              ref.read(formBuilderProvider.notifier).updateNotifications(emailRecipients: list);
                            },
                          ),
                          const SizedBox(height: AppSpacing.md),
                          _toggleTile(
                            key: const ValueKey('notifications-email-payload-switch'),
                            title: 'Include Full Payload',
                            subtitle: 'Send all responses inside the email.',
                            value: builderState.notifications.emailIncludePayload,
                            onChanged: (val) {
                              ref.read(formBuilderProvider.notifier).updateNotifications(emailIncludePayload: val);
                            },
                          ),
                          const SizedBox(height: AppSpacing.sm),
                          _toggleTile(
                            key: const ValueKey('notifications-email-attachments-switch'),
                            title: 'Include File Attachments',
                            subtitle: 'Attach uploaded documents to emails.',
                            value: builderState.notifications.emailIncludeAttachments,
                            onChanged: (val) {
                              ref.read(formBuilderProvider.notifier).updateNotifications(emailIncludeAttachments: val);
                            },
                          ),
                          const SizedBox(height: AppSpacing.sm),
                          const Padding(
                            padding: EdgeInsets.symmetric(horizontal: AppSpacing.sm),
                            child: Text(
                              'Warning: Payload content contains unencrypted fields. Enable PII redaction to protect sensitive answers.',
                              style: TextStyle(color: Colors.amber, fontSize: 11, fontWeight: FontWeight.w500),
                            ),
                          ),
                        ],
                      ],
                    ),
                    const SizedBox(height: AppSpacing.md),
                    _groupCard(
                      context,
                      title: 'Simple Webhook Delivery',
                      children: [
                        _toggleTile(
                          key: const ValueKey('notifications-webhook-switch'),
                          title: 'Enable Webhook Delivery',
                          subtitle: 'POST submission data to a target URL.',
                          value: builderState.notifications.webhookEnabled,
                          onChanged: (val) {
                            ref.read(formBuilderProvider.notifier).updateNotifications(webhookEnabled: val);
                          },
                        ),
                        if (builderState.notifications.webhookEnabled) ...[
                          const SizedBox(height: AppSpacing.md),
                          TextField(
                            key: const ValueKey('notifications-webhook-url-input'),
                            controller: _webhookUrlController,
                            decoration: const InputDecoration(
                              labelText: 'Target URL',
                              hintText: 'https://api.receiver.com/v1/intake',
                            ),
                            onChanged: (val) {
                              ref.read(formBuilderProvider.notifier).updateNotifications(webhookUrl: val);
                            },
                          ),
                          const SizedBox(height: AppSpacing.md),
                          TextField(
                            key: const ValueKey('notifications-webhook-secret-input'),
                            controller: _webhookSecretController,
                            obscureText: true,
                            decoration: const InputDecoration(
                              labelText: 'Webhook Secret',
                              hintText: 'HMAC SHA256 Signing Key',
                            ),
                            onChanged: (val) {
                              ref.read(formBuilderProvider.notifier).updateNotifications(webhookSecret: val);
                            },
                          ),
                          const SizedBox(height: AppSpacing.md),
                          DropdownButtonFormField<String>(
                            key: const ValueKey('notifications-webhook-contenttype-dropdown'),
                            isExpanded: true,
                            value: builderState.notifications.webhookContentType,
                            decoration: const InputDecoration(labelText: 'Content Type'),
                            items: const [
                              DropdownMenuItem(value: 'application/json', child: Text('application/json')),
                              DropdownMenuItem(value: 'application/x-www-form-urlencoded', child: Text('application/x-www-form-urlencoded')),
                            ],
                            onChanged: (val) {
                              if (val != null) {
                                ref.read(formBuilderProvider.notifier).updateNotifications(webhookContentType: val);
                              }
                            },
                          ),
                        ],
                      ],
                    ),
                    const SizedBox(height: AppSpacing.md),
                    _groupCard(
                      context,
                      title: 'Internal Recipients List',
                      children: [
                        _toggleTile(
                          key: const ValueKey('notifications-internal-switch'),
                          title: 'Enable Platform Alerts',
                          subtitle: 'Alert workspace members in-app.',
                          value: builderState.notifications.internalEnabled,
                          onChanged: (val) {
                            ref.read(formBuilderProvider.notifier).updateNotifications(internalEnabled: val);
                          },
                        ),
                        if (builderState.notifications.internalEnabled) ...[
                          const SizedBox(height: AppSpacing.md),
                          TextField(
                            key: const ValueKey('notifications-internal-users-input'),
                            controller: _internalUsersController,
                            decoration: const InputDecoration(
                              labelText: 'Recipient User IDs',
                              hintText: 'Comma separated 24-character ObjectIDs',
                            ),
                            onChanged: (val) {
                              final list = val.split(',').map((e) => e.trim()).where((e) => e.isNotEmpty).toList();
                              ref.read(formBuilderProvider.notifier).updateNotifications(internalUserIds: list);
                            },
                          ),
                          const SizedBox(height: AppSpacing.md),
                          TextField(
                            key: const ValueKey('notifications-internal-teams-input'),
                            controller: _internalTeamsController,
                            decoration: const InputDecoration(
                              labelText: 'Recipient Team IDs',
                              hintText: 'team_sales, team_support',
                            ),
                            onChanged: (val) {
                              final list = val.split(',').map((e) => e.trim()).where((e) => e.isNotEmpty).toList();
                              ref.read(formBuilderProvider.notifier).updateNotifications(internalTeamIds: list);
                            },
                          ),
                        ],
                      ],
                    ),
                    const SizedBox(height: AppSpacing.md),
                    _groupCard(
                      context,
                      title: 'Failure Handling & Resiliency',
                      children: [
                        Row(
                          children: [
                            const Text('Retry Attempts'),
                            Expanded(
                              child: Slider(
                                key: const ValueKey('notifications-failure-retry-slider'),
                                value: builderState.notifications.retryAttempts.toDouble(),
                                min: 0,
                                max: 5,
                                divisions: 5,
                                label: builderState.notifications.retryAttempts.toString(),
                                onChanged: (val) {
                                  ref.read(formBuilderProvider.notifier).updateNotifications(retryAttempts: val.toInt());
                                },
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: AppSpacing.sm),
                        _toggleTile(
                          key: const ValueKey('notifications-failure-alert-switch'),
                          title: 'Alert Owner on Failure',
                          subtitle: 'Send system notification if delivery fails.',
                          value: builderState.notifications.alertOwnerOnFailure,
                          onChanged: (val) {
                            ref.read(formBuilderProvider.notifier).updateNotifications(alertOwnerOnFailure: val);
                          },
                        ),
                      ],
                    ),
                    const SizedBox(height: AppSpacing.xl),
                  ],
                ),
                ListView(
                  children: [
                    _groupCard(
                      context,
                      title: 'Event Tracking',
                      children: [
                        _toggleTile(
                          key: const ValueKey('analytics-enabled-switch'),
                          title: 'Enable Analytics Collection',
                          subtitle: 'Measure form interaction and metrics.',
                          value: builderState.analytics.enabled,
                          onChanged: (val) {
                            ref.read(formBuilderProvider.notifier).updateAnalytics(enabled: val);
                          },
                        ),
                        if (builderState.analytics.enabled) ...[
                          const SizedBox(height: AppSpacing.md),
                          DropdownButtonFormField<String>(
                            key: const ValueKey('analytics-start-event-dropdown'),
                            isExpanded: true,
                            value: builderState.analytics.startEventType,
                            decoration: const InputDecoration(labelText: 'Start Event Condition'),
                            items: const [
                              DropdownMenuItem(value: 'form_load', child: Text('Form Loaded (Initial Page Open)')),
                              DropdownMenuItem(value: 'first_interaction', child: Text('First Interaction (Click or Keypress)')),
                              DropdownMenuItem(value: 'first_input', child: Text('First Input (Data Entry Begun)')),
                            ],
                            onChanged: (val) {
                              if (val != null) {
                                ref.read(formBuilderProvider.notifier).updateAnalytics(startEventType: val);
                              }
                            },
                          ),
                          const SizedBox(height: AppSpacing.md),
                          DropdownButtonFormField<String>(
                            key: const ValueKey('analytics-end-event-dropdown'),
                            isExpanded: true,
                            value: builderState.analytics.endEventType,
                            decoration: const InputDecoration(labelText: 'End Event Condition'),
                            items: const [
                              DropdownMenuItem(value: 'submit_success', child: Text('Successful Submission')),
                              DropdownMenuItem(value: 'submit_attempt', child: Text('Submission Attempt (Click Submit)')),
                            ],
                            onChanged: (val) {
                              if (val != null) {
                                ref.read(formBuilderProvider.notifier).updateAnalytics(endEventType: val);
                              }
                            },
                          ),
                        ],
                      ],
                    ),
                    const SizedBox(height: AppSpacing.md),
                    _groupCard(
                      context,
                      title: 'Measurement & Attribution',
                      children: [
                        _toggleTile(
                          key: const ValueKey('analytics-drop-off-switch'),
                          title: 'Drop-off Tracking',
                          subtitle: 'Log section exits and abandonment points.',
                          value: builderState.analytics.dropOffEnabled,
                          onChanged: (val) {
                            ref.read(formBuilderProvider.notifier).updateAnalytics(dropOffEnabled: val);
                          },
                        ),
                        const SizedBox(height: AppSpacing.md),
                        _toggleTile(
                          key: const ValueKey('analytics-timing-switch'),
                          title: 'Timing Metrics',
                          subtitle: 'Measure average time-to-complete.',
                          value: builderState.analytics.timingEnabled,
                          onChanged: (val) {
                            ref.read(formBuilderProvider.notifier).updateAnalytics(timingEnabled: val);
                          },
                        ),
                        const SizedBox(height: AppSpacing.md),
                        _toggleTile(
                          key: const ValueKey('analytics-utm-capture-switch'),
                          title: 'Attribution / UTM Source Capture',
                          subtitle: 'Extract marketing attribution query parameters.',
                          value: builderState.analytics.utmCaptureEnabled,
                          onChanged: (val) {
                            ref.read(formBuilderProvider.notifier).updateAnalytics(utmCaptureEnabled: val);
                          },
                        ),
                      ],
                    ),
                    const SizedBox(height: AppSpacing.xl),
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

class _PresetCard extends StatelessWidget {
  final String name;
  final String description;
  final Color primaryColor;
  final Color backgroundColor;
  final bool isSelected;
  final VoidCallback onTap;

  const _PresetCard({
    required this.name,
    required this.description,
    required this.primaryColor,
    required this.backgroundColor,
    required this.isSelected,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(10),
      child: Container(
        padding: const EdgeInsets.all(AppSpacing.md),
        decoration: BoxDecoration(
          color: isSelected ? AppColors.brandPrimarySoft.withValues(alpha: 0.2) : Colors.transparent,
          borderRadius: BorderRadius.circular(10),
          border: Border.all(
            color: isSelected ? AppColors.brandPrimary : AppColors.builderDivider,
            width: isSelected ? 2 : 1,
          ),
        ),
        child: Row(
          children: [
            Container(
              width: 32,
              height: 32,
              decoration: BoxDecoration(
                color: backgroundColor,
                borderRadius: BorderRadius.circular(6),
                border: Border.all(color: AppColors.builderDivider),
              ),
              child: Center(
                child: Container(
                  width: 12,
                  height: 12,
                  decoration: BoxDecoration(
                    color: primaryColor,
                    shape: BoxShape.circle,
                  ),
                ),
              ),
            ),
            const SizedBox(width: AppSpacing.md),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    name,
                    style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    description,
                    style: TextStyle(color: AppColors.textMuted, fontSize: 11),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
