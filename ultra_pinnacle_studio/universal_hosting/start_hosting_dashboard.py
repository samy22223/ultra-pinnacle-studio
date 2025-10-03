#!/usr/bin/env python3
"""
Ultra Pinnacle Studio - Universal Hosting Launcher
Simple launcher script to start the hosting dashboard server
"""

import os
import sys
import subprocess
from pathlib import Path

def main():
    """Start the universal hosting dashboard server"""
    print("🌐 Ultra Pinnacle Studio - Universal Hosting Dashboard")
    print("=" * 60)

    # Check if we're in the right directory
    hosting_dir = Path(__file__).parent
    if not (hosting_dir / "hosting_api_server.py").exists():
        print("❌ Error: hosting_api_server.py not found")
        print("Please run this script from the universal_hosting directory")
        sys.exit(1)

    # Change to universal_hosting directory
    os.chdir(hosting_dir)

    print("🚀 Starting universal hosting dashboard on http://localhost:8003")
    print("🌐 Manage cloud & local hybrid hosting with edge synchronization")
    print("🔗 Access from Auto-Install: http://localhost:8001")
    print("🏷️  Access from Domain Builder: http://localhost:8002")
    print("⏹️  Press Ctrl+C to stop the server")
    print("=" * 60)

    try:
        # Start the hosting dashboard server
        subprocess.run([
            sys.executable, "hosting_api_server.py"
        ], cwd=hosting_dir)

    except KeyboardInterrupt:
        print("\n🛑 Universal hosting dashboard stopped by user")
    except Exception as e:
        print(f"❌ Error starting hosting dashboard: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()