import os
from datetime import timedelta


class Config:
    # Basic Flask Configuration
    SECRET_KEY = os.environ.get("SECRET_KEY", "default-secret-key-change-in-prod")
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "jwt-secret-key-change-in-prod")
    FLASK_ENV = os.environ.get("FLASK_ENV", "development")
    
    # Database Configuration
    MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017/form_builder")
    REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    ELASTICSEARCH_URL = os.environ.get("ELASTICSEARCH_URL", "http://localhost:9200")
    
    # Redis Database Selection
    REDIS_CACHE_DB = int(os.environ.get("REDIS_CACHE_DB", 0))
    REDIS_SESSION_DB = int(os.environ.get("REDIS_SESSION_DB", 1))
    REDIS_RATE_LIMIT_DB = int(os.environ.get("REDIS_RATE_LIMIT_DB", 2))
    REDIS_PRESENCE_DB = int(os.environ.get("REDIS_PRESENCE_DB", 3))
    
    # Redis Configuration
    REDIS_CACHE_TTL_SECONDS = int(os.environ.get("REDIS_CACHE_TTL_SECONDS", 3600))
    REDIS_SESSION_TTL_SECONDS = int(os.environ.get("REDIS_SESSION_TTL_SECONDS", 2592000))
    
    # Elasticsearch Configuration
    ELASTICSEARCH_INDEX_PREFIX = os.environ.get("ELASTICSEARCH_INDEX_PREFIX", "formbuilder")
    ELASTICSEARCH_MAX_RESULT_WINDOW = int(os.environ.get("ELASTICSEARCH_MAX_RESULT_WINDOW", 10000))
    ELASTICSEARCH_REFRESH_INTERVAL = os.environ.get("ELASTICSEARCH_REFRESH_INTERVAL", "1s")
    ELASTICSEARCH_NUMBER_OF_SHARDS = int(os.environ.get("ELASTICSEARCH_NUMBER_OF_SHARDS", 1))
    ELASTICSEARCH_NUMBER_OF_REPLICAS = int(os.environ.get("ELASTICSEARCH_NUMBER_OF_REPLICAS", 1))
    
    # Celery Configuration
    CELERY_BROKER_URL = REDIS_URL
    CELERY_RESULT_BACKEND = REDIS_URL
    CELERY_CONCURRENCY = int(os.environ.get("CELERY_CONCURRENCY", 4))
    
    # Email/SMS API Configuration
    EMAIL_API_URL = os.environ.get("EMAIL_API_URL")
    EMAIL_API_TOKEN = os.environ.get("EMAIL_API_TOKEN")
    SMS_API_URL = os.environ.get("SMS_API_URL")
    SMS_API_TOKEN = os.environ.get("SMS_API_TOKEN")
    
    # File Upload Configuration
    UPLOADS_ROOT = os.environ.get("UPLOADS_ROOT", "/var/uploads")
    MAX_UPLOAD_SIZE_PDF = int(os.environ.get("MAX_UPLOAD_SIZE_PDF", 52428800))  # 50MB
    MAX_UPLOAD_SIZE_VIDEO = int(os.environ.get("MAX_UPLOAD_SIZE_VIDEO", 314572800))  # 300MB
    MAX_UPLOAD_SIZE_IMAGE = int(os.environ.get("MAX_UPLOAD_SIZE_IMAGE", 52428800))  # 50MB
    MAX_UPLOAD_SIZE_OTHER = int(os.environ.get("MAX_UPLOAD_SIZE_OTHER", 104857600))  # 100MB
    
    # Plugin System Configuration
    PLUGINS_ENABLED = os.environ.get("PLUGINS_ENABLED", "true").lower() == "true"
    PLUGINS_SANDBOX_ENABLED = os.environ.get("PLUGINS_SANDBOX_ENABLED", "true").lower() == "true"
    PLUGINS_ALLOWED_PERMISSIONS = os.environ.get("PLUGINS_ALLOWED_PERMISSIONS", "db_read_own_org,db_write_own_org,internet_access,filesystem_read,filesystem_write").split(",")
    PLUGINS_SANDBOX_TIMEOUT = int(os.environ.get("PLUGINS_SANDBOX_TIMEOUT", 30))
    PLUGINS_MAX_MEMORY_MB = int(os.environ.get("PLUGINS_MAX_MEMORY_MB", 256))
    
    # Analysis Execution Configuration
    ANALYSIS_MAX_RUNTIME_SECONDS = int(os.environ.get("ANALYSIS_MAX_RUNTIME_SECONDS", 300))
    ANALYSIS_MAX_NODES = int(os.environ.get("ANALYSIS_MAX_NODES", 100))
    ANALYSIS_MAX_RECURSION_DEPTH = int(os.environ.get("ANALYSIS_MAX_RECURSION_DEPTH", 10))
    ANALYSIS_CACHE_TTL_SECONDS = int(os.environ.get("ANALYSIS_CACHE_TTL_SECONDS", 3600))
    ANALYSIS_REACTIVE_DEBOUNCE_MS = int(os.environ.get("ANALYSIS_REACTIVE_DEBOUNCE_MS", 1000))
    
    # Dashboard Canvas Configuration
    DASHBOARD_MAX_WIDGETS = int(os.environ.get("DASHBOARD_MAX_WIDGETS", 50))
    DASHBOARD_AUTO_REFRESH_ENABLED = os.environ.get("DASHBOARD_AUTO_REFRESH_ENABLED", "true").lower() == "true"
    DASHBOARD_DEFAULT_REFRESH_INTERVAL_SECONDS = int(os.environ.get("DASHBOARD_DEFAULT_REFRESH_INTERVAL_SECONDS", 300))
    DASHBOARD_MAX_CANVAS_WIDTH = int(os.environ.get("DASHBOARD_MAX_CANVAS_WIDTH", 3840))
    DASHBOARD_MAX_CANVAS_HEIGHT = int(os.environ.get("DASHBOARD_MAX_CANVAS_HEIGHT", 2160))
    
    # Form Versioning Configuration
    FORM_VERSIONING_ENABLED = os.environ.get("FORM_VERSIONING_ENABLED", "true").lower() == "true"
    FORM_MAX_BRANCHES = int(os.environ.get("FORM_MAX_BRANCHES", 20))
    FORM_MAX_COMMITS_PER_BRANCH = int(os.environ.get("FORM_MAX_COMMITS_PER_BRANCH", 1000))
    FORM_MERGE_CONFLICT_RESOLUTION_ENABLED = os.environ.get("FORM_MERGE_CONFLICT_RESOLUTION_ENABLED", "true").lower() == "true"
    FORM_OFFLINE_SYNC_ENABLED = os.environ.get("FORM_OFFLINE_SYNC_ENABLED", "true").lower() == "true"
    FORM_DRAFT_EXPIRY_HOURS = int(os.environ.get("FORM_DRAFT_EXPIRY_HOURS", 720))
    
    # ClamAV Integration
    CLAMAV_ENABLED = os.environ.get("CLAMAV_ENABLED", "true").lower() == "true"
    CLAMAV_HOST = os.environ.get("CLAMAV_HOST", "localhost")
    CLAMAV_PORT = int(os.environ.get("CLAMAV_PORT", 3310))
    CLAMAV_TIMEOUT_SECONDS = int(os.environ.get("CLAMAV_TIMEOUT_SECONDS", 30))
    CLAMAV_MAX_FILE_SIZE_MB = int(os.environ.get("CLAMAV_MAX_FILE_SIZE_MB", 100))
    
    # CORS Configuration
    CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "*").split(",")
    
    # Rate Limiting Configuration
    RATE_LIMIT_ENABLED = os.environ.get("RATE_LIMIT_ENABLED", "true").lower() == "true"
    RATE_LIMIT_DEFAULT = os.environ.get("RATE_LIMIT_DEFAULT", "60 per minute")
    RATE_LIMIT_AUTHENTICATED = os.environ.get("RATE_LIMIT_AUTHENTICATED", "60 per minute")
    RATE_LIMIT_UNAUTHENTICATED = os.environ.get("RATE_LIMIT_UNAUTHENTICATED", "20 per minute")
    RATE_LIMIT_API_KEY = os.environ.get("RATE_LIMIT_API_KEY", "1000 per hour")
    
    # Platform Configuration
    PLATFORM_VERSION = os.environ.get("PLATFORM_VERSION", "1.0.0")
    PLATFORM_NAME = os.environ.get("PLATFORM_NAME", "Form Builder Platform")
    MAINTENANCE_MODE = os.environ.get("MAINTENANCE_MODE", "false").lower() == "true"
    REGISTRATION_OPEN = os.environ.get("REGISTRATION_OPEN", "false").lower() == "true"
    
    # Security Configuration
    BCRYPT_ROUNDS = int(os.environ.get("BCRYPT_ROUNDS", 12))
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(seconds=int(os.environ.get("JWT_ACCESS_TOKEN_EXPIRES_SECONDS", 900)))
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(seconds=int(os.environ.get("JWT_REFRESH_TOKEN_EXPIRES_SECONDS", 2592000)))
    PASSWORD_MIN_LENGTH = int(os.environ.get("PASSWORD_MIN_LENGTH", 8))
    PASSWORD_MAX_AGE_DAYS = int(os.environ.get("PASSWORD_MAX_AGE_DAYS", 90))
    SESSION_TTL_SECONDS = int(os.environ.get("SESSION_TTL_SECONDS", 3600))
    
    # Monitoring and Logging
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
    LOG_FORMAT = os.environ.get("LOG_FORMAT", "json")
    SENTRY_DSN = os.environ.get("SENTRY_DSN")
    METRICS_ENABLED = os.environ.get("METRICS_ENABLED", "true").lower() == "true"
    HEALTH_CHECK_ENABLED = os.environ.get("HEALTH_CHECK_ENABLED", "true").lower() == "true"
    
    # Storage Configuration
    DEFAULT_STORAGE_QUOTA_BYTES = int(os.environ.get("DEFAULT_STORAGE_QUOTA_BYTES", 10737418240))  # 10GB
    STORAGE_WARNING_THRESHOLD = float(os.environ.get("STORAGE_WARNING_THRESHOLD", 0.8))
    STORAGE_CALCULATION_INTERVAL_HOURS = int(os.environ.get("STORAGE_CALCULATION_INTERVAL_HOURS", 24))
    FILE_CLEANUP_ENABLED = os.environ.get("FILE_CLEANUP_ENABLED", "true").lower() == "true"
    FILE_CLEANUP_RETENTION_DAYS = int(os.environ.get("FILE_CLEANUP_RETENTION_DAYS", 30))
    
    # Notification Configuration
    NOTIFICATION_MAX_RETRIES = int(os.environ.get("NOTIFICATION_MAX_RETRIES", 3))
    NOTIFICATION_RETRY_BACKOFF_SECONDS = list(map(int, os.environ.get("NOTIFICATION_RETRY_BACKOFF_SECONDS", "60,300,900").split(",")))
    WEBHOOK_MAX_RETRIES = int(os.environ.get("WEBHOOK_MAX_RETRIES", 3))
    WEBHOOK_TIMEOUT_SECONDS = int(os.environ.get("WEBHOOK_TIMEOUT_SECONDS", 30))
    WEBHOOK_RETRY_BACKOFF_SECONDS = list(map(int, os.environ.get("WEBHOOK_RETRY_BACKOFF_SECONDS", "60,300,900").split(",")))
    
    # Tus (Resumable Uploads) Configuration
    TUS_CHUNK_SIZE = int(os.environ.get("TUS_CHUNK_SIZE", 5242880))  # 5MB
    TUS_MAX_FILE_SIZE = int(os.environ.get("TUS_MAX_FILE_SIZE", 1073741824))  # 1GB
    TUS_UPLOAD_EXPIRY_HOURS = int(os.environ.get("TUS_UPLOAD_EXPIRY_HOURS", 24))
    
    # WebSocket Configuration (Flask-SocketIO)
    SOCKETIO_ASYNC_MODE = os.environ.get("SOCKETIO_ASYNC_MODE", "gevent")
    SOCKETIO_CORS_ALLOWED_ORIGINS = os.environ.get("SOCKETIO_CORS_ALLOWED_ORIGINS", "*")
    SOCKETIO_PING_TIMEOUT_SECONDS = int(os.environ.get("SOCKETIO_PING_TIMEOUT_SECONDS", 60))
    SOCKETIO_PING_INTERVAL_SECONDS = int(os.environ.get("SOCKETIO_PING_INTERVAL_SECONDS", 25))


class DevelopmentConfig(Config):
    DEBUG = True
    LOG_LEVEL = "DEBUG"
    RATE_LIMIT_ENABLED = False
    CLAMAV_ENABLED = False
    METRICS_ENABLED = False


class TestingConfig(Config):
    TESTING = True
    MONGO_URI = "mongomock://localhost"
    REDIS_URL = "redis://localhost:6379/0"
    SECRET_KEY = "test-secret"
    JWT_SECRET_KEY = "test-jwt-secret"
    CLAMAV_ENABLED = False
    RATE_LIMIT_ENABLED = False
    METRICS_ENABLED = False
    FILE_CLEANUP_ENABLED = False


class ProductionConfig(Config):
    DEBUG = False
    LOG_LEVEL = "INFO"
    # Production-specific overrides can be added here


config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig
}