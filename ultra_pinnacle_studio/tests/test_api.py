import pytest
from fastapi.testclient import TestClient
from api_gateway.main import app
import json

client = TestClient(app)

# Test data
VALID_USER = {"username": "demo", "password": "demo123"}
INVALID_USER = {"username": "invalid", "password": "invalid"}

def get_auth_token():
    """Helper function to get authentication token"""
    response = client.post("/auth/login", json=VALID_USER)
    return response.json()["access_token"]

def get_auth_headers():
    """Helper function to get authentication headers"""
    token = get_auth_token()
    return {"Authorization": f"Bearer {token}"}

# Basic endpoints
def test_root():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "Ultra Pinnacle AI Studio" in data["message"]
    assert "status" in data
    assert "features" in data

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data
    assert "models_loaded" in data
    assert "active_tasks" in data

def test_models_list():
    response = client.get("/models")
    assert response.status_code == 200
    data = response.json()
    assert "models" in data
    assert isinstance(data["models"], dict)

def test_workers_list():
    response = client.get("/workers")
    assert response.status_code == 200
    data = response.json()
    assert "workers" in data
    assert isinstance(data["workers"], list)

# Authentication tests
def test_login_success():
    response = client.post("/auth/login", json=VALID_USER)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

def test_login_invalid_credentials():
    response = client.post("/auth/login", json=INVALID_USER)
    assert response.status_code == 401

def test_login_missing_fields():
    response = client.post("/auth/login", json={"username": "demo"})
    assert response.status_code == 422  # Validation error

# Encyclopedia tests
def test_list_encyclopedia():
    response = client.get("/encyclopedia/list")
    assert response.status_code == 200
    data = response.json()
    assert "topics" in data
    assert isinstance(data["topics"], list)
    assert len(data["topics"]) >= 5  # Should have at least 5 topics

def test_get_topic():
    response = client.get("/encyclopedia/math_sequences")
    assert response.status_code == 200
    data = response.json()
    assert "topic" in data
    assert "content" in data
    assert data["topic"] == "math_sequences"

def test_get_nonexistent_topic():
    response = client.get("/encyclopedia/nonexistent_topic")
    assert response.status_code == 404
    data = response.json()
    assert "detail" in data

def test_search_encyclopedia():
    response = client.post("/encyclopedia/search", json={"query": "algorithm"})
    assert response.status_code == 200
    data = response.json()
    assert "query" in data
    assert "results" in data
    assert isinstance(data["results"], list)

def test_search_encyclopedia_empty_query():
    response = client.post("/encyclopedia/search", json={"query": ""})
    assert response.status_code == 200
    # Should return empty results or handle gracefully

# Protected endpoints requiring authentication
def test_enhance_prompt_unauthorized():
    response = client.post("/enhance_prompt", json={"prompt": "test prompt"})
    assert response.status_code == 403  # FastAPI returns 403 for missing auth

def test_enhance_prompt_authorized():
    headers = get_auth_headers()
    response = client.post("/enhance_prompt",
                          json={"prompt": "test prompt", "model": "llama-2-7b-chat"},
                          headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "enhanced_prompt" in data
    assert "Mock response" in data["enhanced_prompt"]  # Should get mock response

def test_chat_unauthorized():
    response = client.post("/chat", json={"message": "Hello"})
    assert response.status_code == 403  # FastAPI returns 403 for missing auth

def test_chat_authorized():
    headers = get_auth_headers()
    response = client.post("/chat",
                          json={"message": "Hello", "model": "llama-2-7b-chat"},
                          headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    assert "conversation_id" in data
    assert "Mock response" in data["response"]  # Should get mock response

def test_code_task_unauthorized():
    response = client.post("/code/analyze", json={"code": "print('hello')", "language": "python"})
    assert response.status_code == 403  # FastAPI returns 403 for missing auth

def test_code_task_authorized():
    headers = get_auth_headers()
    response = client.post("/code/analyze",
                          json={"code": "print('hello')", "language": "python", "task": "analyze"},
                          headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "task_id" in data
    assert "status" in data

def test_file_upload_unauthorized():
    # Create a simple test file
    import io
    file_content = b"test file content"
    files = {"file": ("test.txt", io.BytesIO(file_content), "text/plain")}
    response = client.post("/upload", files=files)
    assert response.status_code == 403  # FastAPI returns 403 for missing auth

def test_task_status_unauthorized():
    response = client.get("/tasks/test-task-id")
    assert response.status_code == 403  # FastAPI returns 403 for missing auth

# Test invalid requests
def test_enhance_prompt_invalid_model():
    headers = get_auth_headers()
    response = client.post("/enhance_prompt",
                          json={"prompt": "test", "model": "invalid-model"},
                          headers=headers)
    # Should handle gracefully - either accept or return error
    assert response.status_code in [200, 400, 500]

def test_chat_empty_message():
    headers = get_auth_headers()
    response = client.post("/chat", json={"message": ""}, headers=headers)
    assert response.status_code == 200  # Should handle empty messages
    data = response.json()
    assert "response" in data
    assert "conversation_id" in data

def test_code_task_invalid_type():
    headers = get_auth_headers()
    response = client.post("/code/invalid_task",
                          json={"code": "test", "language": "python"},
                          headers=headers)
    assert response.status_code == 422  # Pydantic validation error for invalid task

# Test configuration and setup
def test_config_loading():
    """Test that configuration is loaded properly"""
    from api_gateway.main import config
    assert "app" in config
    assert "models" in config
    assert "security" in config
    assert "paths" in config

def test_model_manager_initialization():
    """Test that model manager initializes correctly"""
    from api_gateway.main import model_manager
    assert model_manager is not None
    models = model_manager.list_models()
    assert isinstance(models, dict)

def test_worker_manager_initialization():
    """Test that worker manager initializes correctly"""
    from api_gateway.main import worker_manager
    assert worker_manager is not None
    workers = worker_manager.list_workers()
    assert isinstance(workers, list)