#!/usr/bin/env python3
"""
Ultra Pinnacle Studio - Updates Dashboard Launcher
Simple launcher script to start the updates dashboard server
"""

import os
import sys
import subprocess
from pathlib import Path

def main():
    """Start the updates dashboard server"""
    print("🔄 Ultra Pinnacle Studio - Auto-Upgrades & Updates Dashboard")
    print("=" * 65)

    # Check if we're in the right directory
    updates_dir = Path(__file__).parent
    if not (updates_dir / "updates_api_server.py").exists():
        print("❌ Error: updates_api_server.py not found")
        print("Please run this script from the auto_upgrader directory")
        sys.exit(1)

    # Change to auto_upgrader directory
    os.chdir(updates_dir)

    print("🚀 Starting updates dashboard on http://localhost:8004")
    print("📦 Manage automatic updates and rollback capabilities")
    print("🔗 Access from Auto-Install: http://localhost:8001")
    print("🏷️  Access from Domain Builder: http://localhost:8002")
    print("🌐 Access from Universal Hosting: http://localhost:8003")
    print("⏹️  Press Ctrl+C to stop the server")
    print("=" * 65)

    try:
        # Start the updates dashboard server
        subprocess.run([
            sys.executable, "updates_api_server.py"
        ], cwd=updates_dir)

    except KeyboardInterrupt:
        print("\n🛑 Updates dashboard stopped by user")
    except Exception as e:
        print(f"❌ Error starting updates dashboard: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()