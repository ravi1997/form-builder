import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../providers/form_builder_provider.dart';

class BuilderCanvas extends ConsumerWidget {
  final String? activeSubSectionId;
  final void Function(String) onSubSectionActivated;

  const BuilderCanvas({
    super.key,
    required this.activeSubSectionId,
    required this.onSubSectionActivated,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final builderState = ref.watch(formBuilderProvider);
    final theme = Theme.of(context);

    return Card(
      elevation: 2,
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  'Form Canvas',
                  style: theme.textTheme.titleLarge?.copyWith(fontWeight: FontWeight.bold),
                ),
                ElevatedButton.icon(
                  onPressed: () {
                    ref.read(formBuilderProvider.notifier).addSection();
                  },
                  icon: const Icon(Icons.add),
                  label: const Text('Add Section'),
                ),
              ],
            ),
            const SizedBox(height: 16),
            Expanded(
              child: ListView.builder(
                itemCount: builderState.sections.length,
                itemBuilder: (context, sIndex) {
                  final section = builderState.sections[sIndex];
                  final isSelectedSec = builderState.selectedElementId == section.id;

                  return Card(
                    color: isSelectedSec ? theme.colorScheme.primaryContainer.withOpacity(0.3) : null,
                    margin: const EdgeInsets.symmetric(vertical: 8.0),
                    shape: RoundedRectangleBorder(
                      side: BorderSide(
                        color: isSelectedSec ? theme.colorScheme.primary : Colors.grey[300]!,
                        width: isSelectedSec ? 2 : 1,
                      ),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Padding(
                      padding: const EdgeInsets.all(12.0),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            mainAxisAlignment: MainAxisAlignment.spaceBetween,
                            children: [
                              Expanded(
                                child: ListTile(
                                  title: Text(
                                    section.title,
                                    style: theme.textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold),
                                  ),
                                  subtitle: Text(section.description.isNotEmpty ? section.description : 'No description'),
                                  onTap: () {
                                    ref.read(formBuilderProvider.notifier).selectElement(section.id);
                                  },
                                ),
                              ),
                              ElevatedButton.icon(
                                onPressed: () {
                                  ref.read(formBuilderProvider.notifier).addSubSection(section.id);
                                },
                                icon: const Icon(Icons.add, size: 16),
                                label: const Text('Sub-section'),
                              ),
                            ],
                          ),
                          const Divider(),
                          ...section.subSections.map((subSec) {
                            final isSelectedSub = builderState.selectedElementId == subSec.id;
                            final isActiveSub = activeSubSectionId == subSec.id;

                            return Card(
                              color: isSelectedSub ? theme.colorScheme.secondaryContainer.withOpacity(0.3) : null,
                              margin: const EdgeInsets.symmetric(vertical: 6.0, horizontal: 8.0),
                              shape: RoundedRectangleBorder(
                                side: BorderSide(
                                  color: isActiveSub
                                      ? theme.colorScheme.primary
                                      : (isSelectedSub ? theme.colorScheme.secondary : Colors.grey[200]!),
                                  width: isActiveSub ? 2 : 1,
                                ),
                                borderRadius: BorderRadius.circular(6),
                              ),
                              child: Padding(
                                padding: const EdgeInsets.all(8.0),
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    ListTile(
                                      title: Text(
                                        subSec.title,
                                        style: theme.textTheme.titleSmall?.copyWith(fontWeight: FontWeight.bold),
                                      ),
                                      trailing: isActiveSub
                                          ? const Chip(
                                              label: Text('Active Target', style: TextStyle(fontSize: 10)),
                                              visualDensity: VisualDensity.compact,
                                            )
                                          : OutlinedButton(
                                              onPressed: () => onSubSectionActivated(subSec.id),
                                              child: const Text('Set Active', style: TextStyle(fontSize: 10)),
                                            ),
                                      onTap: () {
                                        ref.read(formBuilderProvider.notifier).selectElement(subSec.id);
                                        onSubSectionActivated(subSec.id);
                                      },
                                    ),
                                    const SizedBox(height: 8),
                                    if (subSec.questions.isEmpty)
                                      const Padding(
                                        padding: EdgeInsets.symmetric(vertical: 12.0),
                                        child: Center(
                                          child: Text(
                                            'Empty Sub-section. Add components from the left panel.',
                                            style: TextStyle(fontStyle: FontStyle.italic, fontSize: 12),
                                          ),
                                        ),
                                      )
                                    else
                                      ...subSec.questions.map((q) {
                                        final isSelectedQ = builderState.selectedElementId == q.id;

                                        return Card(
                                          color: isSelectedQ ? theme.colorScheme.tertiaryContainer.withOpacity(0.2) : Colors.grey[50],
                                          margin: const EdgeInsets.symmetric(vertical: 4.0),
                                          shape: RoundedRectangleBorder(
                                            side: BorderSide(
                                              color: isSelectedQ ? theme.colorScheme.tertiary : Colors.grey[300]!,
                                            ),
                                            borderRadius: BorderRadius.circular(4),
                                          ),
                                          child: ListTile(
                                            leading: const Icon(Icons.drag_indicator),
                                            title: Text(q.label),
                                            subtitle: Text(q.description.isNotEmpty ? q.description : 'Type: ${q.type}'),
                                            trailing: q.required ? const Text('* Required', style: TextStyle(color: Colors.red, fontSize: 10)) : null,
                                            onTap: () {
                                              ref.read(formBuilderProvider.notifier).selectElement(q.id);
                                            },
                                          ),
                                        );
                                      }),
                                  ],
                                ),
                              ),
                            );
                          }),
                        ],
                      ),
                    ),
                  );
                },
              ),
            ),
          ],
        ),
      ),
    );
  }
}
