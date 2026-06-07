import pytest
import json
import uuid
import datetime
from bson import ObjectId

# Helper to generate UUIDv4 strings
def gen_uuid():
    return str(uuid.uuid4())

def test_dashboard_crud(client, db):
    # Setup dependencies
    project_id = ObjectId()
    db.projects.insert_one({
        "_id": project_id,
        "name": "Test Project",
        "org_id": ObjectId()
    })
    
    # 1. Create Dashboard
    payload = {
        "project_id": str(project_id),
        "name": "My Clinical Dashboard",
        "description": "Visualizing clinic submission data",
        "canvas": {
            "width": 1920,
            "height": 1080,
            "background_color": "#FAFAFA"
        },
        "settings": {
            "auto_refresh": True,
            "refresh_interval_seconds": 30
        }
    }
    
    res = client.post("/api/internal/v1/dashboards", json=payload)
    assert res.status_code == 201
    data = res.get_json()
    assert "dashboard" in data
    dashboard = data["dashboard"]
    assert dashboard["name"] == "My Clinical Dashboard"
    assert dashboard["description"] == "Visualizing clinic submission data"
    assert dashboard["canvas"]["width"] == 1920
    assert dashboard["settings"]["auto_refresh"] is True
    assert dashboard["settings"]["refresh_interval_seconds"] == 30
    assert dashboard["is_deleted"] is False
    dashboard_id = dashboard["_id"]
    
    # Test Create Conflict
    res_conflict = client.post("/api/internal/v1/dashboards", json=payload)
    assert res_conflict.status_code == 409
    assert res_conflict.get_json()["error"]["code"] == "DASHBOARD_NAME_CONFLICT"
    
    # 2. Get Dashboard by ID
    res_get = client.get(f"/api/internal/v1/dashboards/{dashboard_id}")
    assert res_get.status_code == 200
    get_data = res_get.get_json()
    assert get_data["dashboard"]["_id"] == dashboard_id
    assert "linked_analyses" in get_data
    
    # 3. List Dashboards
    res_list = client.get(f"/api/internal/v1/dashboards?project_id={project_id}")
    assert res_list.status_code == 200
    list_data = res_list.get_json()
    assert len(list_data["dashboards"]) == 1
    assert "widgets" not in list_data["dashboards"][0]["canvas"] # Stripped in list
    assert "pagination" in list_data
    
    # 4. Patch Dashboard
    patch_payload = {
        "name": "Updated Dashboard Name",
        "settings": {
            "refresh_interval_seconds": 15
        }
    }
    res_patch = client.patch(f"/api/internal/v1/dashboards/{dashboard_id}", json=patch_payload)
    assert res_patch.status_code == 200
    patch_data = res_patch.get_json()
    assert patch_data["dashboard"]["name"] == "Updated Dashboard Name"
    assert patch_data["dashboard"]["settings"]["refresh_interval_seconds"] == 15
    
    # 5. Soft Delete Dashboard
    res_delete = client.delete(f"/api/internal/v1/dashboards/{dashboard_id}")
    assert res_delete.status_code == 200
    
    # Verify it is deleted (404 on get)
    res_get_deleted = client.get(f"/api/internal/v1/dashboards/{dashboard_id}")
    assert res_get_deleted.status_code == 404
    assert res_get_deleted.get_json()["error"]["code"] == "DASHBOARD_NOT_FOUND"

def test_canvas_save_and_resolution(client, db):
    # Setup
    project_id = ObjectId()
    org_id = ObjectId()
    db.projects.insert_one({"_id": project_id, "org_id": org_id, "name": "Project"})
    
    # Create Dashboard
    db_res = client.post("/api/internal/v1/dashboards", json={
        "project_id": str(project_id),
        "name": "Canvas Dashboard"
    })
    dashboard_id = db_res.get_json()["dashboard"]["_id"]
    
    # Create Analysis & Run
    analysis_id = ObjectId()
    db.analyses.insert_one({
        "_id": analysis_id,
        "name": "Patient Analytics",
        "project_id": project_id,
        "graph": {
            "nodes": [
                {
                    "id": "node_kpi",
                    "type": "scalar_aggregator",
                    "properties": {"title": "Average Heart Rate"}
                },
                {
                    "id": "node_table",
                    "type": "table_generator",
                    "properties": {"title": "Patient List"}
                }
            ]
        }
    })
    
    run_id = ObjectId()
    db.analysis_runs.insert_one({
        "_id": run_id,
        "analysis_id": analysis_id,
        "status": "completed",
        "created_at": datetime.datetime.utcnow().isoformat(),
        "updated_at": datetime.datetime.utcnow().isoformat()
    })
    
    # Insert results
    db.analysis_results.insert_many([
        {
            "analysis_run_id": run_id,
            "node_id": "node_kpi",
            "status": "success",
            "data": {"out": 85.5},
            "updated_at": datetime.datetime.utcnow().isoformat()
        },
        {
            "analysis_run_id": run_id,
            "node_id": "node_table",
            "status": "success",
            "data": {
                "out": {
                    "columns": [{"name": "name", "label": "Name"}, {"name": "dept", "label": "Department"}],
                    "rows": [
                        {"name": "Alice", "dept": "Cardiology"},
                        {"name": "Bob", "dept": "Neurology"},
                        {"name": "Charlie", "dept": "Cardiology"}
                    ]
                }
            },
            "updated_at": datetime.datetime.utcnow().isoformat()
        }
    ])
    
    # Save Canvas
    filter_wid = gen_uuid()
    kpi_wid = gen_uuid()
    table_wid = gen_uuid()
    
    canvas_payload = {
        "canvas": {
            "width": 1920,
            "height": 1080,
            "background_color": "#F0F0F0",
            "widgets": [
                {
                    "id": filter_wid,
                    "type": "filter_widget",
                    "position": {"x": 10, "y": 10},
                    "size": {"width": 200, "height": 80},
                    "z_index": 1,
                    "properties": {
                        "filter_type": "dropdown",
                        "label": "Dept Filter"
                    }
                },
                {
                    "id": kpi_wid,
                    "type": "kpi_card",
                    "position": {"x": 250, "y": 10},
                    "size": {"width": 300, "height": 150},
                    "z_index": 1,
                    "data_binding": {
                        "analysis_id": str(analysis_id),
                        "node_id": "node_kpi",
                        "refresh_mode": "with_dashboard"
                    }
                },
                {
                    "id": table_wid,
                    "type": "data_table",
                    "position": {"x": 10, "y": 200},
                    "size": {"width": 800, "height": 400},
                    "z_index": 2,
                    "data_binding": {
                        "analysis_id": str(analysis_id),
                        "node_id": "node_table",
                        "refresh_mode": "with_dashboard"
                    },
                    "filters": [
                        {
                            "filter_widget_id": filter_wid,
                            "bound_field": "dept"
                        }
                    ]
                }
            ]
        }
    }
    
    res_canvas = client.put(f"/api/internal/v1/dashboards/{dashboard_id}/canvas", json=canvas_payload)
    assert res_canvas.status_code == 200
    
    # Check linked_analysis_ids was populated
    updated_db = db.dashboards.find_one({"_id": ObjectId(dashboard_id)})
    assert ObjectId(analysis_id) in updated_db["linked_analysis_ids"]
    
    # Get Canvas Data (Unfiltered)
    res_data = client.get(f"/api/internal/v1/dashboards/{dashboard_id}/canvas/data")
    assert res_data.status_code == 200
    data = res_data.get_json()
    assert "widget_data" in data
    assert data["widget_data"][kpi_wid]["status"] == "ok"
    assert data["widget_data"][kpi_wid]["data"]["value"] == 85.5
    assert len(data["widget_data"][table_wid]["data"]["rows"]) == 3
    
    # Get Canvas Data (Filtered by Cardiology)
    filter_state = json.dumps({filter_wid: "Cardiology"})
    res_filtered = client.get(f"/api/internal/v1/dashboards/{dashboard_id}/canvas/data?filter_state={filter_state}")
    assert res_filtered.status_code == 200
    filtered_data = res_filtered.get_json()
    # Table rows should be filtered to only 2 Cardiology patients
    assert len(filtered_data["widget_data"][table_wid]["data"]["rows"]) == 2
    assert filtered_data["widget_data"][table_wid]["data"]["rows"][0]["name"] == "Alice"
    assert filtered_data["widget_data"][table_wid]["data"]["rows"][1]["name"] == "Charlie"
    
    # Independent Widget endpoint
    res_widget = client.get(f"/api/internal/v1/dashboards/{dashboard_id}/widgets/{table_wid}/data?filter_state={filter_state}")
    assert res_widget.status_code == 200
    widget_res_data = res_widget.get_json()
    assert widget_res_data["status"] == "ok"
    assert len(widget_res_data["data"]["rows"]) == 2
    
    # Filter options endpoint
    res_opts = client.get(f"/api/internal/v1/dashboards/{dashboard_id}/filter-options?analysis_id={analysis_id}&node_id=node_table&column=dept")
    assert res_opts.status_code == 200
    opts_data = res_opts.get_json()
    assert opts_data["column"] == "dept"
    assert "Cardiology" in opts_data["values"]
    assert "Neurology" in opts_data["values"]

def test_snapshots(client, db):
    # Setup
    project_id = ObjectId()
    db.projects.insert_one({"_id": project_id, "name": "Project"})
    db_res = client.post("/api/internal/v1/dashboards", json={
        "project_id": str(project_id),
        "name": "Snapshot Dashboard"
    })
    dashboard_id = db_res.get_json()["dashboard"]["_id"]
    
    # Create Snapshot
    res_snap = client.post(f"/api/internal/v1/dashboards/{dashboard_id}/snapshots")
    assert res_snap.status_code == 201
    snap_data = res_snap.get_json()
    assert "snapshot" in snap_data
    snapshot_id = snap_data["snapshot"]["_id"]
    
    # List Snapshots
    res_list = client.get(f"/api/internal/v1/dashboards/{dashboard_id}/snapshots")
    assert res_list.status_code == 200
    list_data = res_list.get_json()
    assert len(list_data["snapshots"]) == 1
    assert "widget_data" not in list_data["snapshots"][0]["data"] # Excluded in list
    
    # Get Snapshot
    res_get = client.get(f"/api/internal/v1/dashboards/{dashboard_id}/snapshots/{snapshot_id}")
    assert res_get.status_code == 200
    get_data = res_get.get_json()
    assert get_data["_id"] == snapshot_id
    assert "widget_data" in get_data["data"]
    
    # Delete Snapshot
    res_del = client.delete(f"/api/internal/v1/dashboards/{dashboard_id}/snapshots/{snapshot_id}")
    assert res_del.status_code == 200
    
    res_get_deleted = client.get(f"/api/internal/v1/dashboards/{dashboard_id}/snapshots/{snapshot_id}")
    assert res_get_deleted.status_code == 404

def test_public_sharing(client, db):
    # Setup
    project_id = ObjectId()
    db.projects.insert_one({"_id": project_id, "name": "Project"})
    db_res = client.post("/api/internal/v1/dashboards", json={
        "project_id": str(project_id),
        "name": "Public Dashboard"
    })
    dashboard_id = db_res.get_json()["dashboard"]["_id"]
    
    # Enable Sharing
    res_enable = client.post(f"/api/internal/v1/dashboards/{dashboard_id}/public-token")
    assert res_enable.status_code == 200
    enable_data = res_enable.get_json()
    assert enable_data["is_public"] is True
    token = enable_data["public_token"]
    assert token is not None
    
    # Get Public Dashboard (Unauthenticated)
    res_pub = client.get(f"/api/v1/public/dashboards/{token}")
    assert res_pub.status_code == 200
    pub_data = res_pub.get_json()
    assert "dashboard" in pub_data
    assert pub_data["dashboard"]["name"] == "Public Dashboard"
    # Ensure internal IDs are stripped
    assert "org_id" not in pub_data["dashboard"]
    assert "project_id" not in pub_data["dashboard"]
    
    # Get Public Dashboard Data (Unauthenticated polling)
    res_pub_data = client.get(f"/api/v1/public/dashboards/{token}/data")
    assert res_pub_data.status_code == 200
    pub_data_only = res_pub_data.get_json()
    assert "widget_data" in pub_data_only
    assert "server_time" in pub_data_only
    
    # Revoke Public sharing
    res_revoke = client.delete(f"/api/internal/v1/dashboards/{dashboard_id}/public-token")
    assert res_revoke.status_code == 200
    
    # Try public view again -> should 404
    res_pub_revoked = client.get(f"/api/v1/public/dashboards/{token}")
    assert res_pub_revoked.status_code == 404
