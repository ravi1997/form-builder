import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../../core/theme/theme_presets.dart';
import '../widgets/canvas.dart';
import '../widgets/elements_panel.dart';
import '../widgets/properties_panel.dart';

class FormBuilderPage extends ConsumerStatefulWidget {
  const FormBuilderPage({super.key});

  @override
  ConsumerState<FormBuilderPage> createState() => _FormBuilderPageState();
}

class _FormBuilderPageState extends ConsumerState<FormBuilderPage> {
  String _activeSubSectionId = 'subsec_1';

  @override
  Widget build(BuildContext context) {
    final activeTheme = ref.watch(themePresetProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Dynamic Form Workspace'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.go('/'),
        ),
        backgroundColor: activeTheme.brightness == Brightness.dark
            ? Colors.black.withOpacity(0.4)
            : activeTheme.seedColor.withOpacity(0.1),
        foregroundColor: activeTheme.brightness == Brightness.dark ? Colors.white : Colors.black,
        elevation: 0,
        actions: [
          IconButton(
            icon: const Icon(Icons.help_outline),
            onPressed: () {
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(
                  content: Text('Select active target sub-section first, then insert fields.'),
                ),
              );
            },
          ),
        ],
      ),
      body: Container(
        width: double.infinity,
        height: double.infinity,
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: activeTheme.bgGradient,
          ),
        ),
        padding: const EdgeInsets.all(16.0),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Left Widget Library
            SizedBox(
              width: 280,
              child: ElementsPanel(activeSubSectionId: _activeSubSectionId),
            ),
            const SizedBox(width: 16),
            // Center Canvas Editor
            Expanded(
              child: BuilderCanvas(
                activeSubSectionId: _activeSubSectionId,
                onSubSectionActivated: (id) {
                  setState(() {
                    _activeSubSectionId = id;
                  });
                },
              ),
            ),
            const SizedBox(width: 16),
            // Right Properties Inspector
            const SizedBox(
              width: 320,
              child: PropertiesPanel(),
            ),
          ],
        ),
      ),
    );
  }
}
