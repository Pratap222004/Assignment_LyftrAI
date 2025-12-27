import pytest
import os
import tempfile
from app import storage

# Override database path for tests
@pytest.fixture(autouse=True)
def setup_test_db(monkeypatch):
    """Setup test database in temporary directory"""
    # Create a temporary directory for test database
    test_db_dir = tempfile.mkdtemp()
    test_db_path = os.path.join(test_db_dir, "test.db")
    
    # Override the DB_PATH
    monkeypatch.setattr(storage, "DB_PATH", test_db_path)
    
    # Initialize database
    storage.init_db()
    
    yield
    
    # Cleanup
    if os.path.exists(test_db_path):
        os.remove(test_db_path)
    if os.path.exists(test_db_dir):
        os.rmdir(test_db_dir)

