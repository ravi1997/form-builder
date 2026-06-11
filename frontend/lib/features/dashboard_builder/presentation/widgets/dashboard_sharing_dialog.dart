import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/tokens.dart';
import '../../models/dashboard_model.dart';
import '../../providers/dashboard_provider.dart';

class DashboardSharingDialog extends StatefulWidget {
  final DashboardModel dashboard;
  final Function(DashboardModel) onDashboardUpdated;

  const DashboardSharingDialog({
    super.key,
    required this.dashboard,
    required this.onDashboardUpdated,
  });

  @override
  State<DashboardSharingDialog> createState() => _DashboardSharingDialogState();
}

class _DashboardSharingDialogState extends State<DashboardSharingDialog> {
  bool _isPublic = false;
  String? _publicToken;
  bool _isLoading = false;

  @override
  void initState() {
    super.initState();
    _isPublic = widget.dashboard.isPublic;
    _publicToken = widget.dashboard.publicToken;
  }

  @override
  Widget build(BuildContext context) {
    final publicUrl = _publicToken != null
        ? 'http://localhost:5000/public/dashboard/$_publicToken'
        : 'Not enabled';

    return Consumer(
      builder: (context, ref, child) {
        final service = ref.read(dashboardServiceProvider);
        final token = ref.read(authTokenProvider);

        return Dialog(
          insetPadding: const EdgeInsets.all(AppSpacing.lg),
          child: ConstrainedBox(
            constraints: const BoxConstraints(
              maxWidth: AppDimensions.dialogWidth,
            ),
            child: Padding(
              padding: const EdgeInsets.all(AppSpacing.xl),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Container(
                        padding: const EdgeInsets.all(AppSpacing.sm),
                        decoration: BoxDecoration(
                          color: AppColors.brandPrimarySoft,
                          borderRadius: BorderRadius.circular(AppRadius.md),
                        ),
                        child: const Icon(
                          Icons.share_outlined,
                          color: AppColors.brandPrimary,
                        ),
                      ),
                      const SizedBox(width: AppSpacing.sm),
                      Expanded(
                        child: Text(
                          'Share dashboard',
                          style: Theme.of(context).textTheme.titleLarge
                              ?.copyWith(fontWeight: FontWeight.w800),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: AppSpacing.lg),
                  Text(
                    'Make this dashboard accessible through a secure public link.',
                    style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                      color: AppColors.textSecondary,
                    ),
                  ),
                  const SizedBox(height: AppSpacing.md),
                  SwitchListTile(
                    contentPadding: EdgeInsets.zero,
                    title: const Text('Public access'),
                    subtitle: Text(
                      _isPublic
                          ? 'Anyone with the link can view'
                          : 'Restricted to organization users',
                    ),
                    value: _isPublic,
                    onChanged: _isLoading
                        ? null
                        : (val) async {
                            setState(() => _isLoading = true);
                            try {
                              if (val) {
                                final res = await service.enablePublicSharing(
                                  widget.dashboard.id,
                                  token,
                                );
                                setState(() {
                                  _isPublic = true;
                                  _publicToken = res['public_token'];
                                });
                                widget.onDashboardUpdated(
                                  widget.dashboard.copyWith(
                                    isPublic: true,
                                    publicToken: () => _publicToken,
                                  ),
                                );
                              } else {
                                await service.disablePublicSharing(
                                  widget.dashboard.id,
                                  token,
                                );
                                setState(() {
                                  _isPublic = false;
                                  _publicToken = null;
                                });
                                widget.onDashboardUpdated(
                                  widget.dashboard.copyWith(
                                    isPublic: false,
                                    publicToken: () => null,
                                  ),
                                );
                              }
                            } finally {
                              setState(() => _isLoading = false);
                            }
                          },
                  ),
                  if (_isPublic && _publicToken != null) ...[
                    const SizedBox(height: AppSpacing.md),
                    Text(
                      'Public access URL',
                      style: Theme.of(context).textTheme.labelLarge?.copyWith(
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                    const SizedBox(height: AppSpacing.xs),
                    Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: AppSpacing.md,
                        vertical: AppSpacing.sm,
                      ),
                      decoration: BoxDecoration(
                        color: AppColors.surfaceCardAlt,
                        border: Border.all(color: AppColors.borderSubtle),
                        borderRadius: BorderRadius.circular(AppRadius.md),
                      ),
                      child: Row(
                        children: [
                          Expanded(
                            child: Text(
                              publicUrl,
                              style: Theme.of(context).textTheme.bodySmall
                                  ?.copyWith(fontFamily: 'monospace'),
                              overflow: TextOverflow.ellipsis,
                            ),
                          ),
                          IconButton(
                            icon: const Icon(Icons.copy, size: 18),
                            onPressed: () {
                              Clipboard.setData(ClipboardData(text: publicUrl));
                              ScaffoldMessenger.of(context).showSnackBar(
                                const SnackBar(
                                  content: Text(
                                    'Public URL copied to clipboard',
                                  ),
                                ),
                              );
                            },
                          ),
                        ],
                      ),
                    ),
                  ],
                  const SizedBox(height: AppSpacing.lg),
                  Align(
                    alignment: Alignment.centerRight,
                    child: TextButton(
                      onPressed: () => Navigator.of(context).pop(),
                      child: const Text('Close'),
                    ),
                  ),
                ],
              ),
            ),
          ),
        );
      },
    );
  }
}
