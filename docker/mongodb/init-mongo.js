// MongoDB initialization script
db = db.getSiblingDB('formbuilder');

// Create admin user
db.createUser({
  user: 'admin',
  pwd: passwordPrompt(),
  roles: [
    {
      role: 'userAdminAnyDatabase',
      db: 'admin'
    },
    'readWriteAnyDatabase'
  ]
});

// Switch to formbuilder database
db = db.getSiblingDB('formbuilder');

// Create application user
db.createUser({
  user: 'formbuilder_app',
  pwd: passwordPrompt(),
  roles: [
    {
      role: 'readWrite',
      db: 'formbuilder'
    }
  ]
});

// Create collections with validation
db.createCollection('system_config');
db.createCollection('audit_logs');
db.createCollection('users');
db.createCollection('organisations');
db.createCollection('org_memberships');
db.createCollection('groups');
db.createCollection('group_members');
db.createCollection('invitations');
db.createCollection('sessions');
db.createCollection('api_keys');
db.createCollection('oauth_clients');
db.createCollection('projects');
db.createCollection('project_members');
db.createCollection('concept_registry');
db.createCollection('plugins');
db.createCollection('plugin_versions');
db.createCollection('component_schemas');
db.createCollection('forms');
db.createCollection('form_commits');
db.createCollection('form_templates');
db.createCollection('form_responses');
db.createCollection('response_drafts');
db.createCollection('file_uploads');
db.createCollection('edit_sessions');
db.createCollection('pending_merges');
db.createCollection('analyses');
db.createCollection('analysis_runs');
db.createCollection('analysis_results');
db.createCollection('analysis_exports');
db.createCollection('dashboards');
db.createCollection('dashboard_snapshots');
db.createCollection('notification_templates');
db.createCollection('notification_rules');
db.createCollection('notification_log');
db.createCollection('webhook_configs');
db.createCollection('webhook_delivery_log');
db.createCollection('compliance_standards');
db.createCollection('org_compliance');
db.createCollection('storage_quotas');

print('Database initialization completed');