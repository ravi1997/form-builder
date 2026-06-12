import pytest
import sys
import os
import shutil
from bson import ObjectId

# Ensure backend root is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app import create_app
from app.extensions import mongo
from app.services.auth_service import build_access_token

@pytest.fixture(scope="session")
def app():
    app = create_app("testing")
    yield app

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def db(app):
    # Clear database before each test
    with app.app_context():
        collections = mongo.db.list_collection_names()
        for col in collections:
            mongo.db[col].delete_many({})
        yield mongo.db
        # Cleanup uploads folder if created during test
        if os.path.exists("uploads"):
            try:
                shutil.rmtree("uploads")
            except OSError:
                pass

@pytest.fixture(autouse=True)
def patch_db_command(monkeypatch):
    # Mock database command "dbstats" for mongomock
    from app.extensions import mongo
    original_command = mongo.db.command
    def mock_command(cmd, *args, **kwargs):
        if cmd == "dbstats":
            return {"dataSize": 100, "ok": 1.0}
        return original_command(cmd, *args, **kwargs)
    monkeypatch.setattr(mongo.db, "command", mock_command)

@pytest.fixture
def get_auth_headers(app):
    def _get_headers(user_doc):
        with app.app_context():
            token = build_access_token(user_doc)
            return {"Authorization": f"Bearer {token}"}
    return _get_headers

@pytest.fixture
def mock_storage(app):
    class StorageMock:
        def __init__(self):
            self.uploads_dir = "uploads"

        def write_file(self, org_id, filename, size_bytes):
            org_dir = os.path.join(self.uploads_dir, str(org_id))
            os.makedirs(org_dir, exist_ok=True)
            filepath = os.path.join(org_dir, filename)
            with open(filepath, "wb") as f:
                f.write(b"\0" * size_bytes)
            return filepath

        def cleanup(self):
            if os.path.exists(self.uploads_dir):
                shutil.rmtree(self.uploads_dir)

    mock = StorageMock()
    yield mock
    mock.cleanup()
