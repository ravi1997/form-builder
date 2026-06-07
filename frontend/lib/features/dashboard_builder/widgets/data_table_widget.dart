import 'package:flutter/material.dart';
import '../models/widget_model.dart';
import '../models/widget_data_model.dart';

class DataTableWidget extends StatefulWidget {
  final WidgetModel widget;
  final WidgetDataResult? dataResult;

  const DataTableWidget({
    super.key,
    required this.widget,
    this.dataResult,
  });

  @override
  State<DataTableWidget> createState() => _DataTableWidgetState();
}

class _DataTableWidgetState extends State<DataTableWidget> {
  String _searchQuery = '';
  String _sortColumn = '';
  bool _sortAscending = true;
  int _currentPage = 0;

  @override
  void initState() {
    super.initState();
    final props = widget.widget.properties;
    _sortColumn = props['default_sort_column'] ?? '';
    _sortAscending = (props['default_sort_direction'] ?? 'asc') == 'asc';
  }

  @override
  Widget build(BuildContext context) {
    final props = widget.widget.properties;
    final title = props['title'] ?? 'Data Table';
    final showTitle = props['show_title'] ?? true;
    final striped = props['striped_rows'] ?? true;
    final showSearch = props['show_search'] ?? false;
    final showPagination = props['show_pagination'] ?? true;
    final int maxRows = (props['max_rows_display'] as num? ?? 10).toInt();
    final headerBgStr = props['header_background'] ?? '#F5F5F5';
    final headerTextColorStr = props['header_text_color'] ?? '#424242';

    final headerBg = _parseColor(headerBgStr);
    final headerTextColor = _parseColor(headerTextColorStr);

    if (widget.dataResult == null || widget.dataResult!.status == 'loading') {
      return const Center(child: CircularProgressIndicator());
    }

    if (widget.dataResult!.status == 'error') {
      return Center(
        child: Text(
          widget.dataResult!.error ?? 'Error loading data',
          style: const TextStyle(color: Colors.red),
        ),
      );
    }

    if (widget.dataResult!.status == 'no_binding' || widget.dataResult!.data == null) {
      return Center(
        child: Text(props['no_data_message'] ?? 'No data available'),
      );
    }

    final tableData = TableData.fromJson(widget.dataResult!.data);
    if (tableData.columns.isEmpty) {
      return Center(child: Text(props['no_data_message'] ?? 'No data available'));
    }

    // 1. Apply Search Filter
    List<Map<String, dynamic>> processedRows = List.from(tableData.rows);
    if (showSearch && _searchQuery.isNotEmpty) {
      processedRows = processedRows.where((row) {
        return row.values.any((val) => val.toString().toLowerCase().contains(_searchQuery.toLowerCase()));
      }).toList();
    }

    // 2. Apply Sorting
    if (_sortColumn.isNotEmpty) {
      final colDef = tableData.columns.firstWhere((c) => c.name == _sortColumn,
          orElse: () => TableColumnDef(name: '', label: '', type: 'string'));
      processedRows.sort((a, b) {
        final valA = a[_sortColumn];
        final valB = b[_sortColumn];
        if (valA == null && valB == null) return 0;
        if (valA == null) return _sortAscending ? -1 : 1;
        if (valB == null) return _sortAscending ? 1 : -1;

        int compareRes = 0;
        if (colDef.type == 'number') {
          compareRes = (valA as num).compareTo(valB as num);
        } else {
          compareRes = valA.toString().compareTo(valB.toString());
        }
        return _sortAscending ? compareRes : -compareRes;
      });
    }

    // 3. Apply Pagination
    final int totalItems = processedRows.length;
    final int totalPages = (totalItems / maxRows).ceil();
    if (_currentPage >= totalPages && totalPages > 0) {
      _currentPage = totalPages - 1;
    }
    final int startIdx = _currentPage * maxRows;
    final int endIdx = (startIdx + maxRows).clamp(0, totalItems);
    final paginatedRows = totalItems > 0 ? processedRows.sublist(startIdx, endIdx) : <Map<String, dynamic>>[];

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        if (showTitle) ...[
          Text(title, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
          const SizedBox(height: 8),
        ],
        if (showSearch) ...[
          TextField(
            decoration: const InputDecoration(
              hintText: 'Search table...',
              prefixIcon: Icon(Icons.search, size: 20),
              border: OutlineInputBorder(),
              contentPadding: EdgeInsets.symmetric(vertical: 8, horizontal: 12),
            ),
            onChanged: (val) {
              setState(() {
                _searchQuery = val;
                _currentPage = 0;
              });
            },
          ),
          const SizedBox(height: 8),
        ],
        Expanded(
          child: SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: SingleChildScrollView(
              scrollDirection: Axis.vertical,
              child: DataTable(
                headingRowColor: WidgetStateProperty.all(headerBg),
                headingTextStyle: TextStyle(color: headerTextColor, fontWeight: FontWeight.bold),
                columns: tableData.columns.map((col) {
                  final isSorted = _sortColumn == col.name;
                  return DataColumn(
                    label: Row(
                      children: [
                        Text(col.label),
                        if (props['allow_sort'] == true) ...[
                          const SizedBox(width: 4),
                          Icon(
                            isSorted
                                ? (_sortAscending ? Icons.arrow_upward : Icons.arrow_downward)
                                : Icons.swap_vert,
                            size: 14,
                            color: isSorted ? headerTextColor : Colors.grey,
                          ),
                        ]
                      ],
                    ),
                    onSort: props['allow_sort'] == true
                        ? (colIndex, ascending) {
                            setState(() {
                              if (_sortColumn == col.name) {
                                _sortAscending = !_sortAscending;
                              } else {
                                _sortColumn = col.name;
                                _sortAscending = true;
                              }
                            });
                          }
                        : null,
                  );
                }).toList(),
                rows: List.generate(paginatedRows.length, (rowIdx) {
                  final row = paginatedRows[rowIdx];
                  final isEven = rowIdx % 2 == 0;
                  final Color rowBg = striped
                      ? (isEven ? Colors.white : Colors.grey.withOpacity(0.08))
                      : Colors.white;

                  return DataRow(
                    color: WidgetStateProperty.all(rowBg),
                    cells: tableData.columns.map((col) {
                      final val = row[col.name] ?? '';
                      return DataCell(Text(val.toString()));
                    }).toList(),
                  );
                }),
              ),
            ),
          ),
        ),
        if (showPagination && totalPages > 1) ...[
          const SizedBox(height: 8),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text('Showing ${startIdx + 1}-${endIdx} of $totalItems', style: const TextStyle(fontSize: 12)),
              Row(
                children: [
                  IconButton(
                    icon: const Icon(Icons.chevron_left),
                    onPressed: _currentPage > 0
                        ? () => setState(() => _currentPage--)
                        : null,
                  ),
                  Text('${_currentPage + 1} / $totalPages', style: const TextStyle(fontSize: 12)),
                  IconButton(
                    icon: const Icon(Icons.chevron_right),
                    onPressed: _currentPage < totalPages - 1
                        ? () => setState(() => _currentPage++)
                        : null,
                  ),
                ],
              )
            ],
          ),
        ],
      ],
    );
  }

  Color _parseColor(String hex) {
    try {
      final clean = hex.replaceAll('#', '');
      return Color(int.parse('FF$clean', radix: 16));
    } catch (_) {
      return Colors.grey[200]!;
    }
  }
}
