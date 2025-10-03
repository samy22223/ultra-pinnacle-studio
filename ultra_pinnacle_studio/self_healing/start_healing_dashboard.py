#!/usr/bin/env python3
"""
Ultra Pinnacle Studio - Self-Healing Dashboard Launcher
Simple launcher script to start the self-healing dashboard server
"""

import os
import sys
import subprocess
from pathlib import Path

def main():
    """Start the self-healing dashboard server"""
    print("🔍 Ultra Pinnacle Studio - Self-Healing Dashboard")
    print("=" * 55)

    # Check if we're in the right directory
    healing_dir = Path(__file__).parent
    if not (healing_dir / "healing_api_server.py").exists():
        print("❌ Error: healing_api_server.py not found")
        print("Please run this script from the self_healing directory")
        sys.exit(1)

    # Change to self_healing directory
    os.chdir(healing_dir)

    print("🚀 Starting self-healing dashboard on http://localhost:8005")
    print("🔍 AI diagnostics and automated recovery protocols")
    print("🔗 Access from Auto-Install: http://localhost:8001")
    print("🏷️  Access from Domain Builder: http://localhost:8002")
    print("🌐 Access from Universal Hosting: http://localhost:8003")
    print("📦 Access from Auto-Updates: http://localhost:8004")
    print("⏹️  Press Ctrl+C to stop the server")
    print("=" * 55)

    try:
        # Start the self-healing dashboard server
        subprocess.run([
            sys.executable, "healing_api_server.py"
        ], cwd=healing_dir)

    except KeyboardInterrupt:
        print("\n🛑 Self-healing dashboard stopped by user")
    except Exception as e:
        print(f"❌ Error starting self-healing dashboard: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()