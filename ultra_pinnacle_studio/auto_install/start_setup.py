#!/usr/bin/env python3
"""
Ultra Pinnacle Studio - Auto-Install Launcher
Simple launcher script to start the setup server
"""

import os
import sys
import subprocess
from pathlib import Path

def main():
    """Start the auto-install setup server"""
    print("🚀 Ultra Pinnacle Studio - Auto-Install System")
    print("=" * 50)

    # Check if we're in the right directory
    auto_install_dir = Path(__file__).parent
    if not (auto_install_dir / "setup_server.py").exists():
        print("❌ Error: setup_server.py not found")
        print("Please run this script from the auto_install directory")
        sys.exit(1)

    # Change to auto_install directory
    os.chdir(auto_install_dir)

    print("📡 Starting setup server on http://localhost:8001")
    print("🌐 Open your browser and navigate to the URL above")
    print("⏹️  Press Ctrl+C to stop the server")
    print("=" * 50)

    try:
        # Start the setup server
        subprocess.run([
            sys.executable, "setup_server.py"
        ], cwd=auto_install_dir)

    except KeyboardInterrupt:
        print("\n🛑 Setup server stopped by user")
    except Exception as e:
        print(f"❌ Error starting setup server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()