#!/usr/bin/env python3
"""
Server startup script that handles import issues gracefully
"""
import os
import sys
import subprocess
from pathlib import Path

# Set environment variables
os.environ['JWT_SECRET'] = os.environ.get('JWT_SECRET', 'ultra-pinnacle-dev-secret-key-change-in-production')
os.environ['LOG_LEVEL'] = os.environ.get('LOG_LEVEL', 'INFO')
os.environ['ENVIRONMENT'] = os.environ.get('ENVIRONMENT', 'development')

def main():
    """Start the Ultra Pinnacle AI Studio server"""
    print("🚀 Starting Ultra Pinnacle AI Studio...")
    
    # Check if we're in the right directory
    if not Path('api_gateway').exists():
        print("❌ Error: api_gateway directory not found")
        print("Please run this script from the ultra_pinnacle_studio directory")
        sys.exit(1)
    
    # Check if models directory exists
    models_dir = Path('models')
    if not models_dir.exists():
        print("📁 Creating models directory...")
        models_dir.mkdir()
    
    # Check if logs directory exists
    logs_dir = Path('logs')
    if not logs_dir.exists():
        print("📁 Creating logs directory...")
        logs_dir.mkdir()
    
    # Check if uploads directory exists
    uploads_dir = Path('uploads')
    if not uploads_dir.exists():
        print("📁 Creating uploads directory...")
        uploads_dir.mkdir()
    
    # Try to start the server
    try:
        print("🔧 Starting server with mocked AI models (development mode)...")
        print("📡 Server will be available at: http://localhost:8000")
        print("📖 API documentation at: http://localhost:8000/docs")
        print("📊 Dashboard at: http://localhost:8000/dashboard")
        print("⏹️  Press Ctrl+C to stop the server")
        print("=" * 60)
        
        # Start uvicorn with the app
        cmd = [
            sys.executable, '-m', 'uvicorn',
            'api_gateway.main:app',
            '--host', '0.0.0.0',
            '--port', '8000',
            '--reload',
            '--log-level', 'info'
        ]
        
        # Run the server
        subprocess.run(cmd, cwd='.')
        
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
