#!/usr/bin/env python3
"""
Ultra Pinnacle Studio - Cross-Device Sync Launcher
Simple launcher script to start the sync dashboard server
"""

import os
import sys
import subprocess
from pathlib import Path

def main():
    """Start the cross-device sync dashboard server"""
    print("🔄 Ultra Pinnacle Studio - Cross-Device Sync Dashboard")
    print("=" * 60)

    # Check if we're in the right directory
    sync_dir = Path(__file__).parent
    if not (sync_dir / "sync_api_server.py").exists():
        print("❌ Error: sync_api_server.py not found")
        print("Please run this script from the cross_device_sync directory")
        sys.exit(1)

    # Change to cross_device_sync directory
    os.chdir(sync_dir)

    print("🚀 Starting cross-device sync dashboard on http://localhost:8006")
    print("📱 Real-time synchronization across all your devices")
    print("🔗 Access from Auto-Install: http://localhost:8001")
    print("🏷️  Access from Domain Builder: http://localhost:8002")
    print("🌐 Access from Universal Hosting: http://localhost:8003")
    print("📦 Access from Auto-Updates: http://localhost:8004")
    print("🔍 Access from Self-Healing: http://localhost:8005")
    print("⏹️  Press Ctrl+C to stop the server")
    print("=" * 60)

    try:
        # Start the cross-device sync dashboard server
        subprocess.run([
            sys.executable, "sync_api_server.py"
        ], cwd=sync_dir)

    except KeyboardInterrupt:
        print("\n🛑 Cross-device sync dashboard stopped by user")
    except Exception as e:
        print(f"❌ Error starting sync dashboard: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()