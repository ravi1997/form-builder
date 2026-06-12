import pytest
import datetime
from bson import ObjectId
from app.services.compliance_service import create_legal_hold
from app.services.quota_service import calculate_organization_quota

def test_workflow_1_audited_project_legal_hold_and_blocked_deletion(client, db, get_auth_headers):
    org_id = ObjectId()
    project_id = ObjectId()
    form_id = ObjectId()
    
    # 1. Setup admin user
    user_id = ObjectId()
    user_doc = {
        "_id": user_id,
        "email": "admin@company.com",
        "system_role": "user",
        "status": "active",
        "is_deleted": False
    }
    db.users.insert_one(user_doc)
    db.org_memberships.insert_one({
        "user_id": user_id,
        "org_id": org_id,
        "role": "org_admin",
        "status": "active",
        "is_deleted": False
    })
    db.organisations.insert_one({
        "_id": org_id,
        "name": "Audit Org",
        "status": "active",
        "is_deleted": False
    })
    
    headers = get_auth_headers(user_doc)
    
    # Create project and form in DB
    db.projects.insert_one({"_id": project_id, "org_id": org_id, "is_deleted": False})
    db.forms.insert_one({
        "_id": form_id,
        "org_id": org_id,
        "project_id": project_id,
        "is_deleted": False
    })
    
    # 2. Place project on legal hold
    hold_res = client.post(
        f"/api/orgs/{org_id}/compliance/holds",
        json={
            "name": "Project Audit Hold",
            "description": "Hold all forms under this project",
            "target_type": "project",
            "target_ids": [str(project_id)]
        },
        headers=headers
    )
    assert hold_res.status_code == 201
    hold_id = hold_res.get_json()["data"]["_id"]
    
    # 3. Attempt deleting child form -> should be blocked
    del_res = client.delete(f"/api/internal/v1/forms/{form_id}", headers=headers)
    assert del_res.status_code == 409
    assert del_res.get_json()["code"] == "LEGAL_HOLD_ACTIVE"
    
    # 4. Release hold
    toggle_res = client.put(
        f"/api/compliance/holds/{hold_id}",
        json={"is_active": False},
        headers=headers
    )
    assert toggle_res.status_code == 200
    
    # 5. Delete form -> should succeed
    del_res2 = client.delete(f"/api/internal/v1/forms/{form_id}", headers=headers)
    assert del_res2.status_code == 200
    assert db.forms.find_one({"_id": form_id})["is_deleted"] is True


def test_workflow_2_healthcare_formula_calculation_and_kpi_dashboard_propagation(client, db, get_auth_headers):
    org_id = ObjectId()
    project_id = ObjectId()
    analysis_id = ObjectId()
    run_id = ObjectId()
    node_id = "risk_rate_node"
    widget_uuid = "11111111-2222-3333-4444-555555555555"
    
    user_id = ObjectId()
    user_doc = {
        "_id": user_id,
        "email": "doctor@company.com",
        "system_role": "user",
        "status": "active",
        "is_deleted": False
    }
    db.users.insert_one(user_doc)
    db.org_memberships.insert_one({
        "user_id": user_id,
        "org_id": org_id,
        "role": "org_editor",
        "status": "active",
        "is_deleted": False
    })
    db.organisations.insert_one({
        "_id": org_id,
        "name": "Health Org",
        "status": "active",
        "is_deleted": False
    })
    
    headers = get_auth_headers(user_doc)
    
    # 1. Submit healthcare inputs (simulated by seeding calculated risk values in database)
    db.form_responses.insert_one({
        "org_id": org_id,
        "form_id": ObjectId(),
        "values": {"heart_rate": 110, "respiratory_rate": 22, "calculated_risk": 8.5},
        "submitted_at": datetime.datetime.utcnow()
    })
    
    # 2. Seed calculation results inside an analysis run
    db.analysis_runs.insert_one({
        "_id": run_id,
        "analysis_id": analysis_id,
        "status": "completed",
        "created_at": datetime.datetime.utcnow(),
        "updated_at": datetime.datetime.utcnow()
    })
    db.analysis_results.insert_one({
        "analysis_run_id": run_id,
        "node_id": node_id,
        "status": "success",
        "data": {"out": {"value": 8.5}},
        "updated_at": datetime.datetime.utcnow()
    })
    
    # 3. Create dashboard with KPI widget bound to the analysis output
    dashboard_id = ObjectId()
    db.dashboards.insert_one({
        "_id": dashboard_id,
        "org_id": org_id,
        "project_id": project_id,
        "name": "E2E Health KPI Dashboard",
        "canvas": {
            "width": 1024,
            "height": 768,
            "widgets": [
                {
                    "id": widget_uuid,
                    "type": "kpi_card",
                    "data_binding": {
                        "analysis_id": str(analysis_id),
                        "node_id": node_id
                    }
                }
            ]
        },
        "is_deleted": False
    })
    
    # 4. Access dashboard to check resolved KPI widget data
    dash_res = client.get(f"/api/internal/v1/dashboards/{dashboard_id}/data", headers=headers)
    assert dash_res.status_code == 200
    
    widget_data = dash_res.get_json()["data"]["widget_data"]
    assert widget_uuid in widget_data
    assert widget_data[widget_uuid]["status"] == "ok"
    assert widget_data[widget_uuid]["data"]["value"] == 8.5


def test_workflow_3_member_promotion_and_canvas_layout_customization(client, db, get_auth_headers):
    org_id = ObjectId()
    project_id = ObjectId()
    dashboard_id = ObjectId()
    dynamic_group_id = ObjectId()
    widget_uuid = "22222222-3333-4444-5555-666666666666"
    
    # User starts with viewer role
    user_id = ObjectId()
    user_doc = {
        "_id": user_id,
        "email": "user@company.com",
        "full_name": "E2E User",
        "system_role": "user",
        "status": "active",
        "is_deleted": False
    }
    db.users.insert_one(user_doc)
    
    db.org_memberships.insert_one({
        "user_id": user_id,
        "org_id": org_id,
        "role": "org_viewer",
        "status": "active",
        "is_deleted": False
    })
    db.organisations.insert_one({
        "_id": org_id,
        "name": "Promo Org",
        "status": "active",
        "is_deleted": False
    })
    
    db.dashboards.insert_one({
        "_id": dashboard_id,
        "org_id": org_id,
        "project_id": project_id,
        "name": "Customizable Dashboard",
        "canvas": {"width": 1024, "height": 768, "widgets": []},
        "is_deleted": False
    })
    
    # 1. Update user role in org -> Matches dynamic group rule
    db.org_memberships.update_one(
        {"user_id": user_id, "org_id": org_id},
        {"$set": {"role": "org_editor"}}
    )
    
    db.groups.insert_one({
        "_id": dynamic_group_id,
        "org_id": org_id,
        "name": "Editors Group",
        "type": "dynamic",
        "dynamic_rule": {"field": "role", "operator": "equals", "value": "org_editor"},
        "is_deleted": False
    })
    
    # 2. User logs in (gets updated token containing dynamic group ID)
    headers = get_auth_headers(user_doc)
    
    # 3. User saves updated layout canvas coordinates
    new_canvas = {
        "width": 1200,
        "height": 900,
        "background_color": "#FFFFFF",
        "widgets": [
            {
                "id": widget_uuid,
                "type": "text_label",
                "position": {"x": 100, "y": 150},
                "size": {"width": 200, "height": 50},
                "z_index": 1,
                "properties": {"text": "Updated Layout Title"}
            }
        ]
    }
    
    save_res = client.put(
        f"/api/internal/v1/dashboards/{dashboard_id}/canvas",
        json={"canvas": new_canvas},
        headers=headers
    )
    assert save_res.status_code == 200, save_res.get_json()
    
    # 4. Reload to verify saved coordinates
    reload_res = client.get(f"/api/internal/v1/dashboards/{dashboard_id}/data", headers=headers)
    assert reload_res.status_code == 200
    
    canvas_res = reload_res.get_json()["data"]["canvas"]
    assert canvas_res["width"] == 1200
    assert canvas_res["height"] == 900
    assert canvas_res["widgets"][0]["position"]["x"] == 100


def test_workflow_4_storage_quota_blockage_cleanup_and_recovery(client, db, get_auth_headers):
    org_id = ObjectId()
    project_id = ObjectId()
    
    user_id = ObjectId()
    user_doc = {
        "_id": user_id,
        "email": "admin@company.com",
        "system_role": "user",
        "status": "active",
        "is_deleted": False
    }
    db.users.insert_one(user_doc)
    db.org_memberships.insert_one({
        "user_id": user_id,
        "org_id": org_id,
        "role": "org_admin",
        "status": "active",
        "is_deleted": False
    })
    db.organisations.insert_one({
        "_id": org_id,
        "name": "Quota Org",
        "status": "active",
        "is_deleted": False
    })
    
    headers = get_auth_headers(user_doc)
    
    # 1. Seed quota full
    db.storage_quotas.insert_one({
        "org_id": org_id,
        "quota_bytes": 1000,
        "warning_threshold": 0.8,
        "used_bytes": {"files": 500, "database": 500, "total": 1000},
        "last_calculated_at": datetime.datetime.utcnow()
    })
    
    # 2. Try to create form -> should fail
    create_res = client.post(
        "/api/internal/v1/forms",
        json={
            "name": "Quota E2E Form",
            "org_id": str(org_id),
            "project_id": str(project_id),
            "author_id": str(user_id)
        },
        headers=headers
    )
    assert create_res.status_code == 403
    assert create_res.get_json()["code"] == "QUOTA_EXCEEDED"
    
    # 3. Admin deletes files (simulate by updating used bytes to below limits)
    db.storage_quotas.update_one(
        {"org_id": org_id},
        {"$set": {"used_bytes": {"files": 100, "database": 300, "total": 400}}}
    )
    
    # Recalculate
    calculate_organization_quota(org_id)
    
    # 4. Try to create form again -> should succeed
    create_res2 = client.post(
        "/api/internal/v1/forms",
        json={
            "name": "Recovered E2E Form",
            "org_id": str(org_id),
            "project_id": str(project_id),
            "author_id": str(user_id)
        },
        headers=headers
    )
    assert create_res2.status_code == 201


def test_workflow_5_public_sharing_of_compliance_statistics(client, db):
    org_id = ObjectId()
    project_id = ObjectId()
    analysis_id = ObjectId()
    run_id = ObjectId()
    node_id = "kpi_node"
    widget_uuid = "33333333-4444-5555-6666-777777777777"
    
    # 1. Create a dashboard with public token
    dashboard_id = ObjectId()
    db.dashboards.insert_one({
        "_id": dashboard_id,
        "org_id": org_id,
        "project_id": project_id,
        "name": "Public Statistics",
        "canvas": {
            "width": 1024,
            "height": 768,
            "widgets": [
                {
                    "id": widget_uuid,
                    "type": "kpi_card",
                    "data_binding": {
                        "analysis_id": str(analysis_id),
                        "node_id": node_id
                    }
                }
            ]
        },
        "is_public": True,
        "public_token": "public-compliance-stats-token-123",
        "is_deleted": False
    })
    
    # Seed analysis results
    db.analysis_runs.insert_one({
        "_id": run_id,
        "analysis_id": analysis_id,
        "status": "completed",
        "created_at": datetime.datetime.utcnow(),
        "updated_at": datetime.datetime.utcnow()
    })
    db.analysis_results.insert_one({
        "analysis_run_id": run_id,
        "node_id": node_id,
        "status": "success",
        "data": {"out": {"value": 99.4}},
        "updated_at": datetime.datetime.utcnow()
    })
    
    # 2. Fetch the public dashboard without auth header
    public_res = client.get("/api/v1/public/dashboards/public-compliance-stats-token-123")
    assert public_res.status_code == 200
    
    data = public_res.get_json()["data"]
    
    # Verify dashboard canvas is present and read-only (binding details redacted)
    widgets = data["dashboard"]["canvas"]["widgets"]
    assert len(widgets) == 1
    assert "data_binding" in widgets[0]
    # Data binding should be stripped to only basic config
    assert "analysis_id" not in widgets[0]["data_binding"]
    
    # Verify widget data displays hold numbers/agg metrics correctly
    widget_data = data["widget_data"]
    assert widget_uuid in widget_data
    assert widget_data[widget_uuid]["status"] == "ok"
    assert widget_data[widget_uuid]["data"]["value"] == 99.4
