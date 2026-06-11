import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/theme/app_colors.dart';
import '../../../core/theme/design_system.dart';
import '../../../core/theme/tokens.dart';
import '../models/widget_model.dart';
import '../providers/canvas_state_provider.dart';
import 'binding_panel.dart';

class PropertyPanel extends ConsumerStatefulWidget {
  final String dashboardId;

  const PropertyPanel({super.key, required this.dashboardId});

  @override
  ConsumerState<PropertyPanel> createState() => _PropertyPanelState();
}

class _PropertyPanelState extends ConsumerState<PropertyPanel>
    with SingleTickerProviderStateMixin {
  late TabController _tabController;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 3, vsync: this);
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(canvasStateProvider(widget.dashboardId));
    final selectedId = state.selectedWidgetId;
    final theme = Theme.of(context);

    if (selectedId == null) {
      return Container(
        decoration: AppSurfaceStyles.card(),
        child: const Center(
          child: Padding(
            padding: EdgeInsets.all(AppSpacing.lg),
            child: Text(
              'Select a widget to edit its properties, or drag one from the library.',
              textAlign: TextAlign.center,
              style: TextStyle(color: AppColors.textMuted),
            ),
          ),
        ),
      );
    }

    final widgetModel = state.widgets.firstWhere(
      (w) => w.id == selectedId,
      orElse: () => const WidgetModel(
        id: '',
        type: 'none',
        position: WidgetPosition(x: 0, y: 0),
        size: WidgetSize(width: 0, height: 0),
        properties: {},
      ),
    );

    if (widgetModel.id.isEmpty) {
      return const SizedBox.shrink();
    }

    return Container(
      decoration: AppSurfaceStyles.card(),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(
              AppSpacing.lg,
              AppSpacing.lg,
              AppSpacing.lg,
              AppSpacing.sm,
            ),
            child: Row(
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Widget properties',
                        style: theme.textTheme.titleLarge?.copyWith(
                          fontWeight: FontWeight.w800,
                        ),
                      ),
                      const SizedBox(height: AppSpacing.xs),
                      Text(
                        widgetModel.type,
                        style: theme.textTheme.bodySmall?.copyWith(
                          color: AppColors.textMuted,
                        ),
                      ),
                    ],
                  ),
                ),
                IconButton.filledTonal(
                  icon: const Icon(Icons.delete_outline),
                  tooltip: 'Delete widget',
                  onPressed: () {
                    ref
                        .read(canvasStateProvider(widget.dashboardId).notifier)
                        .deleteWidget(widgetModel.id);
                  },
                ),
              ],
            ),
          ),
          const Divider(height: 1),
          TabBar(
            controller: _tabController,
            tabs: const [
              Tab(text: 'General'),
              Tab(text: 'Data'),
              Tab(text: 'Style'),
            ],
          ),
          Expanded(
            child: TabBarView(
              controller: _tabController,
              children: [
                _buildGeneralTab(widgetModel),
                BindingPanel(
                  dashboardId: widget.dashboardId,
                  widget: widgetModel,
                ),
                _buildStyleTab(widgetModel),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildGeneralTab(WidgetModel w) {
    final props = w.properties;
    final notifier = ref.read(canvasStateProvider(widget.dashboardId).notifier);

    return ListView(
      padding: const EdgeInsets.all(AppSpacing.lg),
      children: [
        TextFormField(
          initialValue: props['title'] ?? '',
          decoration: const InputDecoration(labelText: 'Widget title'),
          onChanged: (val) {
            notifier.updateWidgetProperties(w.id, {'title': val});
          },
        ),
        const SizedBox(height: AppSpacing.md),
        SwitchListTile(
          contentPadding: EdgeInsets.zero,
          title: const Text('Show title header'),
          value: props['show_title'] ?? true,
          onChanged: (val) {
            notifier.updateWidgetProperties(w.id, {'show_title': val});
          },
        ),
        SwitchListTile(
          contentPadding: EdgeInsets.zero,
          title: const Text('Lock widget position'),
          value: w.isLocked,
          onChanged: (val) {
            notifier.toggleLockWidget(w.id);
          },
        ),
        const SizedBox(height: AppSpacing.md),
        Text(
          'Geometry bounds',
          style: Theme.of(
            context,
          ).textTheme.labelLarge?.copyWith(fontWeight: FontWeight.w800),
        ),
        const Divider(),
        Row(
          children: [
            Expanded(
              child: TextFormField(
                key: ValueKey('x-${w.position.x}'),
                initialValue: w.position.x.toStringAsFixed(0),
                decoration: const InputDecoration(labelText: 'X'),
                keyboardType: TextInputType.number,
                onFieldSubmitted: (val) {
                  final parsed = double.tryParse(val) ?? w.position.x;
                  notifier.moveWidget(w.id, parsed, w.position.y);
                },
              ),
            ),
            const SizedBox(width: AppSpacing.sm),
            Expanded(
              child: TextFormField(
                key: ValueKey('y-${w.position.y}'),
                initialValue: w.position.y.toStringAsFixed(0),
                decoration: const InputDecoration(labelText: 'Y'),
                keyboardType: TextInputType.number,
                onFieldSubmitted: (val) {
                  final parsed = double.tryParse(val) ?? w.position.y;
                  notifier.moveWidget(w.id, w.position.x, parsed);
                },
              ),
            ),
          ],
        ),
        Row(
          children: [
            Expanded(
              child: TextFormField(
                key: ValueKey('w-${w.size.width}'),
                initialValue: w.size.width.toStringAsFixed(0),
                decoration: const InputDecoration(labelText: 'Width'),
                keyboardType: TextInputType.number,
                onFieldSubmitted: (val) {
                  final parsed = double.tryParse(val) ?? w.size.width;
                  notifier.resizeWidget(
                    w.id,
                    w.position.x,
                    w.position.y,
                    parsed,
                    w.size.height,
                  );
                },
              ),
            ),
            const SizedBox(width: AppSpacing.sm),
            Expanded(
              child: TextFormField(
                key: ValueKey('h-${w.size.height}'),
                initialValue: w.size.height.toStringAsFixed(0),
                decoration: const InputDecoration(labelText: 'Height'),
                keyboardType: TextInputType.number,
                onFieldSubmitted: (val) {
                  final parsed = double.tryParse(val) ?? w.size.height;
                  notifier.resizeWidget(
                    w.id,
                    w.position.x,
                    w.position.y,
                    w.size.width,
                    parsed,
                  );
                },
              ),
            ),
          ],
        ),
        const SizedBox(height: AppSpacing.lg),
        Text(
          'Layers',
          style: Theme.of(
            context,
          ).textTheme.labelLarge?.copyWith(fontWeight: FontWeight.w800),
        ),
        const Divider(),
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceEvenly,
          children: [
            FilledButton(
              onPressed: () => notifier.bringToFront(w.id),
              child: const Text('Bring front'),
            ),
            OutlinedButton(
              onPressed: () => notifier.sendToBack(w.id),
              child: const Text('Send back'),
            ),
          ],
        ),
        const SizedBox(height: AppSpacing.xl),
        FilledButton.tonalIcon(
          style: FilledButton.styleFrom(
            backgroundColor: AppColors.stateError,
            foregroundColor: Theme.of(context).colorScheme.onError,
          ),
          onPressed: () {
            notifier.deleteWidget(w.id);
          },
          icon: const Icon(Icons.delete),
          label: const Text('Delete widget'),
        ),
      ],
    );
  }

  Widget _buildStyleTab(WidgetModel w) {
    final props = w.properties;
    final notifier = ref.read(canvasStateProvider(widget.dashboardId).notifier);

    return ListView(
      padding: const EdgeInsets.all(AppSpacing.lg),
      children: [
        Text(
          'Visual styling',
          style: Theme.of(
            context,
          ).textTheme.labelLarge?.copyWith(fontWeight: FontWeight.w800),
        ),
        const Divider(),
        TextFormField(
          initialValue: props['background_color'] ?? '#FFFFFF',
          decoration: const InputDecoration(
            labelText: 'Background color (HEX)',
          ),
          onFieldSubmitted: (val) {
            notifier.updateWidgetProperties(w.id, {'background_color': val});
          },
        ),
        const SizedBox(height: AppSpacing.sm),
        TextFormField(
          initialValue: props['border_color'] ?? '#E0E0E0',
          decoration: const InputDecoration(labelText: 'Border color (HEX)'),
          onFieldSubmitted: (val) {
            notifier.updateWidgetProperties(w.id, {'border_color': val});
          },
        ),
        const SizedBox(height: AppSpacing.sm),
        TextFormField(
          initialValue: (props['border_radius'] ?? 8.0).toString(),
          decoration: const InputDecoration(labelText: 'Border radius (px)'),
          keyboardType: TextInputType.number,
          onFieldSubmitted: (val) {
            final parsed = double.tryParse(val) ?? 8.0;
            notifier.updateWidgetProperties(w.id, {'border_radius': parsed});
          },
        ),
        const SizedBox(height: AppSpacing.sm),
        TextFormField(
          initialValue: (props['padding'] ?? 16.0).toString(),
          decoration: const InputDecoration(labelText: 'Padding (px)'),
          keyboardType: TextInputType.number,
          onFieldSubmitted: (val) {
            final parsed = double.tryParse(val) ?? 16.0;
            notifier.updateWidgetProperties(w.id, {'padding': parsed});
          },
        ),
        if (w.type == 'kpi_card') ...[
          const SizedBox(height: AppSpacing.lg),
          Text(
            'KPI styling',
            style: Theme.of(
              context,
            ).textTheme.labelLarge?.copyWith(fontWeight: FontWeight.w800),
          ),
          const Divider(),
          DropdownButtonFormField<String>(
            value: props['value_format'] ?? 'number',
            decoration: const InputDecoration(labelText: 'Value format'),
            items: const [
              DropdownMenuItem(value: 'number', child: Text('Number')),
              DropdownMenuItem(value: 'currency', child: Text('Currency')),
              DropdownMenuItem(value: 'percentage', child: Text('Percentage')),
              DropdownMenuItem(value: 'compact', child: Text('Compact')),
            ],
            onChanged: (val) {
              notifier.updateWidgetProperties(w.id, {'value_format': val});
            },
          ),
          const SizedBox(height: AppSpacing.sm),
          TextFormField(
            initialValue: props['prefix'] ?? '',
            decoration: const InputDecoration(labelText: 'Prefix'),
            onChanged: (val) {
              notifier.updateWidgetProperties(w.id, {'prefix': val});
            },
          ),
          const SizedBox(height: AppSpacing.sm),
          TextFormField(
            initialValue: props['suffix'] ?? '',
            decoration: const InputDecoration(labelText: 'Suffix'),
            onChanged: (val) {
              notifier.updateWidgetProperties(w.id, {'suffix': val});
            },
          ),
        ],
        if (w.type == 'filter_widget') ...[
          const SizedBox(height: AppSpacing.lg),
          Text(
            'Filter configuration',
            style: Theme.of(
              context,
            ).textTheme.labelLarge?.copyWith(fontWeight: FontWeight.w800),
          ),
          const Divider(),
          DropdownButtonFormField<String>(
            value: props['filter_type'] ?? 'dropdown',
            decoration: const InputDecoration(labelText: 'Filter input type'),
            items: const [
              DropdownMenuItem(
                value: 'dropdown',
                child: Text('Dropdown option selector'),
              ),
              DropdownMenuItem(
                value: 'text_search',
                child: Text('Text search input'),
              ),
              DropdownMenuItem(
                value: 'date_range_picker',
                child: Text('Date range picker'),
              ),
            ],
            onChanged: (val) {
              notifier.updateWidgetProperties(w.id, {'filter_type': val});
            },
          ),
          const SizedBox(height: AppSpacing.sm),
          TextFormField(
            initialValue: (props['static_options'] as List?)?.join(', ') ?? '',
            decoration: const InputDecoration(
              labelText: 'Static options (comma separated)',
            ),
            onFieldSubmitted: (val) {
              final options = val
                  .split(',')
                  .map((e) => e.trim())
                  .where((e) => e.isNotEmpty)
                  .toList();
              notifier.updateWidgetProperties(w.id, {
                'static_options': options,
              });
            },
          ),
        ],
      ],
    );
  }
}
