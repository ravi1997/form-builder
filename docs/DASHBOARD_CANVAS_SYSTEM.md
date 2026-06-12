# Dashboard Canvas System

## Overview

The Dashboard Canvas System provides a free-form, drag-and-drop interface for creating interactive dashboards with real-time data visualization. This system allows users to build custom dashboards by placing widgets on a canvas and binding them to analysis output nodes.

## Features

### 🎨 Free-Form Canvas
- **Absolute Positioning**: Widgets can be placed anywhere on the canvas with pixel-perfect precision
- **Resizable Widgets**: All widgets can be resized to fit the dashboard layout
- **Layering Support**: Z-index control for widget overlapping and layering
- **Canvas Background**: Customizable background colors and themes

### 📊 Widget System
The system supports multiple widget types:

#### KPI Cards
- Display single numeric values from analysis outputs
- Customizable titles, colors, and formatting
- Support for trend indicators and comparisons

#### Charts
- **Bar Charts**: For categorical data comparison
- **Line Charts**: For time series and trend analysis  
- **Pie Charts**: For proportional data representation
- All charts support real-time data updates

#### Data Tables
- Display tabular data from analysis outputs
- Sortable columns and pagination
- Customizable column visibility and formatting

#### Filter Widgets
- Interactive filter controls for dashboard data
- Support for dropdowns, date ranges, and multi-select filters
- Real-time filtering of bound data widgets

#### Display Widgets
- **Text Labels**: Static text and titles
- **Images**: Logo and image display
- **Dividers**: Visual separation elements

### 🔗 Data Binding
- **Analysis Integration**: Widgets bind directly to analysis output nodes
- **Real-time Updates**: Data refreshes automatically or on-demand
- **Filter Integration**: Widgets can be filtered by other filter widgets
- **Multiple Analyses**: Single dashboard can pull data from multiple analyses

### 🔄 Auto-Refresh
- **Configurable Intervals**: Set refresh intervals from 10 seconds to 1 hour
- **Per-Widget Control**: Individual widgets can have independent refresh settings
- **Performance Optimized**: Efficient data fetching and caching

### 🌐 Public Sharing
- **Public Tokens**: Generate secure tokens for public dashboard access
- **Embeddable**: Dashboards can be embedded in external websites
- **Access Control**: Fine-grained control over public access permissions
- **Analytics**: Track public dashboard usage and access statistics

### 📸 Snapshots
- **Point-in-Time**: Capture dashboard state at specific moments
- **Historical Tracking**: Maintain history of dashboard changes over time
- **Comparison**: Compare different snapshots to analyze data trends
- **Export**: Snapshots can be exported and shared

## Architecture

### Data Models

#### Dashboard Model
```python
class Dashboard(BaseDBModel):
    project_id: PyObjectId
    name: str
    description: str
    is_public: bool
    public_token: Optional[str]
    canvas: Canvas
    settings: DashboardSettings
    linked_analysis_ids: List[PyObjectId]
```

#### Widget Model
```python
class Widget(BaseModel):
    id: str  # UUID
    type: str  # Widget type
    position: Position
    size: Size
    z_index: int
    is_locked: bool
    properties: Dict[str, Any]
    data_binding: Optional[DataBinding]
    filters: List[FilterBinding]
```

#### Canvas Model
```python
class Canvas(BaseModel):
    width: int
    height: int
    background_color: str
    widgets: List[Widget]
```

### Service Layer

The `DashboardService` class provides all business logic for dashboard operations:

- **Dashboard CRUD**: Create, read, update, delete dashboards
- **Canvas Operations**: Save canvas layouts, validate widget configurations
- **Data Resolution**: Resolve widget data from analysis outputs
- **Public Sharing**: Enable/disable public access with tokens
- **Snapshot Management**: Create and manage dashboard snapshots

### API Endpoints

#### Dashboard Management
- `POST /api/internal/v1/dashboards` - Create dashboard
- `GET /api/internal/v1/dashboards` - List dashboards (with pagination)
- `GET /api/internal/v1/dashboards/{id}` - Get dashboard details
- `PATCH /api/internal/v1/dashboards/{id}` - Update dashboard
- `DELETE /api/internal/v1/dashboards/{id}` - Delete dashboard

#### Canvas Operations
- `PUT /api/internal/v1/dashboards/{id}/canvas` - Save canvas layout
- `GET /api/internal/v1/dashboards/{id}/data` - Get canvas with widget data
- `GET /api/internal/v1/dashboards/{id}/widgets/{widget_id}/data` - Get specific widget data

#### Public Access
- `POST /api/internal/v1/dashboards/{id}/public-token` - Enable public sharing
- `DELETE /api/internal/v1/dashboards/{id}/public-token` - Revoke public sharing
- `GET /api/v1/public/dashboards/{token}` - Get public dashboard
- `GET /api/v1/public/dashboards/{token}/data` - Get public dashboard data

#### Snapshots
- `POST /api/internal/v1/dashboards/{id}/snapshots` - Create snapshot
- `GET /api/internal/v1/dashboards/{id}/snapshots` - List snapshots
- `GET /api/internal/v1/dashboards/{id}/snapshots/{snapshot_id}` - Get snapshot
- `DELETE /api/internal/v1/dashboards/{id}/snapshots/{snapshot_id}` - Delete snapshot

### Background Tasks

The system includes Celery tasks for background operations:

#### Dashboard Tasks (`dashboard_tasks.py`)
- `refresh_dashboard_data_task` - Refresh all widget data
- `cleanup_old_snapshots_task` - Clean up old snapshots
- `generate_dashboard_snapshot_task` - Create dashboard snapshot
- `update_dashboard_access_stats_task` - Update access statistics
- `cache_filter_options_task` - Cache filter options
- `validate_dashboard_integrity_task` - Validate dashboard configuration

## Usage Examples

### Creating a Dashboard

```python
# Create dashboard
dashboard_data = {
    "project_id": "project_id",
    "name": "Sales Dashboard",
    "description": "Monthly sales performance dashboard",
    "canvas": {
        "width": 1920,
        "height": 1080,
        "background_color": "#F5F5F5",
        "widgets": []
    },
    "settings": {
        "auto_refresh": True,
        "refresh_interval_seconds": 60,
        "theme": {
            "font_family": "Inter",
            "primary_color": "#1976D2",
            "border_radius": 8
        }
    }
}

dashboard = dashboard_service.create_dashboard(dashboard_data, user_id, context)
```

### Adding Widgets to Canvas

```python
canvas_data = {
    "width": 1920,
    "height": 1080,
    "background_color": "#FFFFFF",
    "widgets": [
        {
            "id": str(uuid.uuid4()),
            "type": "kpi_card",
            "position": {"x": 50, "y": 50},
            "size": {"width": 300, "height": 200},
            "z_index": 1,
            "is_locked": False,
            "properties": {"title": "Total Sales"},
            "data_binding": {
                "analysis_id": "analysis_id",
                "node_id": "total_sales_node",
                "refresh_mode": "with_dashboard"
            }
        },
        {
            "id": str(uuid.uuid4()),
            "type": "bar_chart",
            "position": {"x": 400, "y": 50},
            "size": {"width": 500, "height": 300},
            "z_index": 1,
            "is_locked": False,
            "properties": {"title": "Sales by Category"},
            "data_binding": {
                "analysis_id": "analysis_id",
                "node_id": "sales_by_category_node",
                "refresh_mode": "with_dashboard"
            }
        },
        {
            "id": str(uuid.uuid4()),
            "type": "filter_widget",
            "position": {"x": 50, "y": 300},
            "size": {"width": 200, "height": 50},
            "z_index": 1,
            "is_locked": False,
            "properties": {"title": "Category Filter"}
        }
    ]
}

dashboard_service.save_canvas(dashboard_id, canvas_data, context)
```

### Enabling Public Sharing

```python
# Enable public sharing
result = dashboard_service.enable_public_sharing(dashboard_id)
print(f"Public URL: {result['public_url']}")

# Revoke public sharing
dashboard_service.revoke_public_sharing(dashboard_id)
```

### Creating Snapshots

```python
# Create snapshot
snapshot = dashboard_service.create_snapshot(dashboard_id, user_id, context)

# List snapshots
snapshots, pagination = dashboard_service.list_snapshots(dashboard_id, page=1, per_page=20)

# Get specific snapshot
snapshot = dashboard_service.get_snapshot(dashboard_id, snapshot_id)
```

## Configuration

### Canvas Limits
- **Minimum Width**: 800px
- **Maximum Width**: 7680px
- **Minimum Height**: 600px
- **Maximum Height**: 4320px

### Widget Limits
- **Minimum Size**: 20x20px
- **Z-Index Range**: 0-999
- **Widget ID**: Must be valid UUID

### Refresh Settings
- **Minimum Interval**: 10 seconds
- **Maximum Interval**: 3600 seconds (1 hour)

## Security Considerations

### Public Access
- Public dashboards are accessible via unique tokens
- Sensitive data is stripped from public responses
- Access logging and analytics for public dashboards

### Data Binding
- Widgets can only access data from analyses the user has permission to view
- Analysis results are validated before binding
- Filter bindings are validated to prevent circular references

### Input Validation
- All canvas and widget configurations are validated
- Widget IDs must be valid UUIDs
- Analysis bindings are verified to exist

## Performance Optimizations

### Caching
- Filter options are cached in Redis for 5 minutes
- Widget data can be cached based on analysis result TTL
- Public dashboard responses are cached when appropriate

### Background Processing
- Data refresh operations run in background tasks
- Snapshot generation is asynchronous
- Dashboard validation runs in background

### Efficient Data Loading
- Widget data is resolved on-demand
- Only necessary analysis results are fetched
- Pagination for large datasets

## Integration with Other Systems

### Analysis Engine
- Dashboards bind to analysis output nodes
- Real-time data updates when analyses are re-run
- Support for all analysis node types (tables, charts, KPIs)

### Authentication System
- Dashboard access follows organizational permissions
- Public access tokens are separate from user authentication
- Audit logging for all dashboard operations

### Plugin System
- Dashboard widgets can be extended via plugins
- Custom widget types can be registered
- Plugin widgets follow the same data binding patterns

## Testing

The system includes comprehensive tests covering:

- **Model Validation**: All Pydantic models are tested for validation
- **Service Layer**: Dashboard service operations are thoroughly tested
- **API Endpoints**: All REST endpoints are tested with various scenarios
- **Integration Tests**: Full dashboard workflows are tested
- **Performance Tests**: Canvas operations with many widgets

Run tests with:
```bash
pytest tests/test_dashboard.py -v
```

## Future Enhancements

### Planned Features
- **Export Options**: PDF, PNG, and CSV export for dashboards
- **Collaborative Editing**: Real-time collaboration on dashboard design
- **Advanced Filters**: Date range pickers, multi-column filtering
- **Widget Templates**: Pre-built widget configurations
- **Dashboard Templates**: Pre-built dashboard layouts

### Performance Improvements
- **WebSocket Updates**: Real-time data updates via WebSockets
- **Client-side Caching**: Improved caching strategies
- **Lazy Loading**: Load widget data on demand
- **Compression**: Reduce data transfer sizes

### UI/UX Enhancements
- **Grid Snapping**: Optional grid alignment for widgets
- **Undo/Redo**: History tracking for canvas changes
- **Keyboard Shortcuts**: Quick actions for power users
- **Responsive Design**: Mobile-friendly dashboard views

## Troubleshooting

### Common Issues

#### Widget Not Showing Data
1. Verify analysis binding is correct
2. Check analysis has completed successfully
3. Ensure user has permission to view the analysis
4. Check widget data binding configuration

#### Public Access Not Working
1. Verify public sharing is enabled
2. Check public token is correct
3. Ensure dashboard contains no sensitive data
4. Verify public access URL is correct

#### Canvas Save Failing
1. Check widget IDs are valid UUIDs
2. Verify analysis bindings exist
3. Ensure widget positions are within canvas bounds
4. Check for duplicate widget IDs

#### Performance Issues
1. Reduce number of widgets on dashboard
2. Increase refresh intervals
3. Use appropriate widget types for data size
4. Enable caching where possible

### Debug Mode
Enable debug logging for detailed troubleshooting:
```python
import logging
logging.getLogger('app.services.dashboard_service').setLevel(logging.DEBUG)
```

## Contributing

When contributing to the Dashboard Canvas System:

1. **Follow Coding Standards**: Use PEP 8 and type hints
2. **Add Tests**: Include comprehensive tests for new features
3. **Update Documentation**: Document new functionality
4. **Performance Testing**: Test with large numbers of widgets
5. **Security Review**: Ensure all changes follow security best practices

## License

This Dashboard Canvas System is part of the Form Builder Platform and is subject to the same license terms.