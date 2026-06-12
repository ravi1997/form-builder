#!/usr/bin/env python3
"""
Database migration script for Form Builder Platform.
Creates all MongoDB collections with proper indexes and schema validation.
"""

import os
import sys
from datetime import datetime, timedelta
from pymongo import MongoClient
from pymongo.errors import CollectionInvalid, OperationFailure
from bson import ObjectId
import uuid

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from app.models.base import PyObjectId


class DatabaseMigration:
    """Database migration class for creating collections and indexes."""
    
    def __init__(self, mongo_uri: str, database_name: str = "formbuilder"):
        """Initialize the migration with MongoDB connection."""
        self.client = MongoClient(mongo_uri)
        self.db = self.client[database_name]
        self.database_name = database_name
        
    def run_migration(self):
        """Run the complete database migration."""
        print(f"Starting database migration for '{self.database_name}'...")
        
        # Create all collections with indexes
        self._create_system_collections()
        self._create_identity_collections()
        self._create_project_collections()
        self._create_plugin_collections()
        self._create_form_collections()
        self._create_analysis_collections()
        self._create_dashboard_collections()
        self._create_notification_collections()
        self._create_compliance_collections()
        self._create_storage_collections()
        
        print("Database migration completed successfully!")
        
    def _create_system_collections(self):
        """Create system collections with indexes."""
        print("Creating system collections...")
        
        # system_config collection
        try:
            self.db.create_collection("system_config")
        except CollectionInvalid:
            print("Collection 'system_config' already exists")
        
        self.db.system_config.create_index([("key", 1)], unique=True)
        
        # audit_logs collection
        try:
            self.db.create_collection("audit_logs")
        except CollectionInvalid:
            print("Collection 'audit_logs' already exists")
        
        self.db.audit_logs.create_index([("org_id", 1)])
        self.db.audit_logs.create_index([("entity_type", 1), ("entity_id", 1)])
        self.db.audit_logs.create_index([("actor_id", 1)])
        self.db.audit_logs.create_index([("timestamp", -1)])
        self.db.audit_logs.create_index([("archived", 1)])
        
    def _create_identity_collections(self):
        """Create identity and access collections with indexes."""
        print("Creating identity and access collections...")
        
        # users collection
        try:
            self.db.create_collection("users")
        except CollectionInvalid:
            print("Collection 'users' already exists")
        
        self.db.users.create_index([("email", 1)], unique=True)
        self.db.users.create_index([("org_id", 1)])
        self.db.users.create_index([("status", 1)])
        self.db.users.create_index([("created_at", -1)])
        self.db.users.create_index([("is_deleted", 1), ("deleted_at", 1)])
        
        # organisations collection
        try:
            self.db.create_collection("organisations")
        except CollectionInvalid:
            print("Collection 'organisations' already exists")
        
        self.db.organisations.create_index([("slug", 1)], unique=True)
        self.db.organisations.create_index([("parent_org_id", 1)])
        self.db.organisations.create_index([("org_type", 1)])
        self.db.organisations.create_index([("status", 1)])
        self.db.organisations.create_index([("is_deleted", 1), ("deleted_at", 1)])
        
        # org_memberships collection
        try:
            self.db.create_collection("org_memberships")
        except CollectionInvalid:
            print("Collection 'org_memberships' already exists")
        
        self.db.org_memberships.create_index([("user_id", 1), ("org_id", 1)], unique=True)
        self.db.org_memberships.create_index([("org_id", 1)])
        self.db.org_memberships.create_index([("user_id", 1)])
        self.db.org_memberships.create_index([("status", 1)])
        self.db.org_memberships.create_index([("is_deleted", 1), ("deleted_at", 1)])
        
        # groups collection
        try:
            self.db.create_collection("groups")
        except CollectionInvalid:
            print("Collection 'groups' already exists")
        
        self.db.groups.create_index([("org_id", 1)])
        self.db.groups.create_index([("type", 1)])
        self.db.groups.create_index([("is_deleted", 1), ("deleted_at", 1)])
        
        # group_members collection
        try:
            self.db.create_collection("group_members")
        except CollectionInvalid:
            print("Collection 'group_members' already exists")
        
        self.db.group_members.create_index([("group_id", 1), ("user_id", 1)], unique=True)
        self.db.group_members.create_index([("group_id", 1)])
        self.db.group_members.create_index([("user_id", 1)])
        
        # invitations collection
        try:
            self.db.create_collection("invitations")
        except CollectionInvalid:
            print("Collection 'invitations' already exists")
        
        self.db.invitations.create_index([("token", 1)], unique=True)
        self.db.invitations.create_index([("org_id", 1)])
        self.db.invitations.create_index([("invited_email", 1)])
        self.db.invitations.create_index([("status", 1)])
        self.db.invitations.create_index([("expires_at", 1)], expireAfterSeconds=0)
        
        # sessions collection
        try:
            self.db.create_collection("sessions")
        except CollectionInvalid:
            print("Collection 'sessions' already exists")
        
        self.db.sessions.create_index([("user_id", 1)])
        self.db.sessions.create_index([("expires_at", 1)], expireAfterSeconds=0)
        
        # api_keys collection
        try:
            self.db.create_collection("api_keys")
        except CollectionInvalid:
            print("Collection 'api_keys' already exists")
        
        self.db.api_keys.create_index([("org_id", 1)])
        self.db.api_keys.create_index([("user_id", 1)])
        self.db.api_keys.create_index([("key_hash", 1)], unique=True)
        self.db.api_keys.create_index([("key_prefix", 1)])
        self.db.api_keys.create_index([("status", 1)])
        self.db.api_keys.create_index([("expires_at", 1)])
        self.db.api_keys.create_index([("is_deleted", 1), ("deleted_at", 1)])
        
        # oauth_clients collection
        try:
            self.db.create_collection("oauth_clients")
        except CollectionInvalid:
            print("Collection 'oauth_clients' already exists")
        
        self.db.oauth_clients.create_index([("org_id", 1)])
        self.db.oauth_clients.create_index([("client_id", 1)], unique=True)
        self.db.oauth_clients.create_index([("status", 1)])
        self.db.oauth_clients.create_index([("is_deleted", 1), ("deleted_at", 1)])
        
    def _create_project_collections(self):
        """Create project collections with indexes."""
        print("Creating project collections...")
        
        # projects collection
        try:
            self.db.create_collection("projects")
        except CollectionInvalid:
            print("Collection 'projects' already exists")
        
        self.db.projects.create_index([("owner_org_id", 1)])
        self.db.projects.create_index([("slug", 1)])
        self.db.projects.create_index([("shared_org_ids", 1)])
        self.db.projects.create_index([("status", 1)])
        self.db.projects.create_index([("is_deleted", 1), ("deleted_at", 1)])
        
        # project_members collection
        try:
            self.db.create_collection("project_members")
        except CollectionInvalid:
            print("Collection 'project_members' already exists")
        
        self.db.project_members.create_index([("project_id", 1), ("user_id", 1)], unique=True)
        self.db.project_members.create_index([("project_id", 1)])
        self.db.project_members.create_index([("user_id", 1)])
        self.db.project_members.create_index([("org_id", 1)])
        self.db.project_members.create_index([("is_deleted", 1), ("deleted_at", 1)])
        
    def _create_plugin_collections(self):
        """Create plugin and concept collections with indexes."""
        print("Creating plugin and concept collections...")
        
        # concept_registry collection
        try:
            self.db.create_collection("concept_registry")
        except CollectionInvalid:
            print("Collection 'concept_registry' already exists")
        
        self.db.concept_registry.create_index([("concept_id", 1)], unique=True)
        self.db.concept_registry.create_index([("builder_type", 1)])
        
        # plugins collection
        try:
            self.db.create_collection("plugins")
        except CollectionInvalid:
            print("Collection 'plugins' already exists")
        
        self.db.plugins.create_index([("plugin_id", 1)], unique=True)
        self.db.plugins.create_index([("status", 1)])
        self.db.plugins.create_index([("is_deleted", 1), ("deleted_at", 1)])
        
        # plugin_versions collection
        try:
            self.db.create_collection("plugin_versions")
        except CollectionInvalid:
            print("Collection 'plugin_versions' already exists")
        
        self.db.plugin_versions.create_index([("plugin_id", 1), ("version", 1)], unique=True)
        self.db.plugin_versions.create_index([("status", 1)])
        
        # component_schemas collection
        try:
            self.db.create_collection("component_schemas")
        except CollectionInvalid:
            print("Collection 'component_schemas' already exists")
        
        self.db.component_schemas.create_index([
            ("plugin_id", 1), ("plugin_version", 1), ("component_type", 1)
        ], unique=True)
        self.db.component_schemas.create_index([("concept_id", 1)])
        
    def _create_form_collections(self):
        """Create form collections with indexes."""
        print("Creating form collections...")
        
        # forms collection
        try:
            self.db.create_collection("forms")
        except CollectionInvalid:
            print("Collection 'forms' already exists")
        
        self.db.forms.create_index([("project_id", 1)])
        self.db.forms.create_index([("org_id", 1)])
        self.db.forms.create_index([("is_deleted", 1), ("deleted_at", 1)])
        
        # form_commits collection
        try:
            self.db.create_collection("form_commits")
        except CollectionInvalid:
            print("Collection 'form_commits' already exists")
        
        self.db.form_commits.create_index([("form_id", 1), ("commit_id", 1)], unique=True)
        self.db.form_commits.create_index([("form_id", 1), ("branch", 1)])
        self.db.form_commits.create_index([("author_id", 1)])
        self.db.form_commits.create_index([("timestamp", -1)])
        
        # form_templates collection
        try:
            self.db.create_collection("form_templates")
        except CollectionInvalid:
            print("Collection 'form_templates' already exists")
        
        self.db.form_templates.create_index([("org_id", 1)])
        self.db.form_templates.create_index([("category", 1)])
        self.db.form_templates.create_index([("is_system", 1)])
        self.db.form_templates.create_index([("is_public", 1)])
        self.db.form_templates.create_index([("is_deleted", 1), ("deleted_at", 1)])
        
        # form_responses collection
        try:
            self.db.create_collection("form_responses")
        except CollectionInvalid:
            print("Collection 'form_responses' already exists")
        
        self.db.form_responses.create_index([("form_id", 1), ("commit_id", 1)])
        self.db.form_responses.create_index([("respondent_id", 1)])
        self.db.form_responses.create_index([("status", 1)])
        self.db.form_responses.create_index([("submitted_at", -1)])
        self.db.form_responses.create_index([("org_id", 1)])
        self.db.form_responses.create_index([("is_deleted", 1), ("deleted_at", 1)])
        
        # response_drafts collection
        try:
            self.db.create_collection("response_drafts")
        except CollectionInvalid:
            print("Collection 'response_drafts' already exists")
        
        self.db.response_drafts.create_index([("form_id", 1), ("respondent_id", 1)], unique=True)
        self.db.response_drafts.create_index([("expires_at", 1)], expireAfterSeconds=30*24*60*60)  # 30 days TTL
        
        # file_uploads collection
        try:
            self.db.create_collection("file_uploads")
        except CollectionInvalid:
            print("Collection 'file_uploads' already exists")
        
        self.db.file_uploads.create_index([("org_id", 1)])
        self.db.file_uploads.create_index([("form_id", 1)])
        self.db.file_uploads.create_index([("response_id", 1)])
        self.db.file_uploads.create_index([("upload_status", 1)])
        self.db.file_uploads.create_index([("virus_scan_status", 1)])
        self.db.file_uploads.create_index([("is_deleted", 1), ("deleted_at", 1)])
        
        # edit_sessions collection
        try:
            self.db.create_collection("edit_sessions")
        except CollectionInvalid:
            print("Collection 'edit_sessions' already exists")
        
        self.db.edit_sessions.create_index([("entity_type", 1), ("entity_id", 1)])
        self.db.edit_sessions.create_index([("user_id", 1)])
        self.db.edit_sessions.create_index([("org_id", 1)])
        self.db.edit_sessions.create_index([("last_ping_at", 1)], expireAfterSeconds=60)  # 60 seconds TTL
        
        # pending_merges collection
        try:
            self.db.create_collection("pending_merges")
        except CollectionInvalid:
            print("Collection 'pending_merges' already exists")
        
        self.db.pending_merges.create_index([("form_id", 1), ("branch_name", 1)])
        self.db.pending_merges.create_index([("status", 1)])
        self.db.pending_merges.create_index([("is_deleted", 1), ("deleted_at", 1)])
        
    def _create_analysis_collections(self):
        """Create analysis collections with indexes."""
        print("Creating analysis collections...")
        
        # analyses collection
        try:
            self.db.create_collection("analyses")
        except CollectionInvalid:
            print("Collection 'analyses' already exists")
        
        self.db.analyses.create_index([("project_id", 1)])
        self.db.analyses.create_index([("org_id", 1)])
        self.db.analyses.create_index([("status", 1)])
        self.db.analyses.create_index([("is_deleted", 1), ("deleted_at", 1)])
        
        # analysis_runs collection
        try:
            self.db.create_collection("analysis_runs")
        except CollectionInvalid:
            print("Collection 'analysis_runs' already exists")
        
        self.db.analysis_runs.create_index([("analysis_id", 1)])
        self.db.analysis_runs.create_index([("org_id", 1)])
        self.db.analysis_runs.create_index([("trigger", 1)])
        self.db.analysis_runs.create_index([("status", 1)])
        self.db.analysis_runs.create_index([("created_at", -1)])
        
        # analysis_results collection
        try:
            self.db.create_collection("analysis_results")
        except CollectionInvalid:
            print("Collection 'analysis_results' already exists")
        
        self.db.analysis_results.create_index([("run_id", 1)])
        self.db.analysis_results.create_index([("analysis_id", 1)])
        self.db.analysis_results.create_index([("node_id", 1)])
        self.db.analysis_results.create_index([("org_id", 1)])
        self.db.analysis_results.create_index([("output_type", 1)])
        self.db.analysis_results.create_index([("cached_until", 1)])
        
        # analysis_exports collection
        try:
            self.db.create_collection("analysis_exports")
        except CollectionInvalid:
            print("Collection 'analysis_exports' already exists")
        
        self.db.analysis_exports.create_index([("analysis_id", 1)])
        self.db.analysis_exports.create_index([("run_id", 1)])
        self.db.analysis_exports.create_index([("org_id", 1)])
        self.db.analysis_exports.create_index([("status", 1)])
        self.db.analysis_exports.create_index([("expires_at", 1)], expireAfterSeconds=7*24*60*60)  # 7 days TTL
        self.db.analysis_exports.create_index([("is_deleted", 1), ("deleted_at", 1)])
        
    def _create_dashboard_collections(self):
        """Create dashboard collections with indexes."""
        print("Creating dashboard collections...")
        
        # dashboards collection
        try:
            self.db.create_collection("dashboards")
        except CollectionInvalid:
            print("Collection 'dashboards' already exists")
        
        self.db.dashboards.create_index([("project_id", 1)])
        self.db.dashboards.create_index([("org_id", 1)])
        self.db.dashboards.create_index([("is_public", 1)])
        self.db.dashboards.create_index([("public_token", 1)])
        self.db.dashboards.create_index([("is_deleted", 1), ("deleted_at", 1)])
        
        # dashboard_snapshots collection
        try:
            self.db.create_collection("dashboard_snapshots")
        except CollectionInvalid:
            print("Collection 'dashboard_snapshots' already exists")
        
        self.db.dashboard_snapshots.create_index([("dashboard_id", 1)])
        self.db.dashboard_snapshots.create_index([("org_id", 1)])
        self.db.dashboard_snapshots.create_index([("created_at", -1)])
        
    def _create_notification_collections(self):
        """Create notification collections with indexes."""
        print("Creating notification collections...")
        
        # notification_templates collection
        try:
            self.db.create_collection("notification_templates")
        except CollectionInvalid:
            print("Collection 'notification_templates' already exists")
        
        self.db.notification_templates.create_index([("org_id", 1)])
        self.db.notification_templates.create_index([("event_type", 1)])
        self.db.notification_templates.create_index([("is_system", 1)])
        self.db.notification_templates.create_index([("is_active", 1)])
        self.db.notification_templates.create_index([("is_deleted", 1), ("deleted_at", 1)])
        
        # notification_rules collection
        try:
            self.db.create_collection("notification_rules")
        except CollectionInvalid:
            print("Collection 'notification_rules' already exists")
        
        self.db.notification_rules.create_index([("org_id", 1)])
        self.db.notification_rules.create_index([("project_id", 1)])
        self.db.notification_rules.create_index([("form_id", 1)])
        self.db.notification_rules.create_index([("event_type", 1)])
        self.db.notification_rules.create_index([("is_active", 1)])
        self.db.notification_rules.create_index([("is_deleted", 1), ("deleted_at", 1)])
        
        # notification_log collection
        try:
            self.db.create_collection("notification_log")
        except CollectionInvalid:
            print("Collection 'notification_log' already exists")
        
        self.db.notification_log.create_index([("rule_id", 1)])
        self.db.notification_log.create_index([("org_id", 1)])
        self.db.notification_log.create_index([("recipient_id", 1)])
        self.db.notification_log.create_index([("channel", 1)])
        self.db.notification_log.create_index([("status", 1)])
        self.db.notification_log.create_index([("next_retry_at", 1)])
        self.db.notification_log.create_index([("created_at", -1)])
        
        # webhook_configs collection
        try:
            self.db.create_collection("webhook_configs")
        except CollectionInvalid:
            print("Collection 'webhook_configs' already exists")
        
        self.db.webhook_configs.create_index([("org_id", 1)])
        self.db.webhook_configs.create_index([("form_id", 1)])
        self.db.webhook_configs.create_index([("project_id", 1)])
        self.db.webhook_configs.create_index([("is_active", 1)])
        self.db.webhook_configs.create_index([("is_deleted", 1), ("deleted_at", 1)])
        
        # webhook_delivery_log collection
        try:
            self.db.create_collection("webhook_delivery_log")
        except CollectionInvalid:
            print("Collection 'webhook_delivery_log' already exists")
        
        self.db.webhook_delivery_log.create_index([("webhook_config_id", 1)])
        self.db.webhook_delivery_log.create_index([("org_id", 1)])
        self.db.webhook_delivery_log.create_index([("status", 1)])
        self.db.webhook_delivery_log.create_index([("next_retry_at", 1)])
        self.db.webhook_delivery_log.create_index([("created_at", -1)])
        
    def _create_compliance_collections(self):
        """Create compliance collections with indexes."""
        print("Creating compliance collections...")
        
        # compliance_standards collection
        try:
            self.db.create_collection("compliance_standards")
        except CollectionInvalid:
            print("Collection 'compliance_standards' already exists")
        
        self.db.compliance_standards.create_index([("code", 1)], unique=True)
        self.db.compliance_standards.create_index([("region", 1)])
        self.db.compliance_standards.create_index([("is_system", 1)])
        
        # org_compliance collection
        try:
            self.db.create_collection("org_compliance")
        except CollectionInvalid:
            print("Collection 'org_compliance' already exists")
        
        self.db.org_compliance.create_index([("org_id", 1), ("compliance_id", 1)], unique=True)
        self.db.org_compliance.create_index([("compliance_id", 1)])
        self.db.org_compliance.create_index([("effective_from", 1)])
        
    def _create_storage_collections(self):
        """Create storage collections with indexes."""
        print("Creating storage collections...")
        
        # storage_quotas collection
        try:
            self.db.create_collection("storage_quotas")
        except CollectionInvalid:
            print("Collection 'storage_quotas' already exists")
        
        self.db.storage_quotas.create_index([("org_id", 1)], unique=True)
        self.db.storage_quotas.create_index([("last_calculated_at", 1)])
        
    def close(self):
        """Close the database connection."""
        self.client.close()


if __name__ == "__main__":
    # Get MongoDB URI from environment or use default
    mongo_uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017/formbuilder")
    database_name = os.getenv("DATABASE_NAME", "formbuilder")
    
    # Run the migration
    migration = DatabaseMigration(mongo_uri, database_name)
    try:
        migration.run_migration()
    except Exception as e:
        print(f"Migration failed: {e}")
        sys.exit(1)
    finally:
        migration.close()