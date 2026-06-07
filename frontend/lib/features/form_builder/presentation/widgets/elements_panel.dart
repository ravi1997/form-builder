import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../providers/form_builder_provider.dart';

class ElementsPanel extends ConsumerWidget {
  final String activeSubSectionId;

  const ElementsPanel({super.key, required this.activeSubSectionId});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final elementTypes = [
      {'type': 'text_input', 'label': 'Text Field', 'icon': Icons.text_fields},
      {'type': 'dropdown', 'label': 'Dropdown Selector', 'icon': Icons.arrow_drop_down_circle},
      {'type': 'date_range_picker', 'label': 'Date Range Picker', 'icon': Icons.date_range},
      {'type': 'multi_select', 'label': 'Multi-Select Options', 'icon': Icons.playlist_add_check},
      {'type': 'rating', 'label': 'Star Rating', 'icon': Icons.star},
      {'type': 'checkbox', 'label': 'Checkbox List Tile', 'icon': Icons.check_box},
      {'type': 'toggle', 'label': 'Switch Toggle', 'icon': Icons.toggle_on},
    ];

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(12.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Add Components',
              style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 8),
            Text(
              'Select a component type below to insert it into the current sub-section.',
              style: Theme.of(context).textTheme.bodySmall,
            ),
            const SizedBox(height: 12),
            Expanded(
              child: ListView.separated(
                itemCount: elementTypes.length,
                separatorBuilder: (context, index) => const Divider(),
                itemBuilder: (context, index) {
                  final el = elementTypes[index];
                  return ListTile(
                    leading: Icon(el['icon'] as IconData, color: Theme.of(context).primaryColor),
                    title: Text(el['label'] as String),
                    dense: true,
                    onTap: () {
                      ref.read(formBuilderProvider.notifier).addQuestion(
                            activeSubSectionId,
                            el['type'] as String,
                          );
                    },
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
