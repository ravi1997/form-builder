import os
import pymongo
from pymongo import MongoClient, IndexModel, ASCENDING, DESCENDING
import redis

class MongoDB:
    def __init__(self):
        self.client = None
        self.db = None

    def init_app(self, app):
        mongo_uri = app.config.get("MONGO_URI", "mongodb://localhost:27017/form_builder")
        
        # Support mongomock for testing
        if mongo_uri.startswith("mongomock://"):
            import mongomock
            self.client = mongomock.MongoClient()
            db_name = "form_builder"
        else:
            self.client = MongoClient(mongo_uri)
            # Parse db_name from connection string
            # Handle standard uri options
            path_part = mongo_uri.split("/")[-1]
            db_name = path_part.split("?")[0] or "form_builder"
            
        self.db = self.client[db_name]
        
        # Verify connection on boot with retries
        if not app.config.get("TESTING"):
            import time
            max_retries = 10
            for attempt in range(max_retries):
                try:
                    self.client.admin.command("ping")
                    app.logger.info("MongoDB connection verified successfully.")
                    break
                except Exception as e:
                    app.logger.warning(f"Attempt {attempt + 1}/{max_retries} - Failed to connect to MongoDB: {e}")
                    if attempt == max_retries - 1:
                        app.logger.error("Max retries reached. Exiting.")
                        raise e
                    time.sleep(3)


        # Initialize indexes
        self.init_indexes(app)

    def init_indexes(self, app):
        """Initializes all collections and their corresponding indexes."""
        if not self.db:
            return

        index_specifications = {
            "system_config": [
                IndexModel([("key", ASCENDING)], unique=True)
            ],
            "audit_logs": [
                IndexModel([("org_id", ASCENDING), ("timestamp", DESCENDING)]),
                IndexModel([("entity_type", ASCENDING), ("entity_id", ASCENDING)]),
                IndexModel([("actor_id", ASCENDING), ("timestamp", DESCENDING)]),
                IndexModel([("timestamp", ASCENDING)])
            ],
            "users": [
                IndexModel([("email", ASCENDING)], unique=True),
                IndexModel([("status", ASCENDING)])
            ],
            "organisations": [
                IndexModel([("slug", ASCENDING)], unique=True),
                IndexModel([("parent_org_id", ASCENDING)])
            ],
            "org_memberships": [
                IndexModel([("user_id", ASCENDING), ("org_id", ASCENDING)], unique=True),
                IndexModel([("org_id", ASCENDING)])
            ],
            "groups": [
                IndexModel([("org_id", ASCENDING)])
            ],
            "group_members": [
                IndexModel([("group_id", ASCENDING), ("user_id", ASCENDING)], unique=True)
            ],
            "invitations": [
                IndexModel([("token", ASCENDING)], unique=True),
                IndexModel([("expires_at", ASCENDING)], expireAfterSeconds=0) # TTL index
            ],
            "sessions": [
                IndexModel([("refresh_token_hash", ASCENDING)], unique=True),
                IndexModel([("expires_at", ASCENDING)], expireAfterSeconds=0) # TTL index
            ],
            "api_keys": [
                IndexModel([("key_hash", ASCENDING)], unique=True),
                IndexModel([("org_id", ASCENDING)])
            ],
            "oauth_clients": [
                IndexModel([("client_id", ASCENDING)], unique=True)
            ],
            "projects": [
                IndexModel([("org_id", ASCENDING)]),
                IndexModel([("slug", ASCENDING)])
            ],
            "project_members": [
                IndexModel([("project_id", ASCENDING), ("user_id", ASCENDING)], unique=True)
            ],
            "concept_registry": [
                IndexModel([("concept_id", ASCENDING)], unique=True)
            ],
            "plugins": [
                IndexModel([("plugin_id", ASCENDING)], unique=True)
            ],
            "plugin_versions": [
                IndexModel([("plugin_id", ASCENDING), ("version", ASCENDING)], unique=True)
            ],
            "component_schemas": [
                IndexModel([("plugin_id", ASCENDING), ("component_type", ASCENDING)], unique=True)
            ],
            "form_templates": [
                IndexModel([("category", ASCENDING)]),
                IndexModel([("org_id", ASCENDING)])
            ],
            "form_responses": [
                IndexModel([("form_id", ASCENDING), ("submitted_at", DESCENDING)]),
                IndexModel([("respondent_id", ASCENDING)]),
                IndexModel([("org_id", ASCENDING)])
            ],
            "response_drafts": [
                IndexModel([("form_id", ASCENDING), ("respondent_id", ASCENDING)], unique=True),
                IndexModel([("expires_at", ASCENDING)], expireAfterSeconds=0) # TTL index
            ],
            "file_uploads": [
                IndexModel([("org_id", ASCENDING)]),
                IndexModel([("form_id", ASCENDING)]),
                IndexModel([("response_id", ASCENDING)])
            ],
            "edit_sessions": [
                IndexModel([("last_ping_at", ASCENDING)], expireAfterSeconds=60) # TTL index
            ],
            "pending_merges": [
                IndexModel([("form_id", ASCENDING), ("status", ASCENDING)])
            ],
            "analyses": [
                IndexModel([("project_id", ASCENDING)]),
                IndexModel([("org_id", ASCENDING)])
            ],
            "analysis_runs": [
                IndexModel([("analysis_id", ASCENDING), ("created_at", DESCENDING)])
            ],
            "dashboards": [
                IndexModel([("org_id", ASCENDING)]),
                IndexModel([("project_id", ASCENDING)]),
                IndexModel([("public_token", ASCENDING)], sparse=True, unique=True),
                IndexModel([("is_deleted", ASCENDING)])
            ],
            "dashboard_snapshots": [
                IndexModel([("dashboard_id", ASCENDING), ("created_at", DESCENDING)])
            ]
        }

        for collection_name, indexes in index_specifications.items():
            try:
                self.db[collection_name].create_indexes(indexes)
                app.logger.info(f"Initialized indexes for collection: {collection_name}")
            except Exception as e:
                app.logger.error(f"Failed to initialize indexes for {collection_name}: {e}")
                if not app.config.get("TESTING"):
                    raise e

mongo = MongoDB()
redis_client = None

def init_redis(app):
    global redis_client
    redis_uri = app.config.get("REDIS_URI", "redis://localhost:6379/0")
    if not app.config.get("TESTING"):
        try:
            redis_client = redis.from_url(redis_uri)
            redis_client.ping()
            app.logger.info("Redis connection verified successfully.")
        except Exception as e:
            app.logger.error(f"Failed to connect to Redis: {e}")
            raise e
    else:
        # Mock redis for testing if needed or use simple strict redis client
        redis_client = redis.from_url(redis_uri)
