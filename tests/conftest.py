import pytest
import os
import tempfile
from app import storage

@pytest.fixture(autouse=True)
def setup_test_env_and_db(monkeypatch):
    # ✅ FORCE environment variable for pytest runtime
    monkeypatch.setenv("WEBHOOK_SECRET", "testsecret")

    # ---- DB setup ----
    test_db_dir = tempfile.mkdtemp()
    test_db_path = os.path.join(test_db_dir, "test.db")

    monkeypatch.setattr(storage, "DB_PATH", test_db_path)
    storage.init_db()

    yield

    # ---- Cleanup ----
    if os.path.exists(test_db_path):
        os.remove(test_db_path)
    if os.path.exists(test_db_dir):
        os.rmdir(test_db_dir)
