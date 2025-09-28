#!/usr/bin/env python3
"""
Server Startup Test Script for Ultra Pinnacle AI Studio
Tests that the FastAPI server can start up correctly and routes are registered
"""

import asyncio
import sys
import os

# Add parent directory to path to import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_server_startup():
    """Test server startup and route registration"""
    print("🚀 SERVER STARTUP TEST")
    print("=" * 50)

    try:
        from api_gateway.main import app
        print("✅ FastAPI app imported successfully")

        # Analyze routes
        routes = {}
        route_count = 0

        for route in app.routes:
            if hasattr(route, 'path'):
                methods = getattr(route, 'methods', ['GET'])
                routes[route.path] = methods
                route_count += 1

        print(f"✅ Found {route_count} registered routes")
        print()

        # Categorize routes
        auth_routes = []
        api_routes = []
        encyclopedia_routes = []
        other_routes = []

        for path, methods in routes.items():
            if '/auth/' in path:
                auth_routes.append((path, methods))
            elif any(endpoint in path for endpoint in ['/chat', '/enhance_prompt', '/code/', '/upload', '/tasks/']):
                api_routes.append((path, methods))
            elif '/encyclopedia/' in path:
                encyclopedia_routes.append((path, methods))
            else:
                other_routes.append((path, methods))

        # Display route summary
        print("Route Summary:")
        print(f"  System routes: {len(other_routes)}")
        print(f"  Auth routes: {len(auth_routes)}")
        print(f"  API routes: {len(api_routes)}")
        print(f"  Encyclopedia routes: {len(encyclopedia_routes)}")
        print()

        # Test specific important routes
        critical_routes = ['/', '/health', '/auth/login', '/encyclopedia/list']
        missing_routes = []

        for route in critical_routes:
            if route not in routes:
                missing_routes.append(route)

        if missing_routes:
            print("❌ Missing critical routes:")
            for route in missing_routes:
                print(f"   - {route}")
            return False
        else:
            print("✅ All critical routes present")

        # Test route methods
        expected_methods = {
            '/': ['GET'],
            '/health': ['GET'],
            '/models': ['GET'],
            '/workers': ['GET'],
            '/auth/login': ['POST'],
            '/chat': ['POST'],
            '/enhance_prompt': ['POST'],
            '/encyclopedia/list': ['GET'],
            '/encyclopedia/search': ['POST'],
        }

        method_issues = []
        for route, expected in expected_methods.items():
            if route in routes:
                actual = routes[route]
                if not set(expected).issubset(set(actual)):
                    method_issues.append(f"{route}: expected {expected}, got {actual}")

        if method_issues:
            print("❌ Route method issues:")
            for issue in method_issues:
                print(f"   - {issue}")
            return False
        else:
            print("✅ All route methods correctly configured")

        # Test app configuration
        if hasattr(app, 'title') and app.title:
            print(f"✅ App title: {app.title}")
        if hasattr(app, 'version') and app.version:
            print(f"✅ App version: {app.version}")

        print()
        print("🎉 Server startup test completed successfully!")
        return True

    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("   └─ Make sure you're running from the validation_scripts directory")
        return False
    except Exception as e:
        print(f"❌ Server startup test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_server_startup()
    exit(0 if success else 1)