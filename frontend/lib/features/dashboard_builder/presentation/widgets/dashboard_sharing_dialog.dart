import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
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

        return AlertDialog(
          title: const Text('Share Dashboard'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text('Make this dashboard accessible publicly via a secure link:'),
              const SizedBox(height: 12),
              SwitchListTile(
                contentPadding: EdgeInsets.zero,
                title: const Text('Public Access'),
                subtitle: Text(_isPublic ? 'Anyone with the link can view' : 'Restricted to org users'),
                value: _isPublic,
                onChanged: _isLoading
                    ? null
                    : (val) async {
                        setState(() => _isLoading = true);
                        try {
                          if (val) {
                            final res = await service.enablePublicSharing(widget.dashboard.id, token);
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
                            await service.disablePublicSharing(widget.dashboard.id, token);
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
                const SizedBox(height: 16),
                const Text('Public Access URL:', style: TextStyle(fontWeight: FontWeight.bold)),
                const SizedBox(height: 4),
                Container(
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color: Colors.grey[100],
                    border: Border.all(color: Colors.grey[300]!),
                    borderRadius: BorderRadius.circular(4),
                  ),
                  child: Row(
                    children: [
                      Expanded(
                        child: Text(
                          publicUrl,
                          style: const TextStyle(fontFamily: 'monospace', fontSize: 12),
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                      IconButton(
                        icon: const Icon(Icons.copy, size: 16),
                        onPressed: () {
                          Clipboard.setData(ClipboardData(text: publicUrl));
                          ScaffoldMessenger.of(context).showSnackBar(
                            const SnackBar(content: Text('Public URL copied to clipboard')),
                          );
                        },
                      )
                    ],
                  ),
                ),
              ],
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(context).pop(),
              child: const Text('Close'),
            )
          ],
        );
      },
    );
  }
}
