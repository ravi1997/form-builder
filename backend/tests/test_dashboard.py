import pytest
import json
import uuid
from datetime import datetime, timedelta
from bson import ObjectId
from app import create_app
from app.services.dashboard_service import dashboard_service
from app.models.dashboard import Dashboard, Widget, Canvas, DashboardSettings


@pytest.fixture
def app():
    """Create test Flask app."""
    app = create_app("testing")
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


@pytest.fixture
def test_user():
    """Create test user."""
    return {
        "_id": ObjectId(),
        "email": "test@example.com",
        "full_name": "Test User",
        "status": "active",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "created_by": ObjectId(),
        "is_deleted": False,
        "deleted_at": None
    }


@pytest.fixture
def test_org():
    """Create test organization."""
    return {
        "_id": ObjectId(),
        "name": "Test Org",
        "slug": "test-org",
        "status": "active",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "created_by": ObjectId(),
        "is_deleted": False,
        "deleted_at": None
    }


@pytest.fixture
def test_project(test_org):
    """Create test project."""
    return {
        "_id": ObjectId(),
        "name": "Test Project",
        "description": "Test project description",
        "slug": "test-project",
        "owner_org_id": test_org["_id"],
        "status": "active",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "created_by": ObjectId(),
        "org_id": test_org["_id"],
        "is_deleted": False,
        "deleted_at": None
    }


@pytest.fixture
def test_analysis(test_org, test_project):
    """Create test analysis."""
    return {
        "_id": ObjectId(),
        "name": "Test Analysis",
        "description": "Test analysis description",
        "org_id": test_org["_id"],
        "project_id": test_project["_id"],
        "linked_form_ids": [],
        "execution_modes": ["on_demand"],
        "schedule": None,
        "reactive_debounce_ms": 1000,
        "graph": {
            "nodes": [
                {
                    "id": "node1",
                    "type": "table_output",
                    "position": {"x": 100, "y": 100},
                    "size": {"width": 200, "height": 100},
                    "properties": {"title": "Test Output"},
                    "label": "Test Output Node",
                    "is_disabled": False
                },
                {
                    "id": "node2",
                    "type": "kpi_value",
                    "position": {"x": 100, "y": 250},
                    "size": {"width": 200, "height": 100},
                    "properties": {"title": "Test KPI"},
                    "label": "Test KPI Node",
                    "is_disabled": False
                }
            ],
            "edges": []
        },
        "last_run_id": None,
        "status": "idle",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "created_by": ObjectId(),
        "is_deleted": False,
        "deleted_at": None
    }


@pytest.fixture
def test_analysis_run(test_analysis):
    """Create test analysis run."""
    return {
        "_id": ObjectId(),
        "analysis_id": test_analysis["_id"],
        "org_id": test_analysis["org_id"],
        "trigger": "manual",
        "triggered_by": ObjectId(),
        "status": "completed",
        "started_at": datetime.utcnow() - timedelta(minutes=5),
        "completed_at": datetime.utcnow() - timedelta(minutes=4),
        "celery_task_id": "test-task-id",
        "node_statuses": {
            "node1": {"status": "completed", "started_at": datetime.utcnow() - timedelta(minutes=5), "completed_at": datetime.utcnow() - timedelta(minutes=4)},
            "node2": {"status": "completed", "started_at": datetime.utcnow() - timedelta(minutes=5), "completed_at": datetime.utcnow() - timedelta(minutes=4)}
        },
        "error_summary": None,
        "result_ids": {
            "node1": ObjectId(),
            "node2": ObjectId()
        },
        "created_at": datetime.utcnow() - timedelta(minutes=5)
    }


@pytest.fixture
def test_analysis_result(test_analysis_run):
    """Create test analysis result."""
    return [
        {
            "_id": test_analysis_run["result_ids"]["node1"],
            "run_id": test_analysis_run["_id"],
            "analysis_id": test_analysis_run["analysis_id"],
            "node_id": "node1",
            "org_id": test_analysis_run["org_id"],
            "output_type": "table",
            "data": {
                "out": {
                    "rows": [
                        {"id": 1, "name": "Item 1", "value": 100, "category": "A"},
                        {"id": 2, "name": "Item 2", "value": 200, "category": "B"},
                        {"id": 3, "name": "Item 3", "value": 150, "category": "A"}
                    ],
                    "row_count": 3,
                    "column_definitions": [
                        {"name": "id", "type": "int", "label": "ID"},
                        {"name": "name", "type": "string", "label": "Name"},
                        {"name": "value", "type": "int", "label": "Value"},
                        {"name": "category", "type": "string", "label": "Category"}
                    ]
                }
            },
            "row_count": 3,
            "column_definitions": [
                {"name": "id", "type": "int", "label": "ID"},
                {"name": "name", "type": "string", "label": "Name"},
                {"name": "value", "type": "int", "label": "Value"},
                {"name": "category", "type": "string", "label": "Category"}
            ],
            "cached_until": datetime.utcnow() + timedelta(hours=1),
            "created_at": datetime.utcnow() - timedelta(minutes=4)
        },
        {
            "_id": test_analysis_run["result_ids"]["node2"],
            "run_id": test_analysis_run["_id"],
            "analysis_id": test_analysis_run["analysis_id"],
            "node_id": "node2",
            "org_id": test_analysis_run["org_id"],
            "output_type": "value",
            "data": {
                "out": 450
            },
            "row_count": 0,
            "column_definitions": [],
            "cached_until": datetime.utcnow() + timedelta(hours=1),
            "created_at": datetime.utcnow() - timedelta(minutes=4)
        }
    ]


class TestDashboardService:
    """Test dashboard service functionality."""

    def test_create_dashboard(self, app, test_project, test_user):
        """Test dashboard creation."""
        with app.app_context():
            # Insert test data
            app.db.projects.insert_one(test_project)
            
            # Create dashboard data
            dashboard_data = {
                "project_id": str(test_project["_id"]),
                "name": "Test Dashboard",
                "description": "Test dashboard description",
                "canvas": {
                    "width": 1920,
                    "height": 1080,
                    "background_color": "#F5F5F5",
                    "widgets": []
                },
                "settings": {
                    "auto_refresh": False,
                    "refresh_interval_seconds": 60,
                    "theme": {
                        "font_family": "Inter",
                        "primary_color": "#1976D2",
                        "border_radius": 8
                    }
                }
            }
            
            # Create dashboard
            dashboard = dashboard_service.create_dashboard(
                dashboard_data, 
                str(test_user["_id"]), 
                {"user_id": str(test_user["_id"]), "org_ids": [str(test_project["org_id"])]}
            )
            
            # Verify dashboard was created
            assert dashboard["name"] == "Test Dashboard"
            assert dashboard["project_id"] == test_project["_id"]
            assert dashboard["org_id"] == test_project["org_id"]
            assert dashboard["is_public"] is False
            assert dashboard["public_token"] is None
            assert dashboard["canvas"]["width"] == 1920
            assert dashboard["canvas"]["height"] == 1080
            assert dashboard["settings"]["auto_refresh"] is False

    def test_create_dashboard_invalid_project(self, app, test_user):
        """Test dashboard creation with invalid project."""
        with app.app_context():
            dashboard_data = {
                "project_id": str(ObjectId()),
                "name": "Test Dashboard"
            }
            
            with pytest.raises(ValueError, match="Project not found"):
                dashboard_service.create_dashboard(
                    dashboard_data, 
                    str(test_user["_id"]), 
                    {"user_id": str(test_user["_id"]), "org_ids": []}
                )

    def test_save_canvas(self, app, test_project, test_user, test_analysis):
        """Test canvas saving with widgets."""
        with app.app_context():
            # Insert test data
            app.db.projects.insert_one(test_project)
            app.db.analyses.insert_one(test_analysis)
            
            # Create dashboard first
            dashboard_data = {
                "project_id": str(test_project["_id"]),
                "name": "Test Dashboard"
            }
            dashboard = dashboard_service.create_dashboard(
                dashboard_data, 
                str(test_user["_id"]), 
                {"user_id": str(test_user["_id"]), "org_ids": [str(test_project["org_id"])]}
            )
            
            # Create canvas with widgets
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
                        "properties": {"title": "Total Value"},
                        "data_binding": {
                            "analysis_id": str(test_analysis["_id"]),
                            "node_id": "node2",
                            "refresh_mode": "with_dashboard"
                        },
                        "filters": []
                    },
                    {
                        "id": str(uuid.uuid4()),
                        "type": "data_table",
                        "position": {"x": 400, "y": 50},
                        "size": {"width": 500, "height": 300},
                        "z_index": 1,
                        "is_locked": False,
                        "properties": {"title": "Data Table"},
                        "data_binding": {
                            "analysis_id": str(test_analysis["_id"]),
                            "node_id": "node1",
                            "refresh_mode": "with_dashboard"
                        },
                        "filters": []
                    },
                    {
                        "id": str(uuid.uuid4()),
                        "type": "filter_widget",
                        "position": {"x": 50, "y": 300},
                        "size": {"width": 200, "height": 50},
                        "z_index": 1,
                        "is_locked": False,
                        "properties": {"title": "Category Filter"},
                        "filters": []
                    }
                ]
            }
            
            # Save canvas
            result = dashboard_service.save_canvas(
                str(dashboard["_id"]), 
                canvas_data, 
                {"user_id": str(test_user["_id"]), "org_ids": [str(test_project["org_id"])]}
            )
            
            # Verify canvas was saved
            assert result is not None
            dashboard = result["dashboard"]
            assert len(dashboard["canvas"]["widgets"]) == 3
            assert dashboard["canvas"]["background_color"] == "#FFFFFF"
            assert len(dashboard["linked_analysis_ids"]) == 1

    def test_resolve_widget_data(self, app, test_project, test_user, test_analysis, test_analysis_run, test_analysis_result):
        """Test widget data resolution."""
        with app.app_context():
            # Insert test data
            app.db.projects.insert_one(test_project)
            app.db.analyses.insert_one(test_analysis)
            app.db.analysis_runs.insert_one(test_analysis_run)
            for result in test_analysis_result:
                app.db.analysis_results.insert_one(result)
            
            # Create dashboard with widgets
            dashboard_data = {
                "project_id": str(test_project["_id"]),
                "name": "Test Dashboard",
                "canvas": {
                    "width": 1920,
                    "height": 1080,
                    "background_color": "#F5F5F5",
                    "widgets": [
                        {
                            "id": str(uuid.uuid4()),
                            "type": "kpi_card",
                            "position": {"x": 50, "y": 50},
                            "size": {"width": 300, "height": 200},
                            "z_index": 1,
                            "is_locked": False,
                            "properties": {"title": "Total Value"},
                            "data_binding": {
                                "analysis_id": str(test_analysis["_id"]),
                                "node_id": "node2",
                                "refresh_mode": "with_dashboard"
                            },
                            "filters": []
                        },
                        {
                            "id": str(uuid.uuid4()),
                            "type": "data_table",
                            "position": {"x": 400, "y": 50},
                            "size": {"width": 500, "height": 300},
                            "z_index": 1,
                            "is_locked": False,
                            "properties": {"title": "Data Table"},
                            "data_binding": {
                                "analysis_id": str(test_analysis["_id"]),
                                "node_id": "node1",
                                "refresh_mode": "with_dashboard"
                            },
                            "filters": []
                        }
                    ]
                }
            }
            
            dashboard = dashboard_service.create_dashboard(
                dashboard_data, 
                str(test_user["_id"]), 
                {"user_id": str(test_user["_id"]), "org_ids": [str(test_project["org_id"])]}
            )
            
            # Resolve widget data
            widget_data = dashboard_service.resolve_widget_data(dashboard)
            
            # Verify widget data
            assert len(widget_data) == 2
            
            # Check KPI widget data
            kpi_widget_id = dashboard["canvas"]["widgets"][0]["id"]
            kpi_data = widget_data[kpi_widget_id]
            assert kpi_data["status"] == "ok"
            assert kpi_data["data"]["value"] == 450
            
            # Check table widget data
            table_widget_id = dashboard["canvas"]["widgets"][1]["id"]
            table_data = widget_data[table_widget_id]
            assert table_data["status"] == "ok"
            assert len(table_data["data"]["rows"]) == 3

    def test_get_filter_options(self, app, test_project, test_user, test_analysis, test_analysis_run, test_analysis_result):
        """Test filter options retrieval."""
        with app.app_context():
            # Insert test data
            app.db.projects.insert_one(test_project)
            app.db.analyses.insert_one(test_analysis)
            app.db.analysis_runs.insert_one(test_analysis_run)
            for result in test_analysis_result:
                app.db.analysis_results.insert_one(result)
            
            # Get filter options
            filter_options = dashboard_service.get_filter_options(
                str(test_analysis["_id"]),
                "node1",
                "category",
                context={"user_id": str(test_user["_id"]), "org_ids": [str(test_project["org_id"])]}
            )
            
            # Verify filter options
            assert filter_options["column"] == "category"
            assert len(filter_options["values"]) == 2
            assert "A" in filter_options["values"]
            assert "B" in filter_options["values"]
            assert filter_options["total_distinct"] == 2

    def test_enable_public_sharing(self, app, test_project, test_user):
        """Test enabling public sharing."""
        with app.app_context():
            # Insert test data
            app.db.projects.insert_one(test_project)
            
            # Create dashboard
            dashboard_data = {
                "project_id": str(test_project["_id"]),
                "name": "Test Dashboard"
            }
            dashboard = dashboard_service.create_dashboard(
                dashboard_data, 
                str(test_user["_id"]), 
                {"user_id": str(test_user["_id"]), "org_ids": [str(test_project["org_id"])]}
            )
            
            # Enable public sharing
            result = dashboard_service.enable_public_sharing(str(dashboard["_id"]))
            
            # Verify public sharing was enabled
            assert result["is_public"] is True
            assert result["public_token"] is not None
            assert "public_url" in result

    def test_create_snapshot(self, app, test_project, test_user, test_analysis, test_analysis_run, test_analysis_result):
        """Test dashboard snapshot creation."""
        with app.app_context():
            # Insert test data
            app.db.projects.insert_one(test_project)
            app.db.analyses.insert_one(test_analysis)
            app.db.analysis_runs.insert_one(test_analysis_run)
            for result in test_analysis_result:
                app.db.analysis_results.insert_one(result)
            
            # Create dashboard with widgets
            dashboard_data = {
                "project_id": str(test_project["_id"]),
                "name": "Test Dashboard",
                "canvas": {
                    "width": 1920,
                    "height": 1080,
                    "background_color": "#F5F5F5",
                    "widgets": [
                        {
                            "id": str(uuid.uuid4()),
                            "type": "kpi_card",
                            "position": {"x": 50, "y": 50},
                            "size": {"width": 300, "height": 200},
                            "z_index": 1,
                            "is_locked": False,
                            "properties": {"title": "Total Value"},
                            "data_binding": {
                                "analysis_id": str(test_analysis["_id"]),
                                "node_id": "node2",
                                "refresh_mode": "with_dashboard"
                            },
                            "filters": []
                        }
                    ]
                }
            }
            
            dashboard = dashboard_service.create_dashboard(
                dashboard_data, 
                str(test_user["_id"]), 
                {"user_id": str(test_user["_id"]), "org_ids": [str(test_project["org_id"])]}
            )
            
            # Create snapshot
            snapshot = dashboard_service.create_snapshot(
                str(dashboard["_id"]), 
                str(test_user["_id"]), 
                {"user_id": str(test_user["_id"]), "org_ids": [str(test_project["org_id"])]}
            )
            
            # Verify snapshot was created
            assert snapshot is not None
            assert snapshot["dashboard_id"] == dashboard["_id"]
            assert "widget_data" in snapshot["data"]
            assert "canvas_meta" in snapshot["data"]


class TestDashboardRoutes:
    """Test dashboard API routes."""

    def test_create_dashboard_route(self, client, test_project, test_user):
        """Test dashboard creation via API."""
        # Insert test data
        client.app.db.projects.insert_one(test_project)
        
        # Create auth token
        token = "Bearer test-token"
        
        # Create dashboard
        response = client.post(
            "/api/internal/v1/dashboards",
            json={
                "project_id": str(test_project["_id"]),
                "name": "Test Dashboard",
                "description": "Test dashboard description"
            },
            headers={"Authorization": token}
        )
        
        # Verify response
        assert response.status_code == 201
        data = response.get_json()
        assert data["status"] == "success"
        assert "dashboard" in data["data"]

    def test_get_dashboard_route(self, client, test_project, test_user):
        """Test getting dashboard via API."""
        # Insert test data
        client.app.db.projects.insert_one(test_project)
        
        # Create dashboard first
        dashboard_data = {
            "project_id": str(test_project["_id"]),
            "name": "Test Dashboard"
        }
        dashboard = dashboard_service.create_dashboard(
            dashboard_data, 
            str(test_user["_id"]), 
            {"user_id": str(test_user["_id"]), "org_ids": [str(test_project["org_id"])]}
        )
        
        # Create auth token
        token = "Bearer test-token"
        
        # Get dashboard
        response = client.get(
            f"/api/internal/v1/dashboards/{dashboard['_id']}",
            headers={"Authorization": token}
        )
        
        # Verify response
        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "success"
        assert "dashboard" in data["data"]

    def test_save_canvas_route(self, client, test_project, test_user, test_analysis):
        """Test canvas saving via API."""
        # Insert test data
        client.app.db.projects.insert_one(test_project)
        client.app.db.analyses.insert_one(test_analysis)
        
        # Create dashboard first
        dashboard_data = {
            "project_id": str(test_project["_id"]),
            "name": "Test Dashboard"
        }
        dashboard = dashboard_service.create_dashboard(
            dashboard_data, 
            str(test_user["_id"]), 
            {"user_id": str(test_user["_id"]), "org_ids": [str(test_project["org_id"])]}
        )
        
        # Create auth token
        token = "Bearer test-token"
        
        # Save canvas
        canvas_data = {
            "canvas": {
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
                        "properties": {"title": "Total Value"},
                        "data_binding": {
                            "analysis_id": str(test_analysis["_id"]),
                            "node_id": "node2",
                            "refresh_mode": "with_dashboard"
                        },
                        "filters": []
                    }
                ]
            }
        }
        
        response = client.put(
            f"/api/internal/v1/dashboards/{dashboard['_id']}/canvas",
            json=canvas_data,
            headers={"Authorization": token}
        )
        
        # Verify response
        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "success"
        assert "dashboard" in data["data"]

    def test_get_canvas_data_route(self, client, test_project, test_user, test_analysis, test_analysis_run, test_analysis_result):
        """Test getting canvas data via API."""
        # Insert test data
        client.app.db.projects.insert_one(test_project)
        client.app.db.analyses.insert_one(test_analysis)
        client.app.db.analysis_runs.insert_one(test_analysis_run)
        for result in test_analysis_result:
            client.app.db.analysis_results.insert_one(result)
        
        # Create dashboard with widgets
        dashboard_data = {
            "project_id": str(test_project["_id"]),
            "name": "Test Dashboard",
            "canvas": {
                "width": 1920,
                "height": 1080,
                "background_color": "#F5F5F5",
                "widgets": [
                    {
                        "id": str(uuid.uuid4()),
                        "type": "kpi_card",
                        "position": {"x": 50, "y": 50},
                        "size": {"width": 300, "height": 200},
                        "z_index": 1,
                        "is_locked": False,
                        "properties": {"title": "Total Value"},
                        "data_binding": {
                            "analysis_id": str(test_analysis["_id"]),
                            "node_id": "node2",
                            "refresh_mode": "with_dashboard"
                        },
                        "filters": []
                    }
                ]
            }
        }
        
        dashboard = dashboard_service.create_dashboard(
            dashboard_data, 
            str(test_user["_id"]), 
            {"user_id": str(test_user["_id"]), "org_ids": [str(test_project["org_id"])]}
        )
        
        # Create auth token
        token = "Bearer test-token"
        
        # Get canvas data
        response = client.get(
            f"/api/internal/v1/dashboards/{dashboard['_id']}/data",
            headers={"Authorization": token}
        )
        
        # Verify response
        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "success"
        assert "canvas" in data["data"]
        assert "widget_data" in data["data"]

    def test_enable_public_sharing_route(self, client, test_project, test_user):
        """Test enabling public sharing via API."""
        # Insert test data
        client.app.db.projects.insert_one(test_project)
        
        # Create dashboard first
        dashboard_data = {
            "project_id": str(test_project["_id"]),
            "name": "Test Dashboard"
        }
        dashboard = dashboard_service.create_dashboard(
            dashboard_data, 
            str(test_user["_id"]), 
            {"user_id": str(test_user["_id"]), "org_ids": [str(test_project["org_id"])]}
        )
        
        # Create auth token
        token = "Bearer test-token"
        
        # Enable public sharing
        response = client.post(
            f"/api/internal/v1/dashboards/{dashboard['_id']}/public-token",
            headers={"Authorization": token}
        )
        
        # Verify response
        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "success"
        assert data["data"]["is_public"] is True
        assert "public_token" in data["data"]

    def test_get_public_dashboard_route(self, client, test_project, test_user):
        """Test getting public dashboard via API."""
        # Insert test data
        client.app.db.projects.insert_one(test_project)
        
        # Create dashboard first
        dashboard_data = {
            "project_id": str(test_project["_id"]),
            "name": "Test Dashboard"
        }
        dashboard = dashboard_service.create_dashboard(
            dashboard_data, 
            str(test_user["_id"]), 
            {"user_id": str(test_user["_id"]), "org_ids": [str(test_project["org_id"])]}
        )
        
        # Enable public sharing
        public_result = dashboard_service.enable_public_sharing(str(dashboard["_id"]))
        public_token = public_result["public_token"]
        
        # Get public dashboard
        response = client.get(f"/api/v1/public/dashboards/{public_token}")
        
        # Verify response
        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "success"
        assert "dashboard" in data["data"]
        assert "widget_data" in data["data"]

    def test_create_snapshot_route(self, client, test_project, test_user):
        """Test creating snapshot via API."""
        # Insert test data
        client.app.db.projects.insert_one(test_project)
        
        # Create dashboard first
        dashboard_data = {
            "project_id": str(test_project["_id"]),
            "name": "Test Dashboard"
        }
        dashboard = dashboard_service.create_dashboard(
            dashboard_data, 
            str(test_user["_id"]), 
            {"user_id": str(test_user["_id"]), "org_ids": [str(test_project["org_id"])]}
        )
        
        # Create auth token
        token = "Bearer test-token"
        
        # Create snapshot
        response = client.post(
            f"/api/internal/v1/dashboards/{dashboard['_id']}/snapshots",
            headers={"Authorization": token}
        )
        
        # Verify response
        assert response.status_code == 201
        data = response.get_json()
        assert data["status"] == "success"
        assert "snapshot" in data["data"]


class TestDashboardModels:
    """Test dashboard model validation."""

    def test_widget_model_validation(self):
        """Test widget model validation."""
        # Valid widget
        widget_data = {
            "id": str(uuid.uuid4()),
            "type": "kpi_card",
            "position": {"x": 50, "y": 50},
            "size": {"width": 300, "height": 200},
            "z_index": 1,
            "is_locked": False,
            "properties": {"title": "Total Value"}
        }
        
        widget = Widget(**widget_data)
        assert widget.id == widget_data["id"]
        assert widget.type == "kpi_card"
        assert widget.position.x == 50
        assert widget.position.y == 50
        assert widget.size.width == 300
        assert widget.size.height == 200
        
        # Invalid widget ID
        with pytest.raises(ValueError):
            Widget(**{**widget_data, "id": "invalid-uuid"})
        
        # Invalid widget type
        with pytest.raises(ValueError):
            Widget(**{**widget_data, "type": "invalid_type"})

    def test_canvas_model_validation(self):
        """Test canvas model validation."""
        # Valid canvas
        canvas_data = {
            "width": 1920,
            "height": 1080,
            "background_color": "#F5F5F5",
            "widgets": []
        }
        
        canvas = Canvas(**canvas_data)
        assert canvas.width == 1920
        assert canvas.height == 1080
        assert canvas.background_color == "#F5F5F5"
        
        # Invalid width
        with pytest.raises(ValueError):
            Canvas(**{**canvas_data, "width": 700})
        
        # Invalid height
        with pytest.raises(ValueError):
            Canvas(**{**canvas_data, "height": 500})

    def test_dashboard_model_validation(self):
        """Test dashboard model validation."""
        # Valid dashboard
        dashboard_data = {
            "project_id": ObjectId(),
            "name": "Test Dashboard",
            "description": "Test dashboard description",
            "canvas": {
                "width": 1920,
                "height": 1080,
                "background_color": "#F5F5F5",
                "widgets": []
            },
            "settings": {
                "auto_refresh": False,
                "refresh_interval_seconds": 60,
                "theme": {
                    "font_family": "Inter",
                    "primary_color": "#1976D2",
                    "border_radius": 8
                }
            }
        }
        
        dashboard = Dashboard(**dashboard_data)
        assert dashboard.name == "Test Dashboard"
        assert dashboard.project_id == dashboard_data["project_id"]
        assert dashboard.canvas.width == 1920
        assert dashboard.settings.auto_refresh is False
        
        # Invalid name (too long)
        with pytest.raises(ValueError):
            Dashboard(**{**dashboard_data, "name": "A" * 121})
        
        # Invalid refresh interval
        with pytest.raises(ValueError):
            Dashboard(**{**dashboard_data, "settings": {"auto_refresh": True, "refresh_interval_seconds": 5}})