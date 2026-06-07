import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../providers/form_builder_provider.dart';

class PropertiesPanel extends ConsumerWidget {
  const PropertiesPanel({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final builderState = ref.watch(formBuilderProvider);
    final selectedId = builderState.selectedElementId;

    if (selectedId == null) {
      return const Card(
        child: Center(
          child: Text('Select an element in the canvas to edit its properties.'),
        ),
      );
    }

    // Determine what is selected
    FormSection? selectedSec;
    FormSubSection? selectedSub;
    FormQuestion? selectedQ;

    for (final sec in builderState.sections) {
      if (sec.id == selectedId) {
        selectedSec = sec;
        break;
      }
      for (final sub in sec.subSections) {
        if (sub.id == selectedId) {
          selectedSub = sub;
          break;
        }
        for (final q in sub.questions) {
          if (q.id == selectedId) {
            selectedQ = q;
            break;
          }
        }
      }
    }

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(12.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  'Properties Panel',
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold),
                ),
                IconButton(
                  icon: const Icon(Icons.delete, color: Colors.red),
                  onPressed: () {
                    ref.read(formBuilderProvider.notifier).deleteElement(selectedId);
                  },
                ),
              ],
            ),
            const Divider(),
            const SizedBox(height: 8),
            Expanded(
              child: SingleChildScrollView(
                child: Builder(
                  builder: (context) {
                    if (selectedSec != null) {
                      return _buildSectionProperties(context, ref, selectedSec);
                    }
                    if (selectedSub != null) {
                      return _buildSubSectionProperties(context, ref, selectedSub);
                    }
                    if (selectedQ != null) {
                      return _buildQuestionProperties(context, ref, selectedQ);
                    }
                    return const Text('Element details not found.');
                  },
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildSectionProperties(BuildContext context, WidgetRef ref, FormSection sec) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text('Section Properties', style: TextStyle(fontWeight: FontWeight.bold)),
        const SizedBox(height: 12),
        TextField(
          controller: TextEditingController(text: sec.title)..selection = TextSelection.collapsed(offset: sec.title.length),
          decoration: const InputDecoration(labelText: 'Section Title', border: OutlineInputBorder()),
          onChanged: (val) {
            ref.read(formBuilderProvider.notifier).updateSection(sec.id, title: val);
          },
        ),
        const SizedBox(height: 12),
        TextField(
          controller: TextEditingController(text: sec.description)..selection = TextSelection.collapsed(offset: sec.description.length),
          decoration: const InputDecoration(labelText: 'Description', border: OutlineInputBorder()),
          onChanged: (val) {
            ref.read(formBuilderProvider.notifier).updateSection(sec.id, description: val);
          },
        ),
        const SizedBox(height: 12),
        SwitchListTile(
          title: const Text('Repeatable Section'),
          value: sec.repeatable,
          onChanged: (val) {
            ref.read(formBuilderProvider.notifier).updateSection(sec.id, repeatable: val);
          },
        ),
      ],
    );
  }

  Widget _buildSubSectionProperties(BuildContext context, WidgetRef ref, FormSubSection sub) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text('Sub-Section Properties', style: TextStyle(fontWeight: FontWeight.bold)),
        const SizedBox(height: 12),
        TextField(
          controller: TextEditingController(text: sub.title)..selection = TextSelection.collapsed(offset: sub.title.length),
          decoration: const InputDecoration(labelText: 'Sub-Section Title', border: OutlineInputBorder()),
          onChanged: (val) {
            ref.read(formBuilderProvider.notifier).updateSubSection(sub.id, title: val);
          },
        ),
        const SizedBox(height: 12),
        SwitchListTile(
          title: const Text('Repeatable Sub-Section'),
          value: sub.repeatable,
          onChanged: (val) {
            ref.read(formBuilderProvider.notifier).updateSubSection(sub.id, repeatable: val);
          },
        ),
      ],
    );
  }

  Widget _buildQuestionProperties(BuildContext context, WidgetRef ref, FormQuestion q) {
    final placeholderController = TextEditingController(text: q.properties['placeholder']?.toString() ?? '');

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text('Field Properties (${q.type})', style: const TextStyle(fontWeight: FontWeight.bold)),
        const SizedBox(height: 12),
        TextField(
          controller: TextEditingController(text: q.label)..selection = TextSelection.collapsed(offset: q.label.length),
          decoration: const InputDecoration(labelText: 'Field Label', border: OutlineInputBorder()),
          onChanged: (val) {
            ref.read(formBuilderProvider.notifier).updateQuestion(q.id, label: val);
          },
        ),
        const SizedBox(height: 12),
        TextField(
          controller: TextEditingController(text: q.description)..selection = TextSelection.collapsed(offset: q.description.length),
          decoration: const InputDecoration(labelText: 'Description/Hint', border: OutlineInputBorder()),
          onChanged: (val) {
            ref.read(formBuilderProvider.notifier).updateQuestion(q.id, description: val);
          },
        ),
        const SizedBox(height: 12),
        SwitchListTile(
          title: const Text('Required Field'),
          value: q.required,
          onChanged: (val) {
            ref.read(formBuilderProvider.notifier).updateQuestion(q.id, required: val);
          },
        ),
        const SizedBox(height: 12),
        const Text('Primitive Specific Options', style: TextStyle(fontWeight: FontWeight.w600)),
        const SizedBox(height: 8),
        TextField(
          controller: placeholderController..selection = TextSelection.collapsed(offset: placeholderController.text.length),
          decoration: const InputDecoration(labelText: 'Placeholder Hint', border: OutlineInputBorder()),
          onChanged: (val) {
            final props = Map<String, dynamic>.from(q.properties);
            props['placeholder'] = val;
            ref.read(formBuilderProvider.notifier).updateQuestion(q.id, properties: props);
          },
        ),
        if (q.type == 'dropdown' || q.type == 'multi_select') ...[
          const SizedBox(height: 12),
          const Text('Options List (comma separated):', style: TextStyle(fontSize: 12)),
          const SizedBox(height: 6),
          _buildOptionsEditor(context, ref, q),
        ],
      ],
    );
  }

  Widget _buildOptionsEditor(BuildContext context, WidgetRef ref, FormQuestion q) {
    final List<Map<String, dynamic>> opts = [];
    final rawOpts = q.properties['options'];
    if (rawOpts is List) {
      for (final o in rawOpts) {
        if (o is Map) {
          opts.add(Map<String, dynamic>.from(o));
        }
      }
    }

    final valString = opts.map((o) => o['label'] ?? o['value'] ?? '').join(', ');

    return TextField(
      controller: TextEditingController(text: valString)..selection = TextSelection.collapsed(offset: valString.length),
      decoration: const InputDecoration(
        hintText: 'e.g., Male, Female, Other',
        border: OutlineInputBorder(),
      ),
      onChanged: (val) {
        final parts = val.split(',').map((e) => e.trim()).where((e) => e.isNotEmpty).toList();
        final List<Map<String, String>> newOpts = parts.map((e) {
          return {
            'value': e.toLowerCase().replaceAll(' ', '_'),
            'label': e,
          };
        }).toList();

        final props = Map<String, dynamic>.from(q.properties);
        props['options'] = newOpts;
        ref.read(formBuilderProvider.notifier).updateQuestion(q.id, properties: props);
      },
    );
  }
}
