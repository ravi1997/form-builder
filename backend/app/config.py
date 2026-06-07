import os

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "default-secret-key-change-in-prod")
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "jwt-secret-key-change-in-prod")
    
    # MongoDB Config
    MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017/form_builder")
    
    # Redis Config
    REDIS_URI = os.environ.get("REDIS_URI", "redis://localhost:6379/0")
    
    # Elasticsearch Config
    ELASTICSEARCH_URI = os.environ.get("ELASTICSEARCH_URI", "http://localhost:9200")
    
    # Celery Config
    CELERY_BROKER_URL = REDIS_URI
    CELERY_RESULT_BACKEND = REDIS_URI

class DevelopmentConfig(Config):
    DEBUG = True

class TestingConfig(Config):
    TESTING = True
    MONGO_URI = "mongomock://localhost"
    REDIS_URI = "redis://localhost:6379/0"
    SECRET_KEY = "test-secret"
    JWT_SECRET_KEY = "test-jwt-secret"

class ProductionConfig(Config):
    DEBUG = False

config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig
}
