#!/usr/bin/env python3
"""
Basic import test to isolate the segmentation fault issue
"""
import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("Testing basic imports...")

try:
    print("1. Testing config import...")
    from api_gateway.config import config
    print("✅ Config imported successfully")
    print(f"   App name: {config.get('app.name')}")
    
    print("2. Testing logging config...")
    from api_gateway.logging_config import logger
    print("✅ Logging config imported successfully")
    
    print("3. Testing database...")
    from api_gateway.database import get_db, User
    print("✅ Database imported successfully")
    
    print("4. Testing auth...")
    from api_gateway.auth import get_password_hash, create_access_token
    print("✅ Auth imported successfully")
    
    print("5. Testing models (without problematic imports)...")
    # Let's test if we can import models module by patching the problematic imports
    import sys
    from unittest.mock import MagicMock
    
    # Mock the problematic modules before importing
    sys.modules['torch'] = MagicMock()
    sys.modules['diffusers'] = MagicMock()
    sys.modules['diffusers.utils'] = MagicMock()
    sys.modules['diffusers.utils.peft_utils'] = MagicMock()
    
    from api_gateway.models import ModelManager
    print("✅ Models imported successfully with mocked torch/diffusers")
    
    print("6. Testing workers...")
    from api_gateway.workers import WorkerManager
    print("✅ Workers imported successfully")
    
    print("7. Testing main app...")
    # We need to mock the models import in main.py as well
    from api_gateway import main
    print("✅ Main app imported successfully")
    
    print("\n🎉 ALL BASIC IMPORTS SUCCESSFUL!")
    print("The segmentation fault issue is related to torch/diffusers imports.")
    print("The system can work with mocked AI models for development.")
    
except Exception as e:
    print(f"❌ Import failed: {e}")
    import traceback
    traceback.print_exc()
