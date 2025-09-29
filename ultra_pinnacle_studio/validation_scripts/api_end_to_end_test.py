#!/usr/bin/env python3
"""
API End-to-End Test Script for Ultra Pinnacle AI Studio
Tests complete API functionality from authentication to protected endpoints
"""

import sys
import os

# Add parent directory to path to import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_api_end_to_end():
    """Test complete API functionality end-to-end"""
    print("🔗 API END-TO-END TEST")
    print("=" * 50)

    try:
        from fastapi.testclient import TestClient
        from api_gateway.main import app

        client = TestClient(app)
        print("✅ Test client initialized")

        # Test 1: Root endpoint
        print("\n1. Testing root endpoint...")
        response = client.get('/')
        assert response.status_code == 200
        data = response.json()
        assert 'message' in data
        assert 'Ultra Pinnacle AI Studio' in data['message']
        print("✅ Root endpoint accessible")

        # Test 2: Health endpoint
        print("\n2. Testing health endpoint...")
        response = client.get('/health')
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'healthy'
        assert 'timestamp' in data
        assert 'models_loaded' in data
        assert 'active_tasks' in data
        print("✅ Health endpoint working")

        # Test 3: Models endpoint
        print("\n3. Testing models endpoint...")
        response = client.get('/models')
        assert response.status_code == 200
        data = response.json()
        assert 'models' in data
        print(f"✅ Models endpoint working ({len(data['models'])} models available)")

        # Test 4: Workers endpoint
        print("\n4. Testing workers endpoint...")
        response = client.get('/workers')
        assert response.status_code == 200
        data = response.json()
        assert 'workers' in data
        print(f"✅ Workers endpoint working ({len(data['workers'])} workers available)")

        # Test 5: Authentication
        print("\n5. Testing authentication...")
        response = client.post('/auth/login', json={
            'username': 'demo',
            'password': 'demo123'
        })
        assert response.status_code == 200
        data = response.json()
        assert 'access_token' in data
        assert data['token_type'] == 'bearer'
        token = data['access_token']
        print("✅ Authentication successful")

        # Test 6: Protected endpoints (should fail without token)
        print("\n6. Testing protected endpoints (unauthorized)...")
        response = client.post('/chat', json={'message': 'Hello'})
        assert response.status_code == 403  # Forbidden (FastAPI returns 403 for missing auth)
        print("✅ Protected endpoints correctly secured")

        # Test 7: Protected endpoints (with token)
        print("\n7. Testing protected endpoints (authorized)...")
        headers = {'Authorization': f'Bearer {token}'}

        # Chat endpoint
        response = client.post('/chat', json={'message': 'Hello'}, headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert 'response' in data
        assert 'conversation_id' in data
        print("✅ Chat endpoint working")

        # Enhance prompt endpoint
        response = client.post('/enhance_prompt', json={'prompt': 'Test prompt'}, headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert 'enhanced_prompt' in data
        print("✅ Enhance prompt endpoint working")

        # Test 8: Encyclopedia endpoints
        print("\n8. Testing encyclopedia endpoints...")

        # List topics
        response = client.get('/encyclopedia/list')
        assert response.status_code == 200
        data = response.json()
        assert 'topics' in data
        assert len(data['topics']) >= 5
        topics = data['topics']
        print(f"✅ Encyclopedia list working ({len(topics)} topics)")

        # Get specific topic
        if topics:
            first_topic = topics[0]
            response = client.get(f'/encyclopedia/{first_topic}')
            assert response.status_code == 200
            data = response.json()
            assert 'content' in data
            assert data['topic'] == first_topic
            print(f"✅ Encyclopedia topic retrieval working ({first_topic})")

        # Search encyclopedia
        response = client.post('/encyclopedia/search', json={'query': 'algorithm'})
        assert response.status_code == 200
        data = response.json()
        assert 'results' in data
        print("✅ Encyclopedia search working")

        # Test 9: Code analysis endpoint
        print("\n9. Testing code analysis endpoint...")
        response = client.post('/code/analyze', json={
            'code': 'def hello():\n    print("Hello World")',
            'language': 'python',
            'task': 'analyze'
        }, headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert 'task_id' in data
        task_id = data['task_id']
        print(f"✅ Code analysis task submitted (ID: {task_id})")

        # Test 10: Task status endpoint
        print("\n10. Testing task status endpoint...")
        response = client.get(f'/tasks/{task_id}', headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert 'status' in data
        print(f"✅ Task status endpoint working (status: {data['status']})")

        print("\n🎉 All API end-to-end tests passed!")
        print("✅ Ultra Pinnacle AI Studio API is fully functional")
        return True

    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("   └─ Make sure you're running from the validation_scripts directory")
        return False
    except AssertionError as e:
        print(f"❌ Test assertion failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    except Exception as e:
        print(f"❌ API test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_api_end_to_end()
    exit(0 if success else 1)