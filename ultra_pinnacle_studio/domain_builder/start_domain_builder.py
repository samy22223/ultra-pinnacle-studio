#!/usr/bin/env python3
"""
Ultra Pinnacle Studio - Domain Builder Launcher
Simple launcher script to start the domain builder server
"""

import os
import sys
import subprocess
from pathlib import Path

def main():
    """Start the domain builder server"""
    print("🌐 Ultra Pinnacle Studio - Free Domain Auto-Builder")
    print("=" * 55)

    # Check if we're in the right directory
    domain_dir = Path(__file__).parent
    if not (domain_dir / "domain_api_server.py").exists():
        print("❌ Error: domain_api_server.py not found")
        print("Please run this script from the domain_builder directory")
        sys.exit(1)

    # Change to domain_builder directory
    os.chdir(domain_dir)

    print("🚀 Starting domain builder server on http://localhost:8002")
    print("🎯 Open your browser and navigate to the URL above")
    print("🌐 Generate free custom domains, subdomains, and international TLDs")
    print("⏹️  Press Ctrl+C to stop the server")
    print("=" * 55)

    try:
        # Start the domain builder server
        subprocess.run([
            sys.executable, "domain_api_server.py"
        ], cwd=domain_dir)

    except KeyboardInterrupt:
        print("\n🛑 Domain builder server stopped by user")
    except Exception as e:
        print(f"❌ Error starting domain builder server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()