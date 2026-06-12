import 'package:flutter/material.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/design_system.dart';
import '../../../../core/theme/tokens.dart';

class CompliancePage extends StatefulWidget {
  final double? initialUsedBytes;
  const CompliancePage({super.key, this.initialUsedBytes});

  @override
  State<CompliancePage> createState() => _CompliancePageState();
}

class _CompliancePageState extends State<CompliancePage> {
  // Mock data representing the storage quota settings
  late double _usedBytes;
  final double _quotaBytes = 1024 * 1024 * 1024; // 1 GB (1024 MB)
  final double _warningThreshold = 0.8; // 80%

  @override
  void initState() {
    super.initState();
    _usedBytes = widget.initialUsedBytes ?? (850 * 1024 * 1024);
  }


  final List<Map<String, dynamic>> _legalHolds = [
    {
      'id': 'hold_1',
      'name': 'GDPR Audit Retention',
      'description': 'Hold forms and responses for ongoing GDPR audit compliance.',
      'target_type': 'project',
      'target_ids': ['project_alpha', 'project_beta'],
      'is_active': true,
      'created_at': '2026-06-01T12:00:00Z',
    },
    {
      'id': 'hold_2',
      'name': 'HIPAA Compliance Retainer',
      'description': 'Medical data audit retention hold.',
      'target_type': 'form',
      'target_ids': ['form_patient_intake'],
      'is_active': false,
      'created_at': '2026-05-15T08:30:00Z',
    }
  ];

  void _addLegalHold(String name, String description, String targetType, List<String> targetIds) {
    setState(() {
      _legalHolds.add({
        'id': 'hold_${DateTime.now().millisecondsSinceEpoch}',
        'name': name,
        'description': description,
        'target_type': targetType,
        'target_ids': targetIds,
        'is_active': true,
        'created_at': DateTime.now().toIso8601String(),
      });
    });
  }

  void _toggleHold(int index) {
    setState(() {
      _legalHolds[index]['is_active'] = !_legalHolds[index]['is_active'];
    });
  }

  void _showAddHoldDialog() {
    final nameController = TextEditingController();
    final descController = TextEditingController();
    final targetIdsController = TextEditingController();
    String targetType = 'form';

    showDialog(
      context: context,
      builder: (context) {
        return StatefulBuilder(
          builder: (context, setDialogState) {
            return AlertDialog(
              backgroundColor: AppColors.surfaceCard,
              title: const Text('Create Compliance Legal Hold'),
              content: SingleChildScrollView(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    TextField(
                      controller: nameController,
                      decoration: const InputDecoration(labelText: 'Hold Name'),
                    ),
                    const SizedBox(height: AppSpacing.sm),
                    TextField(
                      controller: descController,
                      decoration: const InputDecoration(labelText: 'Description'),
                    ),
                    const SizedBox(height: AppSpacing.md),
                    DropdownButtonFormField<String>(
                      value: targetType,
                      dropdownColor: AppColors.surfaceCard,
                      decoration: const InputDecoration(labelText: 'Target Type'),
                      items: ['form', 'project'].map((type) {
                        return DropdownMenuItem(value: type, child: Text(type.toUpperCase()));
                      }).toList(),
                      onChanged: (val) {
                        if (val != null) {
                          setDialogState(() {
                            targetType = val;
                          });
                        }
                      },
                    ),
                    const SizedBox(height: AppSpacing.sm),
                    TextField(
                      controller: targetIdsController,
                      decoration: const InputDecoration(
                        labelText: 'Target IDs (comma separated)',
                        hintText: 'e.g. q_text, subsec_1',
                      ),
                    ),
                  ],
                ),
              ),
              actions: [
                TextButton(
                  onPressed: () => Navigator.pop(context),
                  child: const Text('Cancel'),
                ),
                ElevatedButton(
                  onPressed: () {
                    if (nameController.text.trim().isNotEmpty) {
                      final ids = targetIdsController.text
                          .split(',')
                          .map((s) => s.trim())
                          .where((s) => s.isNotEmpty)
                          .toList();
                      _addLegalHold(
                        nameController.text.trim(),
                        descController.text.trim(),
                        targetType,
                        ids,
                      );
                      Navigator.pop(context);
                    }
                  },
                  child: const Text('Create'),
                ),
              ],
            );
          },
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    final usageRatio = _usedBytes / _quotaBytes;
    final isOverWarning = usageRatio >= _warningThreshold;
    final usagePercent = (usageRatio * 100).toStringAsFixed(1);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Admin Compliance & Settings'),
        backgroundColor: Colors.transparent,
        elevation: 0,
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => Navigator.of(context).maybePop() ?? Navigator.of(context).pop(),
        ),
      ),
      body: SingleChildScrollView(
        padding: EdgeInsets.all(AppSpacing.lg),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Quota storage indicator section
            Card(
              color: AppColors.surfaceCard.withOpacity(0.3),
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(AppRadius.md),
                side: BorderSide(
                  color: isOverWarning ? Colors.amber.withOpacity(0.5) : AppColors.borderSubtle.withOpacity(0.3),
                  width: isOverWarning ? 2 : 1,
                ),
              ),
              child: Padding(
                padding: EdgeInsets.all(AppSpacing.md),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        const Text(
                          'Storage Quota Usage',
                          style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
                        ),
                        Text(
                          '$usagePercent% Used',
                          style: TextStyle(
                            fontWeight: FontWeight.bold,
                            color: isOverWarning ? Colors.amberAccent : Colors.white,
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: AppSpacing.sm),
                    LinearProgressIndicator(
                      value: usageRatio,
                      backgroundColor: Colors.white24,
                      valueColor: AlwaysStoppedAnimation<Color>(
                        isOverWarning ? Colors.amber : Colors.blue,
                      ),
                      minHeight: 12,
                      borderRadius: BorderRadius.circular(6),
                    ),
                    const SizedBox(height: AppSpacing.sm),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Text(
                          '${(_usedBytes / (1024 * 1024)).toStringAsFixed(0)} MB of ${(_quotaBytes / (1024 * 1024)).toStringAsFixed(0)} MB used',
                          style: const TextStyle(color: Colors.grey, fontSize: 13),
                        ),
                        if (isOverWarning)
                          const Row(
                            children: [
                              Icon(Icons.warning_amber_rounded, color: Colors.amberAccent, size: 16),
                              SizedBox(width: 4),
                              Text(
                                'Warning: Near storage limit',
                                style: TextStyle(color: Colors.amberAccent, fontSize: 13, fontWeight: FontWeight.bold),
                              ),
                            ],
                          ),
                      ],
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: AppSpacing.lg),

            // Legal Holds Management header
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Text(
                  'Compliance Legal Holds',
                  style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
                ),
                ElevatedButton.icon(
                  onPressed: _showAddHoldDialog,
                  icon: const Icon(Icons.add),
                  label: const Text('Add Legal Hold'),
                ),
              ],
            ),
            const SizedBox(height: AppSpacing.md),

            // Legal holds list
            ListView.builder(
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              itemCount: _legalHolds.length,
              itemBuilder: (context, index) {
                final hold = _legalHolds[index];
                final isActive = hold['is_active'] as bool;
                return Card(
                  margin: EdgeInsets.only(bottom: AppSpacing.md),
                  color: AppColors.surfaceCard.withOpacity(0.5),
                  child: ListTile(
                    title: Text(
                      hold['name'],
                      style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
                    ),
                    subtitle: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const SizedBox(height: 4),
                        Text(hold['description'], style: const TextStyle(color: Colors.grey)),
                        const SizedBox(height: 8),
                        Row(
                          children: [
                            Chip(
                              label: Text(
                                '${hold['target_type'].toUpperCase()}: ${hold['target_ids'].join(', ')}',
                                style: const TextStyle(fontSize: 11, color: Colors.white70),
                              ),
                              backgroundColor: Colors.white12,
                              padding: EdgeInsets.zero,
                            ),
                            const Spacer(),
                            Text(
                              'Created: ${hold['created_at'].substring(0, 10)}',
                              style: const TextStyle(fontSize: 11, color: Colors.grey),
                            ),
                          ],
                        ),
                      ],
                    ),
                    trailing: Switch(
                      value: isActive,
                      activeColor: Colors.blueAccent,
                      onChanged: (val) => _toggleHold(index),
                    ),
                  ),
                );
              },
            ),
          ],
        ),
      ),
    );
  }
}
