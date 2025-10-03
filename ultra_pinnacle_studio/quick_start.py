#!/usr/bin/env python3
"""
Ultra Pinnacle Studio - Quick Start
Get your platform running in under 5 minutes!
"""

import os
import sys
import json
import time
import asyncio
import subprocess
from pathlib import Path
from datetime import datetime

def print_header():
    """Print startup header"""
    print("🚀 Ultra Pinnacle Studio - Quick Start")
    print("=" * 50)
    print("🎉 Welcome to the most comprehensive autonomous platform!")
    print("📋 This will get you up and running in minutes!")
    print("=" * 50)

def check_requirements():
    """Check system requirements"""
    print("\n🔍 Checking system requirements...")

    # Check Python version
    python_version = f"{sys.version_info.major}.{sys.version_info.minor}"
    print(f"   ✅ Python {python_version} detected")

    # Check available memory
    import psutil
    memory_gb = psutil.virtual_memory().total / (1024**3)
    if memory_gb >= 4:
        print(f"   ✅ Memory: {memory_gb:.1f}GB (sufficient)")
    else:
        print(f"   ⚠️ Memory: {memory_gb:.1f}GB (minimum 4GB recommended)")

    # Check disk space
    disk_gb = psutil.disk_usage('.').free / (1024**3)
    if disk_gb >= 10:
        print(f"   ✅ Disk space: {disk_gb:.1f}GB (sufficient)")
    else:
        print(f"   ⚠️ Disk space: {disk_gb:.1f}GB (minimum 10GB recommended)")

def setup_configuration():
    """Set up basic configuration"""
    print("\n⚙️ Setting up configuration...")

    # Copy template config if config.json doesn't exist
    config_template = Path("config.template.json")
    config_file = Path("config.json")

    if not config_file.exists() and config_template.exists():
        import shutil
        shutil.copy(config_template, config_file)
        print("   ✅ Configuration file created from template")
        print("   📝 Please edit config.json to add your API keys")
    elif config_file.exists():
        print("   ✅ Configuration file already exists")
    else:
        print("   ⚠️ Configuration template not found")

def install_dependencies():
    """Install Python dependencies"""
    print("\n📦 Installing Python dependencies...")

    try:
        # Try to install requirements
        result = subprocess.run([
            sys.executable, "-m", "pip", "install", "-r", "requirements.txt"
        ], capture_output=True, text=True, timeout=300)

        if result.returncode == 0:
            print("   ✅ Dependencies installed successfully")
        else:
            print("   ⚠️ Some dependencies failed to install")
            print(f"   Error: {result.stderr}")

    except subprocess.TimeoutExpired:
        print("   ⚠️ Installation timed out - some packages may not be installed")
    except Exception as e:
        print(f"   ⚠️ Installation failed: {e}")

def run_basic_tests():
    """Run basic functionality tests"""
    print("\n🧪 Running basic tests...")

    try:
        # Test basic imports
        test_modules = [
            "api_gateway.main",
            "auto_install.deployment_engine",
            "security_privacy.zero_trust_ai"
        ]

        success_count = 0
        for module in test_modules:
            try:
                __import__(module)
                print(f"   ✅ {module} imported successfully")
                success_count += 1
            except Exception as e:
                print(f"   ❌ {module} failed: {e}")

        print(f"   📊 Test results: {success_count}/{len(test_modules)} modules working")

    except Exception as e:
        print(f"   ❌ Test execution failed: {e}")

def start_platform():
    """Start the platform"""
    print("\n🚀 Starting Ultra Pinnacle Studio...")

    try:
        # Start the server
        print("   Starting API Gateway...")
        server_process = subprocess.Popen([
            sys.executable, "start_server.py"
        ])

        print("   ✅ Server started!")
        print("   🌐 Platform URL: http://localhost:8000")
        print("   📚 API Documentation: http://localhost:8000/docs")
        print("   👤 Admin Dashboard: http://localhost:8000/admin")

        # Save process ID for later management
        with open("server_pid.txt", "w") as f:
            f.write(str(server_process.pid))

        return server_process

    except Exception as e:
        print(f"   ❌ Failed to start platform: {e}")
        return None

def print_success_message():
    """Print success message and next steps"""
    print("\n" + "=" * 50)
    print("🎉 SUCCESS! Ultra Pinnacle Studio is running!")
    print("=" * 50)
    print("🌐 Access your platform at: http://localhost:8000")
    print("📚 API documentation: http://localhost:8000/docs")
    print("👤 Admin dashboard: http://localhost:8000/admin")
    print()
    print("📋 What you can do now:")
    print("   🎬 Generate AI videos from text")
    print("   🎨 Create designs and prototypes")
    print("   🛒 Set up e-commerce stores")
    print("   🤖 Use AI assistants and automation")
    print("   👥 Collaborate with your team")
    print("   🔒 Manage security and privacy")
    print()
    print("📖 Next steps:")
    print("   1. Edit config.json with your API keys")
    print("   2. Explore the web interface")
    print("   3. Try the AI features")
    print("   4. Set up your custom domain")
    print("   5. Configure external integrations")
    print()
    print("🚀 You're all set! Enjoy your autonomous platform!")
    print("=" * 50)

def main():
    """Main quick start execution"""
    print_header()

    # Step 1: Check requirements
    check_requirements()

    # Step 2: Setup configuration
    setup_configuration()

    # Step 3: Install dependencies
    install_dependencies()

    # Step 4: Run basic tests
    run_basic_tests()

    # Step 5: Start platform
    server_process = start_platform()

    if server_process:
        print_success_message()
        return 0
    else:
        print("\n❌ Platform startup failed")
        print("Please check the error messages above and try again")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)