import pytest
from bson import ObjectId
import jwt
from app.services.auth_service import resolve_group_members, get_user_groups_from_claims_or_db, user_has_access_to_resource

def test_tier1_single_rule_condition_matching(db):
    org_id = ObjectId()
    u1_id = ObjectId()
    u2_id = ObjectId()

    # Seed users and memberships
    db.users.insert_many([
        {"_id": u1_id, "email": "alice@company.com", "full_name": "Alice Smith", "status": "active"},
        {"_id": u2_id, "email": "bob@partner.com", "full_name": "Bob Jones", "status": "active"},
    ])
    db.org_memberships.insert_many([
        {"user_id": u1_id, "org_id": org_id, "role": "org_admin", "status": "active", "is_deleted": False},
        {"user_id": u2_id, "org_id": org_id, "role": "org_viewer", "status": "active", "is_deleted": False},
    ])

    group = {
        "_id": ObjectId(),
        "org_id": org_id,
        "type": "dynamic",
        "dynamic_rule": {"field": "role", "operator": "equals", "value": "org_admin"},
        "is_deleted": False
    }

    members = resolve_group_members(group, str(org_id))
    assert str(u1_id) in members
    assert str(u2_id) not in members


def test_tier1_logical_and_rules(db):
    org_id = ObjectId()
    u1_id = ObjectId()
    u2_id = ObjectId()

    db.users.insert_many([
        {"_id": u1_id, "email": "alice@company.com", "full_name": "Alice Smith", "status": "active"},
        {"_id": u2_id, "email": "bob@company.com", "full_name": "Bob Jones", "status": "active"},
    ])
    db.org_memberships.insert_many([
        {"user_id": u1_id, "org_id": org_id, "role": "org_admin", "status": "active", "is_deleted": False},
        {"user_id": u2_id, "org_id": org_id, "role": "org_viewer", "status": "active", "is_deleted": False},
    ])

    rule = {
        "logical_operator": "AND",
        "conditions": [
            {"field": "email", "operator": "ends_with", "value": "@company.com"},
            {"field": "role", "operator": "equals", "value": "org_admin"}
        ]
    }
    group = {"_id": ObjectId(), "org_id": org_id, "type": "dynamic", "dynamic_rule": rule}

    members = resolve_group_members(group, str(org_id))
    assert str(u1_id) in members
    assert str(u2_id) not in members


def test_tier1_logical_or_rules(db):
    org_id = ObjectId()
    u1_id = ObjectId()
    u2_id = ObjectId()

    db.users.insert_many([
        {"_id": u1_id, "email": "alice@company.com", "full_name": "Alice Smith", "status": "active"},
        {"_id": u2_id, "email": "bob@partner.com", "full_name": "Bob Jones", "status": "active"},
    ])
    db.org_memberships.insert_many([
        {"user_id": u1_id, "org_id": org_id, "role": "org_viewer", "status": "active", "is_deleted": False},
        {"user_id": u2_id, "org_id": org_id, "role": "org_viewer", "status": "active", "is_deleted": False},
    ])

    rule = {
        "logical_operator": "OR",
        "conditions": [
            {"field": "email", "operator": "ends_with", "value": "partner.com"},
            {"field": "full_name", "operator": "starts_with", "value": "Alice"}
        ]
    }
    group = {"_id": ObjectId(), "org_id": org_id, "type": "dynamic", "dynamic_rule": rule}

    members = resolve_group_members(group, str(org_id))
    assert str(u1_id) in members
    assert str(u2_id) in members


def test_tier1_logical_not_rules(db):
    org_id = ObjectId()
    u1_id = ObjectId()
    u2_id = ObjectId()

    db.users.insert_many([
        {"_id": u1_id, "email": "alice@company.com", "full_name": "Alice Smith", "status": "active"},
        {"_id": u2_id, "email": "bob@partner.com", "full_name": "Bob Jones", "status": "active"},
    ])
    db.org_memberships.insert_many([
        {"user_id": u1_id, "org_id": org_id, "role": "org_admin", "status": "active", "is_deleted": False},
        {"user_id": u2_id, "org_id": org_id, "role": "org_viewer", "status": "active", "is_deleted": False},
    ])

    rule = {
        "logical_operator": "NOT",
        "conditions": [
            {"field": "role", "operator": "equals", "value": "org_admin"}
        ]
    }
    group = {"_id": ObjectId(), "org_id": org_id, "type": "dynamic", "dynamic_rule": rule}

    members = resolve_group_members(group, str(org_id))
    assert str(u1_id) not in members
    assert str(u2_id) in members


def test_tier1_dynamic_updates_when_data_changes(db):
    org_id = ObjectId()
    u1_id = ObjectId()

    db.users.insert_one({"_id": u1_id, "email": "alice@company.com", "full_name": "Alice Smith", "status": "active"})
    db.org_memberships.insert_one({"user_id": u1_id, "org_id": org_id, "role": "org_viewer", "status": "active", "is_deleted": False})

    group = {
        "_id": ObjectId(),
        "org_id": org_id,
        "type": "dynamic",
        "dynamic_rule": {"field": "role", "operator": "equals", "value": "org_admin"}
    }

    # Initially not in group
    assert str(u1_id) not in resolve_group_members(group, str(org_id))

    # Promote user role in organization membership
    db.org_memberships.update_one({"user_id": u1_id, "org_id": org_id}, {"$set": {"role": "org_admin"}})

    # Membership should update dynamically on next resolution
    assert str(u1_id) in resolve_group_members(group, str(org_id))


def test_tier2_empty_dynamic_rule_handling(db):
    org_id = ObjectId()
    u1_id = ObjectId()

    db.users.insert_one({"_id": u1_id, "email": "alice@company.com", "full_name": "Alice Smith", "status": "active"})
    db.org_memberships.insert_one({"user_id": u1_id, "org_id": org_id, "role": "org_viewer", "status": "active", "is_deleted": False})

    # Empty rule {} should execute safely and not crash
    group = {"_id": ObjectId(), "org_id": org_id, "type": "dynamic", "dynamic_rule": {}}
    members = resolve_group_members(group, str(org_id))
    assert isinstance(members, list)


def test_tier2_case_insensitivity(db):
    org_id = ObjectId()
    u1_id = ObjectId()

    db.users.insert_one({"_id": u1_id, "email": "Alice@Company.com", "full_name": "Alice Smith", "status": "active"})
    db.org_memberships.insert_one({"user_id": u1_id, "org_id": org_id, "role": "org_viewer", "status": "active", "is_deleted": False})

    group = {
        "_id": ObjectId(),
        "org_id": org_id,
        "type": "dynamic",
        "dynamic_rule": {"field": "email", "operator": "ends_with", "value": "@company.com"}
    }
    # "ends_with" ignores case in implementation
    assert str(u1_id) in resolve_group_members(group, str(org_id))


def test_tier2_missing_candidate_field_handling(db):
    org_id = ObjectId()
    u1_id = ObjectId()

    db.users.insert_one({"_id": u1_id, "email": "alice@company.com", "full_name": "Alice Smith", "status": "active"})
    db.org_memberships.insert_one({"user_id": u1_id, "org_id": org_id, "role": "org_viewer", "status": "active", "is_deleted": False})

    # Check rule targeting a non-existent candidate field
    group = {
        "_id": ObjectId(),
        "org_id": org_id,
        "type": "dynamic",
        "dynamic_rule": {"field": "nonexistent_field", "operator": "equals", "value": "some_value"}
    }
    # Should safely evaluate to False instead of throwing Exception
    members = resolve_group_members(group, str(org_id))
    assert str(u1_id) not in members


def test_tier2_in_operator_with_comma_separated_string(db):
    org_id = ObjectId()
    u1_id = ObjectId()
    u2_id = ObjectId()

    db.users.insert_many([
        {"_id": u1_id, "email": "alice@company.com", "full_name": "Alice Smith", "status": "active"},
        {"_id": u2_id, "email": "bob@company.com", "full_name": "Bob Jones", "status": "active"},
    ])
    db.org_memberships.insert_many([
        {"user_id": u1_id, "org_id": org_id, "role": "org_admin", "status": "active", "is_deleted": False},
        {"user_id": u2_id, "org_id": org_id, "role": "org_viewer", "status": "active", "is_deleted": False},
    ])

    group = {
        "_id": ObjectId(),
        "org_id": org_id,
        "type": "dynamic",
        "dynamic_rule": {"field": "role", "operator": "in", "value": "org_admin,org_editor"}
    }

    members = resolve_group_members(group, str(org_id))
    assert str(u1_id) in members
    assert str(u2_id) not in members


def test_tier2_malformed_operator_graceful_recovery(db):
    org_id = ObjectId()
    u1_id = ObjectId()

    db.users.insert_one({"_id": u1_id, "email": "alice@company.com", "full_name": "Alice Smith", "status": "active"})
    db.org_memberships.insert_one({"user_id": u1_id, "org_id": org_id, "role": "org_viewer", "status": "active", "is_deleted": False})

    group = {
        "_id": ObjectId(),
        "org_id": org_id,
        "type": "dynamic",
        "dynamic_rule": {"field": "role", "operator": "super_operator_123", "value": "org_viewer"}
    }
    # Should resolve safely to empty list without raising
    members = resolve_group_members(group, str(org_id))
    assert members == []


def test_tier3_f1_x_f2_dynamic_group_permission_integration(db):
    # F1 x F2 interaction testing via user_has_access_to_resource checking
    user_id = ObjectId()
    org_id = ObjectId()
    project_id = ObjectId()
    dynamic_group_id = ObjectId()

    user_doc = {
        "_id": user_id,
        "email": "analyst@company.com",
        "full_name": "Analyst User",
        "system_role": "user",
        "status": "active"
    }
    db.users.insert_one(user_doc)

    db.org_memberships.insert_one({
        "user_id": user_id,
        "org_id": org_id,
        "role": "org_analyst",
        "status": "active",
        "is_deleted": False,
    })

    # The dynamic group matches org_analyst
    db.groups.insert_one({
        "_id": dynamic_group_id,
        "org_id": org_id,
        "name": "Analysts Dynamic",
        "type": "dynamic",
        "dynamic_rule": {"field": "role", "operator": "equals", "value": "org_analyst"},
        "is_deleted": False,
    })

    # Prepare token claim
    orgs_claim = [{
        "org_id": str(org_id),
        "role": "org_analyst",
        "status": "active",
        "group_ids": [str(dynamic_group_id)]
    }]
    decoded_token = {
        "sub": str(user_id),
        "system_role": "user",
        "orgs": orgs_claim
    }

    # Restrict resource to the dynamic group
    resource = {
        "type": "form",
        "org_id": org_id,
        "project_id": project_id,
        "project_doc": {
            "_id": project_id,
            "org_id": org_id,
            "is_deleted": False
        },
        "form_access": {
            "type": "groups",
            "allowed_group_ids": [str(dynamic_group_id)]
        }
    }

    # Verify access is granted
    assert user_has_access_to_resource(user_doc, decoded_token, resource, "view_responses") is True

    # If the user changes to a non-matching role, access is denied (simulating non-qualifying user)
    decoded_token_no_group = {
        "sub": str(user_id),
        "system_role": "user",
        "orgs": [{
            "org_id": str(org_id),
            "role": "org_viewer",
            "status": "active",
            "group_ids": []
        }]
    }
    # Check permission with non-qualifying token -> returns False due to group restriction
    assert user_has_access_to_resource(user_doc, decoded_token_no_group, resource, "view_responses") is False
