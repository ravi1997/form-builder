import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'canvas/dashboard_canvas.dart';
import 'models/dashboard_model.dart';
import 'properties/property_panel.dart';
import 'providers/canvas_state_provider.dart';
import 'providers/dashboard_provider.dart';
import 'providers/widget_data_provider.dart';
import 'sidebar/widget_library_sidebar.dart';
import 'presentation/widgets/dashboard_sharing_dialog.dart';

class DashboardBuilderPage extends ConsumerStatefulWidget {
  final String dashboardId;

  const DashboardBuilderPage({
    super.key,
    required this.dashboardId,
  });

  @override
  ConsumerState<DashboardBuilderPage> createState() => _DashboardBuilderPageState();
}

class _DashboardBuilderPageState extends ConsumerState<DashboardBuilderPage> {
  DashboardModel? _dashboard;
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadDashboardData();
  }

  Future<void> _loadDashboardData() async {
    setState(() => _isLoading = true);
    final service = ref.read(dashboardServiceProvider);
    final token = ref.read(authTokenProvider);

    try {
      final dbModel = await service.getDashboard(widget.dashboardId, token);
      setState(() {
        _dashboard = dbModel;
        _isLoading = false;
      });

      // Load canvas and initialize data fetches
      ref.read(canvasStateProvider(widget.dashboardId).notifier).loadDashboard(dbModel);
      ref.read(widgetDataProvider(widget.dashboardId).notifier).refreshData();
      _setupAutoRefreshTimer(dbModel);
    } catch (_) {
      setState(() => _isLoading = false);
    }
  }

  void _setupAutoRefreshTimer(DashboardModel dbModel) {
    ref.read(widgetDataProvider(widget.dashboardId).notifier).setupAutoRefresh(
          enabled: dbModel.settings.autoRefresh,
          intervalSeconds: dbModel.settings.refreshIntervalSeconds,
        );
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading) {
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }

    if (_dashboard == null) {
      return const Scaffold(body: Center(child: Text('Failed to load dashboard.')));
    }

    final canvasState = ref.watch(canvasStateProvider(widget.dashboardId));
    final isEditMode = canvasState.mode == CanvasMode.edit;

    return Scaffold(
      appBar: AppBar(
        title: Text(canvasState.isDirty ? '${_dashboard!.name}*' : _dashboard!.name),
        actions: [
          // Undo / Redo
          if (isEditMode) ...[
            IconButton(
              icon: const Icon(Icons.undo),
              onPressed: () => ref.read(canvasStateProvider(widget.dashboardId).notifier).undo(),
            ),
            IconButton(
              icon: const Icon(Icons.redo),
              onPressed: () => ref.read(canvasStateProvider(widget.dashboardId).notifier).redo(),
            ),
            const VerticalDivider(),
            // Snap to Grid
            IconButton(
              icon: Icon(canvasState.snapToGrid ? Icons.grid_on : Icons.grid_off),
              tooltip: 'Snap to Grid',
              onPressed: () => ref.read(canvasStateProvider(widget.dashboardId).notifier).toggleSnapToGrid(),
            ),
          ],
          const VerticalDivider(),
          // Settings (Auto-Refresh)
          IconButton(
            icon: const Icon(Icons.settings),
            tooltip: 'Settings / Auto-Refresh',
            onPressed: () => _showSettingsDialog(context),
          ),
          // Share
          IconButton(
            icon: const Icon(Icons.share),
            tooltip: 'Share',
            onPressed: () => _showSharingDialog(context),
          ),
          // Preview Toggle
          IconButton(
            icon: Icon(isEditMode ? Icons.visibility : Icons.edit),
            tooltip: isEditMode ? 'Preview Mode' : 'Edit Mode',
            onPressed: () => ref.read(canvasStateProvider(widget.dashboardId).notifier).toggleMode(),
          ),
          // Save Button
          if (canvasState.isDirty)
            IconButton(
              icon: const Icon(Icons.save),
              tooltip: 'Save Canvas',
              onPressed: () async {
                await ref.read(canvasStateProvider(widget.dashboardId).notifier).saveCanvasState();
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(content: Text('Canvas saved successfully')),
                );
              },
            ),
        ],
      ),
      body: Row(
        children: [
          if (isEditMode)
            SizedBox(
              width: 260,
              child: WidgetLibrarySidebar(dashboardId: widget.dashboardId),
            ),
          Expanded(
            child: DashboardCanvas(dashboardId: widget.dashboardId),
          ),
          if (isEditMode)
            SizedBox(
              width: 300,
              child: PropertyPanel(dashboardId: widget.dashboardId),
            ),
        ],
      ),
    );
  }

  void _showSharingDialog(BuildContext context) {
    if (_dashboard == null) return;
    showDialog(
      context: context,
      builder: (context) => DashboardSharingDialog(
        dashboard: _dashboard!,
        onDashboardUpdated: (updated) {
          setState(() {
            _dashboard = updated;
          });
        },
      ),
    );
  }

  void _showSettingsDialog(BuildContext context) {
    if (_dashboard == null) return;
    showDialog(
      context: context,
      builder: (context) {
        bool autoRefresh = _dashboard!.settings.autoRefresh;
        int interval = _dashboard!.settings.refreshIntervalSeconds;

        return StatefulBuilder(
          builder: (context, setDialogState) {
            return AlertDialog(
              title: const Text('Dashboard Settings'),
              content: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  SwitchListTile(
                    title: const Text('Enable Auto-Refresh'),
                    value: autoRefresh,
                    onChanged: (val) {
                      setDialogState(() => autoRefresh = val);
                    },
                  ),
                  if (autoRefresh) ...[
                    const SizedBox(height: 8),
                    TextFormField(
                      initialValue: interval.toString(),
                      decoration: const InputDecoration(
                        labelText: 'Refresh Interval (seconds)',
                        border: OutlineInputBorder(),
                      ),
                      keyboardType: TextInputType.number,
                      onChanged: (val) {
                        final parsed = int.tryParse(val) ?? 60;
                        setDialogState(() => interval = parsed);
                      },
                    ),
                  ],
                ],
              ),
              actions: [
                TextButton(
                  onPressed: () => Navigator.of(context).pop(),
                  child: const Text('Cancel'),
                ),
                ElevatedButton(
                  onPressed: () async {
                    final service = ref.read(dashboardServiceProvider);
                    final token = ref.read(authTokenProvider);
                    final newSettings = _dashboard!.settings.copyWith(
                      autoRefresh: autoRefresh,
                      refreshIntervalSeconds: interval,
                    );

                    final updated = await service.updateDashboard(
                      dashboardId: _dashboard!.id,
                      settings: newSettings,
                      token: token,
                    );

                    setState(() {
                      _dashboard = updated;
                    });
                    _setupAutoRefreshTimer(updated);
                    Navigator.of(context).pop();
                  },
                  child: const Text('Save'),
                ),
              ],
            );
          },
        );
      },
    );
  }
}
