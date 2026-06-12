import json
import pytest
from bson import ObjectId

def test_create_form_and_commit(client):
    # 1. Create a form
    res = client.post("/api/internal/v1/forms", json={
        "name": "Test Intake Form",
        "description": "A form to test version control features",
        "project_id": str(ObjectId()),
        "org_id": str(ObjectId())
    })
    assert res.status_code == 201
    data = res.get_json()["data"]
    form_id = data["form_id"]
    assert "main" in data["branches"]
    init_commit_id = data["branches"]["main"]
    assert len(init_commit_id) == 12

    # 2. Get the initial schema
    res = client.get(f"/api/internal/v1/forms/{form_id}/branches/main/schema")
    assert res.status_code == 200
    schema_data = res.get_json()["data"]
    assert schema_data["commit_id"] == init_commit_id
    assert schema_data["branch"] == "main"
    assert schema_data["schema"]["ui"]["layout"] == "single_page"

    # 3. Create a commit on main
    new_schema = dict(schema_data["schema"])
    new_schema["ui"]["theme"]["primary_color"] = "#FF5722"
    new_schema["sections"] = [
        {
            "id": "sec_1",
            "title": "Registration",
            "sub_sections": [
                {
                    "id": "ssec_1",
                    "questions": [
                        {
                            "id": "q_1",
                            "type": "text_input",
                            "label": "Full Name",
                            "required": True,
                            "properties": {}
                        }
                    ]
                }
            ]
        }
    ]

    res = client.post(f"/api/internal/v1/forms/{form_id}/commits", json={
        "branch": "main",
        "message": "Add registration section",
        "schema": new_schema
    })
    assert res.status_code == 200
    commit_data = res.get_json()["data"]
    new_commit_id = commit_data["commit_id"]
    assert len(new_commit_id) == 12
    assert new_commit_id != init_commit_id

def test_branch_operations(client):
    # Create Form
    res = client.post("/api/internal/v1/forms", json={
        "name": "Branching Form",
        "project_id": str(ObjectId()),
        "org_id": str(ObjectId())
    })
    form_id = res.get_json()["data"]["form_id"]
    init_commit_id = res.get_json()["data"]["branches"]["main"]

    # 1. Create a new branch 'dev'
    res = client.post(f"/api/internal/v1/forms/{form_id}/branches", json={
        "name": "dev",
        "from_branch": "main"
    })
    assert res.status_code == 201
    assert res.get_json()["data"]["name"] == "dev"
    assert res.get_json()["data"]["commit_id"] == init_commit_id

    # 2. Duplicate branch creation should fail
    res = client.post(f"/api/internal/v1/forms/{form_id}/branches", json={
        "name": "dev",
        "from_branch": "main"
    })
    assert res.status_code == 400

    # 3. Delete branch constraints
    # Cannot delete main
    res = client.delete(f"/api/internal/v1/forms/{form_id}/branches/main")
    assert res.status_code == 400

    # Cannot delete production branch
    res = client.delete(f"/api/internal/v1/forms/{form_id}/branches/main")
    assert res.status_code == 400

    # 4. Successfully delete dev
    res = client.delete(f"/api/internal/v1/forms/{form_id}/branches/dev")
    assert res.status_code == 200
    assert "deleted successfully" in res.get_json()["message"]

def test_publish_branch(client):
    # Create Form
    res = client.post("/api/internal/v1/forms", json={
        "name": "Publishing Form",
        "project_id": str(ObjectId()),
        "org_id": str(ObjectId())
    })
    form_id = res.get_json()["data"]["form_id"]
    
    # Create dev branch
    client.post(f"/api/internal/v1/forms/{form_id}/branches", json={"name": "dev"})
    
    # Publish dev branch
    res = client.post(f"/api/internal/v1/forms/{form_id}/publish", json={"branch": "dev"})
    assert res.status_code == 200
    assert res.get_json()["data"]["production_branch"] == "dev"

    # Verify we can no longer delete dev
    res = client.delete(f"/api/internal/v1/forms/{form_id}/branches/dev")
    assert res.status_code == 400

def test_three_way_merge_auto(client, db):
    # Setup a common base commit
    res = client.post("/api/internal/v1/forms", json={
        "name": "Merge Form",
        "project_id": str(ObjectId()),
        "org_id": str(ObjectId())
    })
    form_id = res.get_json()["data"]["form_id"]
    init_commit_id = res.get_json()["data"]["branches"]["main"]

    base_schema = {
        "ui": {"theme": {"primary_color": "#2196F3"}, "layout": "single_page"},
        "access": {"allow_anonymous": True},
        "settings": {},
        "sections": [
            {
                "id": "sec_1",
                "title": "Section 1",
                "sub_sections": [
                    {
                        "id": "ssec_1",
                        "questions": [
                            {
                                "id": "q_1",
                                "type": "text_input",
                                "label": "First Name"
                            }
                        ]
                    }
                ]
            }
        ]
    }

    # Commit base schema to main
    res = client.post(f"/api/internal/v1/forms/{form_id}/commits", json={
        "branch": "main",
        "message": "Set base schema",
        "schema": base_schema
    })
    base_commit_id = res.get_json()["data"]["commit_id"]

    # Create dev branch from this base commit
    client.post(f"/api/internal/v1/forms/{form_id}/branches", json={
        "name": "dev",
        "from_commit_id": base_commit_id
    })

    # Target branch (main) changes: change theme color, add q_2
    schema_A = dict(base_schema)
    schema_A["ui"] = {"theme": {"primary_color": "#AABBCC"}, "layout": "single_page"}
    schema_A["sections"] = [
        {
            "id": "sec_1",
            "title": "Section 1",
            "sub_sections": [
                {
                    "id": "ssec_1",
                    "questions": [
                        {
                            "id": "q_1",
                            "type": "text_input",
                            "label": "First Name"
                        },
                        {
                            "id": "q_2",
                            "type": "text_input",
                            "label": "Last Name"
                        }
                    ]
                }
            ]
        }
    ]
    client.post(f"/api/internal/v1/forms/{form_id}/commits", json={
        "branch": "main",
        "schema": schema_A,
        "message": "Main change"
    })

    # Source branch (dev) changes: change access configuration, add q_3
    schema_B = dict(base_schema)
    schema_B["access"] = {"allow_anonymous": False}
    schema_B["sections"] = [
        {
            "id": "sec_1",
            "title": "Section 1",
            "sub_sections": [
                {
                    "id": "ssec_1",
                    "questions": [
                        {
                            "id": "q_1",
                            "type": "text_input",
                            "label": "First Name"
                        },
                        {
                            "id": "q_3",
                            "type": "text_input",
                            "label": "Email Address"
                        }
                    ]
                }
            ]
        }
    ]
    client.post(f"/api/internal/v1/forms/{form_id}/commits", json={
        "branch": "dev",
        "schema": schema_B,
        "message": "Dev change"
    })

    # Merge dev into main (source = dev, target = main)
    res = client.post(f"/api/internal/v1/forms/{form_id}/merge", json={
        "source_branch": "dev",
        "target_branch": "main",
        "author_id": str(ObjectId())
    })
    assert res.status_code == 200
    data = res.get_json()["data"]
    assert data["status"] == "merged"
    merge_commit_id = data["commit_id"]

    # Verify merged schema
    res = client.get(f"/api/internal/v1/forms/{form_id}/branches/main/schema")
    merged_schema = res.get_json()["data"]["schema"]
    # ui layout should be single_page (from A/base)
    assert merged_schema["ui"]["layout"] == "single_page"
    # theme color should be #AABBCC (from A)
    assert merged_schema["ui"]["theme"]["primary_color"] == "#AABBCC"
    # access allow_anonymous should be False (from B)
    assert merged_schema["access"]["allow_anonymous"] is False
    # sections should contain both q_2 and q_3
    qs = merged_schema["sections"][0]["sub_sections"][0]["questions"]
    q_ids = [q["id"] for q in qs]
    assert "q_1" in q_ids
    assert "q_2" in q_ids
    assert "q_3" in q_ids

def test_three_way_merge_conflict(client):
    # Setup form
    res = client.post("/api/internal/v1/forms", json={
        "name": "Conflict Form",
        "project_id": str(ObjectId()),
        "org_id": str(ObjectId())
    })
    form_id = res.get_json()["data"]["form_id"]
    
    base_schema = {
        "ui": {"theme": {"primary_color": "#2196F3"}, "layout": "single_page"},
        "sections": []
    }
    res = client.post(f"/api/internal/v1/forms/{form_id}/commits", json={
        "branch": "main",
        "schema": base_schema,
        "message": "Base"
    })
    base_commit_id = res.get_json()["data"]["commit_id"]

    # Create dev branch
    client.post(f"/api/internal/v1/forms/{form_id}/branches", json={
        "name": "dev",
        "from_commit_id": base_commit_id
    })

    # Modify main theme color to red
    schema_A = {
        "ui": {"theme": {"primary_color": "#FF0000"}, "layout": "single_page"},
        "sections": []
    }
    client.post(f"/api/internal/v1/forms/{form_id}/commits", json={
        "branch": "main",
        "schema": schema_A,
        "message": "Change color to red"
    })

    # Modify dev theme color to green
    schema_B = {
        "ui": {"theme": {"primary_color": "#00FF00"}, "layout": "single_page"},
        "sections": []
    }
    client.post(f"/api/internal/v1/forms/{form_id}/commits", json={
        "branch": "dev",
        "schema": schema_B,
        "message": "Change color to green"
    })

    # Merge dev into main
    res = client.post(f"/api/internal/v1/forms/{form_id}/merge", json={
        "source_branch": "dev",
        "target_branch": "main"
    })
    assert res.status_code == 409
    err = res.get_json()
    assert err["code"] == "MERGE_CONFLICT"
    assert "ui" in err["details"]["conflict_fields"]
    assert "pending_merge_id" in err["details"]

def test_style_presets(client):
    res = client.get("/api/internal/v1/forms/presets")
    assert res.status_code == 200
    presets = res.get_json()["data"]
    assert len(presets) == 3
    assert presets[0]["id"] == "sleek_dark"
    assert "primary_color" in presets[0]["tokens"]
    assert "custom_css" in presets[0]

def test_custom_css_validation(client):
    # Create Form
    res = client.post("/api/internal/v1/forms", json={
        "name": "Validation Form",
        "project_id": str(ObjectId()),
        "org_id": str(ObjectId())
    })
    form_id = res.get_json()["data"]["form_id"]
    
    # Commit with invalid custom_css (script tag)
    schema = {
        "ui": {
            "theme": {
                "custom_css": ".form { font-size: 14px; } <script>alert(1)</script>"
            }
        },
        "sections": []
    }
    res = client.post(f"/api/internal/v1/forms/{form_id}/commits", json={
        "branch": "main",
        "schema": schema,
        "message": "Inject script"
    })
    assert res.status_code == 400
    assert "forbidden HTML/script tags" in res.get_json()["message"]

    # Commit with invalid custom_css (too large)
    large_schema = {
        "ui": {
            "theme": {
                "custom_css": "a" * 10001
            }
        },
        "sections": []
    }
    res = client.post(f"/api/internal/v1/forms/{form_id}/commits", json={
        "branch": "main",
        "schema": large_schema,
        "message": "Too large css"
    })
    assert res.status_code == 400
    assert "exceeds size limit" in res.get_json()["message"]

    # Commit with valid custom_css
    valid_schema = {
        "ui": {
            "theme": {
                "custom_css": ".form { background-color: red; }"
            }
        },
        "sections": []
    }
    res = client.post(f"/api/internal/v1/forms/{form_id}/commits", json={
        "branch": "main",
        "schema": valid_schema,
        "message": "Valid custom css"
    })
    assert res.status_code == 200


def test_notifications_settings_validation(client):
    # Create Form
    res = client.post("/api/internal/v1/forms", json={
        "name": "Validation Form",
        "project_id": str(ObjectId()),
        "org_id": str(ObjectId())
    })
    form_id = res.get_json()["data"]["form_id"]

    # 1. Valid notifications configuration
    valid_schema = {
        "settings": {
            "notifications": {
                "email_alerts": {
                    "enabled": True,
                    "trigger_event": "on_submission",
                    "recipients": ["user@example.com", "admin@company.org"],
                    "include_payload": True,
                    "include_attachments": False
                },
                "webhook_delivery": {
                    "enabled": True,
                    "url": "https://api.external.com/v1/webhook",
                    "secret": "my-secret-key-12345",
                    "content_type": "application/json"
                },
                "internal_recipients": {
                    "enabled": True,
                    "user_ids": [str(ObjectId()), str(ObjectId())],
                    "team_ids": ["team_a", "team_b"]
                },
                "failure_handling": {
                    "retry_attempts": 3,
                    "alert_owner_on_failure": True
                }
            }
        },
        "sections": []
    }
    res = client.post(f"/api/internal/v1/forms/{form_id}/commits", json={
        "branch": "main",
        "schema": valid_schema,
        "message": "Valid notifications schema"
    })
    assert res.status_code == 200

    # 2. Invalid Email: Bad format
    bad_email_schema = {
        "settings": {
            "notifications": {
                "email_alerts": {
                    "enabled": True,
                    "recipients": ["not-an-email"]
                }
            }
        },
        "sections": []
    }
    res = client.post(f"/api/internal/v1/forms/{form_id}/commits", json={
        "branch": "main",
        "schema": bad_email_schema,
        "message": "Bad email"
    })
    assert res.status_code == 400
    assert "Invalid email address" in res.get_json()["message"]

    # 3. Invalid Email: Too many emails (> 20)
    too_many_emails_schema = {
        "settings": {
            "notifications": {
                "email_alerts": {
                    "enabled": True,
                    "recipients": [f"user{i}@example.com" for i in range(21)]
                }
            }
        },
        "sections": []
    }
    res = client.post(f"/api/internal/v1/forms/{form_id}/commits", json={
        "branch": "main",
        "schema": too_many_emails_schema,
        "message": "Too many emails"
    })
    assert res.status_code == 400
    assert "cannot contain more than 20" in res.get_json()["message"]

    # 4. Invalid Webhook: SSRF Localhost
    ssrf_schema = {
        "settings": {
            "notifications": {
                "webhook_delivery": {
                    "enabled": True,
                    "url": "http://localhost/endpoint"
                }
            }
        },
        "sections": []
    }
    res = client.post(f"/api/internal/v1/forms/{form_id}/commits", json={
        "branch": "main",
        "schema": ssrf_schema,
        "message": "SSRF check"
    })
    assert res.status_code == 400
    assert "cannot point to a local hostname" in res.get_json()["message"]

    # 5. Invalid Webhook: Local IP
    ssrf_ip_schema = {
        "settings": {
            "notifications": {
                "webhook_delivery": {
                    "enabled": True,
                    "url": "http://192.168.1.100/endpoint"
                }
            }
        },
        "sections": []
    }
    res = client.post(f"/api/internal/v1/forms/{form_id}/commits", json={
        "branch": "main",
        "schema": ssrf_ip_schema,
        "message": "SSRF IP check"
    })
    assert res.status_code == 400
    assert "cannot point to a private IP" in res.get_json()["message"]

    # 6. Invalid Webhook: Non HTTP/HTTPS
    ftp_schema = {
        "settings": {
            "notifications": {
                "webhook_delivery": {
                    "enabled": True,
                    "url": "ftp://files.example.com"
                }
            }
        },
        "sections": []
    }
    res = client.post(f"/api/internal/v1/forms/{form_id}/commits", json={
        "branch": "main",
        "schema": ftp_schema,
        "message": "FTP URL check"
    })
    assert res.status_code == 400
    assert "must use http:// or https://" in res.get_json()["message"]

    # 7. Invalid Webhook: Secret too long
    long_secret_schema = {
        "settings": {
            "notifications": {
                "webhook_delivery": {
                    "enabled": True,
                    "url": "https://api.example.com",
                    "secret": "s" * 129
                }
            }
        },
        "sections": []
    }
    res = client.post(f"/api/internal/v1/forms/{form_id}/commits", json={
        "branch": "main",
        "schema": long_secret_schema,
        "message": "Long secret check"
    })
    assert res.status_code == 400
    assert "secret cannot exceed 128 characters" in res.get_json()["message"]

    # 8. Invalid Internal Recipients: Bad ObjectID
    bad_uid_schema = {
        "settings": {
            "notifications": {
                "internal_recipients": {
                    "enabled": True,
                    "user_ids": ["not-an-object-id"],
                    "team_ids": []
                }
            }
        },
        "sections": []
    }
    res = client.post(f"/api/internal/v1/forms/{form_id}/commits", json={
        "branch": "main",
        "schema": bad_uid_schema,
        "message": "Bad UID check"
    })
    assert res.status_code == 400
    assert "Invalid user_id format" in res.get_json()["message"]

    # 9. Invalid Failure Handling: Too many retries
    bad_retries_schema = {
        "settings": {
            "notifications": {
                "failure_handling": {
                    "retry_attempts": 6
                }
            }
        },
        "sections": []
    }
    res = client.post(f"/api/internal/v1/forms/{form_id}/commits", json={
        "branch": "main",
        "schema": bad_retries_schema,
        "message": "Bad retries check"
    })
    assert res.status_code == 400
    assert "retry_attempts must be an integer between 0 and 5" in res.get_json()["message"]


def test_analytics_settings_validation(client):
    # Create Form
    res = client.post("/api/internal/v1/forms", json={
        "name": "Analytics Validation Form",
        "project_id": str(ObjectId()),
        "org_id": str(ObjectId())
    })
    form_id = res.get_json()["data"]["form_id"]

    # 1. Valid analytics configuration
    valid_schema = {
        "settings": {
            "analytics": {
                "enabled": True,
                "start_event_type": "first_interaction",
                "end_event_type": "submit_success",
                "drop_off_enabled": True,
                "timing_enabled": True,
                "utm_capture_enabled": True
            }
        },
        "sections": []
    }
    res = client.post(f"/api/internal/v1/forms/{form_id}/commits", json={
        "branch": "main",
        "schema": valid_schema,
        "message": "Valid analytics schema"
    })
    assert res.status_code == 200

    # 2. Invalid start_event_type
    bad_start_schema = {
        "settings": {
            "analytics": {
                "start_event_type": "invalid_event"
            }
        },
        "sections": []
    }
    res = client.post(f"/api/internal/v1/forms/{form_id}/commits", json={
        "branch": "main",
        "schema": bad_start_schema,
        "message": "Bad start event"
    })
    assert res.status_code == 400
    assert "analytics.start_event_type must be" in res.get_json()["message"]

    # 3. Invalid end_event_type
    bad_end_schema = {
        "settings": {
            "analytics": {
                "end_event_type": "invalid_end_event"
            }
        },
        "sections": []
    }
    res = client.post(f"/api/internal/v1/forms/{form_id}/commits", json={
        "branch": "main",
        "schema": bad_end_schema,
        "message": "Bad end event"
    })
    assert res.status_code == 400
    assert "analytics.end_event_type must be" in res.get_json()["message"]



