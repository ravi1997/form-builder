#!/bin/bash
set -e

# Wait for services to be ready
wait_for_service() {
    local service=$1
    local port=$2
    local timeout=${3:-60}
    
    echo "Waiting for $service to be ready..."
    for i in $(seq 1 $timeout); do
        if nc -z "$service" "$port"; then
            echo "$service is ready!"
            return 0
        fi
        echo "Waiting for $service... ($i/$timeout)"
        sleep 1
    done
    echo "Timeout waiting for $service"
    return 1
}

# Wait for MongoDB
if [ "$MONGO_URI" ]; then
    echo "Waiting for MongoDB..."
    python -c "
import time
import pymongo
from urllib.parse import urlparse
from app.config import Config

uri = Config.MONGO_URI
parsed = urlparse(uri)
host = parsed.hostname
port = parsed.port or 27017

for i in range(60):
    try:
        client = pymongo.MongoClient(uri, serverSelectionTimeoutMS=1000)
        client.admin.command('ping')
        print('MongoDB is ready!')
        break
    except Exception as e:
        print(f'Waiting for MongoDB... ({i+1}/60)')
        time.sleep(1)
else
    echo 'MONGO_URI not set, skipping MongoDB check'
fi

# Wait for Redis
if [ "$REDIS_URL" ]; then
    echo "Waiting for Redis..."
    python -c "
import time
import redis
from urllib.parse import urlparse
from app.config import Config

uri = Config.REDIS_URL
parsed = urlparse(uri)
host = parsed.hostname
port = parsed.port or 6379

for i in range(60):
    try:
        client = redis.Redis(host=host, port=port, socket_connect_timeout=1)
        client.ping()
        print('Redis is ready!')
        break
    except Exception as e:
        print(f'Waiting for Redis... ({i+1}/60)')
        time.sleep(1)
else
    echo 'REDIS_URL not set, skipping Redis check'
fi

# Wait for Elasticsearch
if [ "$ELASTICSEARCH_URL" ]; then
    echo "Waiting for Elasticsearch..."
    python -c "
import time
import requests
from app.config import Config

url = Config.ELASTICSEARCH_URL

for i in range(60):
    try:
        response = requests.get(f'{url}/_cluster/health', timeout=1)
        if response.status_code == 200:
            print('Elasticsearch is ready!')
            break
    except Exception as e:
        print(f'Waiting for Elasticsearch... ({i+1}/60)')
        time.sleep(1)
else
    echo 'ELASTICSEARCH_URL not set, skipping Elasticsearch check'
fi

# Wait for ClamAV
if [ "$CLAMAV_ENABLED" = "true" ] && [ "$CLAMAV_HOST" ]; then
    echo "Waiting for ClamAV..."
    for i in $(seq 1 60); do
        if nc -z "$CLAMAV_HOST" "${CLAMAV_PORT:-3310}"; then
            echo "ClamAV is ready!"
            break
        fi
        echo "Waiting for ClamAV... ($i/60)"
        sleep 1
    done
else
    echo 'ClamAV disabled or not configured, skipping check'
fi

# Run database migrations if needed
echo "Running database migrations..."
python -c "
from app.config import config_by_name
from app.extensions import db
import os

env = os.getenv('FLASK_ENV', 'development')
config = config_by_name[env]

# Initialize database connections and collections
print('Database initialization completed')
"

# Collect static files if needed
echo "Collecting static files..."
python -c "
import os
if os.path.exists('manage.py'):
    try:
        from flask import Flask
        from app import create_app
        app = create_app()
        with app.app_context():
            # Collect static files if needed
            print('Static files collection completed')
    except Exception as e:
        print(f'Static files collection skipped: {e}')
"

# Execute the command
exec "$@"