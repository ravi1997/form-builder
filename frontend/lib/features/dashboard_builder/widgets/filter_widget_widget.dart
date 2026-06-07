import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/widget_model.dart';
import '../providers/filter_state_provider.dart';

class FilterWidgetWidget extends ConsumerWidget {
  final WidgetModel widget;

  const FilterWidgetWidget({
    super.key,
    required this.widget,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final props = widget.properties;
    final label = props['label'] ?? 'Filter';
    final placeholder = props['placeholder'] ?? 'Select...';
    final filterType = props['filter_type'] ?? 'dropdown';
    final source = props['options_source'] ?? 'static';
    final allowClear = props['allow_clear'] ?? true;
    final clearLabel = props['clear_label'] ?? 'All';

    final activeFilters = ref.watch(filterStateProvider);
    final activeValue = activeFilters[widget.id];

    // Resolve static options
    final List<String> options = List<String>.from(props['static_options'] ?? []);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        Text(
          label,
          style: const TextStyle(fontWeight: FontWeight.w500, fontSize: 13, color: Colors.grey),
        ),
        const SizedBox(height: 4),
        if (filterType == 'dropdown')
          DropdownButtonFormField<String>(
            value: activeValue as String?,
            hint: Text(placeholder),
            decoration: const InputDecoration(
              isDense: true,
              contentPadding: EdgeInsets.symmetric(horizontal: 10, vertical: 8),
              border: OutlineInputBorder(),
            ),
            items: [
              if (allowClear)
                DropdownMenuItem<String>(
                  value: null,
                  child: Text(clearLabel),
                ),
              ...options.map((opt) {
                return DropdownMenuItem<String>(
                  value: opt,
                  child: Text(opt),
                );
              }),
            ],
            onChanged: (val) {
              ref.read(filterStateProvider.notifier).updateFilter(widget.id, val);
            },
          )
        else if (filterType == 'text_search')
          TextField(
            decoration: InputDecoration(
              hintText: placeholder,
              isDense: true,
              contentPadding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
              border: const OutlineInputBorder(),
              suffixIcon: activeValue != null
                  ? IconButton(
                      icon: const Icon(Icons.clear, size: 16),
                      onPressed: () {
                        ref.read(filterStateProvider.notifier).updateFilter(widget.id, null);
                      },
                    )
                  : null,
            ),
            onChanged: (val) {
              ref.read(filterStateProvider.notifier).updateFilter(widget.id, val.isEmpty ? null : val);
            },
          )
        else
          // Fallback simple control for other filters like date_range
          ElevatedButton(
            onPressed: () async {
              if (filterType == 'date_range_picker') {
                final picked = await showDateRangePicker(
                  context: context,
                  firstDate: DateTime(2020),
                  lastDate: DateTime(2030),
                );
                if (picked != null) {
                  ref.read(filterStateProvider.notifier).updateFilter(
                        widget.id,
                        '${picked.start.toIso8601String().substring(0, 10)} to ${picked.end.toIso8601String().substring(0, 10)}',
                      );
                }
              }
            },
            child: Text(activeValue?.toString() ?? placeholder),
          ),
      ],
    );
  }
}
