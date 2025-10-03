#!/usr/bin/env python3
"""
Ultra Pinnacle Studio - Autonomous Deployment Engine
Handles one-click setup across multiple platforms and ecosystems
"""

import os
import sys
import json
import time
import shutil
import subprocess
import platform
import hashlib
import secrets
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

class DeploymentMode(Enum):
    QUICK = "quick"
    CUSTOM = "custom"
    ENTERPRISE = "enterprise"

class PlatformType(Enum):
    WINDOWS = "windows"
    MACOS = "macos"
    LINUX = "linux"
    MOBILE = "mobile"
    DOCKER = "docker"

@dataclass
class DeploymentConfig:
    """Configuration for deployment process"""
    mode: DeploymentMode
    platform: PlatformType
    domain_name: str = ""
    admin_email: str = ""
    enable_ssl: bool = True
    enable_monitoring: bool = True
    enable_backups: bool = True
    custom_ports: Dict[str, int] = None

    def __post_init__(self):
        if self.custom_ports is None:
            self.custom_ports = {
                "api": 8000,
                "web_ui": 3000,
                "monitoring": 9090
            }

class DeploymentEngine:
    """Main deployment engine for Ultra Pinnacle Studio"""

    def __init__(self, config: DeploymentConfig):
        self.config = config
        self.project_root = Path(__file__).parent.parent
        self.deployment_log = []
        self.start_time = datetime.now()

    async def deploy(self) -> bool:
        """Execute the complete deployment process"""
        try:
            self.log("🚀 Starting Ultra Pinnacle Studio deployment...")
            self.log(f"Mode: {self.config.mode.value}")
            self.log(f"Platform: {self.config.platform.value}")

            # Phase 1: Pre-deployment checks
            await self.pre_deployment_checks()

            # Phase 2: Directory structure setup
            await self.setup_directories()

            # Phase 3: Dependencies installation
            await self.install_dependencies()

            # Phase 4: Configuration generation
            await self.generate_configuration()

            # Phase 5: Database setup
            await self.setup_database()

            # Phase 6: Services configuration
            await self.configure_services()

            # Phase 7: Security setup
            await self.setup_security()

            # Phase 8: Domain and networking
            await self.setup_domain_networking()

            # Phase 9: Final setup and startup
            await self.final_setup()

            self.log("✅ Deployment completed successfully!")
            return True

        except Exception as e:
            self.log(f"❌ Deployment failed: {str(e)}", "error")
            return False

    async def pre_deployment_checks(self):
        """Perform pre-deployment system checks"""
        self.log("🔍 Running pre-deployment checks...")

        # Check Python version
        python_version = sys.version_info
        if python_version < (3, 12):
            raise Exception(f"Python 3.12+ required, found {python_version.major}.{python_version.minor}")

        # Check available disk space (need at least 5GB)
        disk_usage = shutil.disk_usage(self.project_root)
        free_gb = disk_usage.free / (1024**3)
        if free_gb < 5:
            raise Exception(f"Insufficient disk space. Need at least 5GB, have {free_gb:.1f}GB")

        # Check platform compatibility
        current_platform = self.detect_platform()
        if current_platform != self.config.platform:
            self.log(f"⚠️  Platform mismatch: detected {current_platform.value}, configured {self.config.platform.value}")

        # Check network connectivity
        try:
            import urllib.request
            urllib.request.urlopen('https://google.com', timeout=5)
            self.log("✅ Network connectivity verified")
        except:
            self.log("⚠️  No internet connection - some features may be limited")

        self.log("✅ Pre-deployment checks completed")

    async def setup_directories(self):
        """Create necessary directory structure"""
        self.log("📁 Setting up directory structure...")

        directories = [
            'models', 'logs', 'uploads', 'backups', 'temp',
            'ssl/certs', 'ssl/private', 'config/custom',
            'data/encyclopedias', 'data/embeddings'
        ]

        for dir_name in directories:
            dir_path = self.project_root / dir_name
            dir_path.mkdir(parents=True, exist_ok=True)

            # Set appropriate permissions
            if platform.system() != 'Windows':
                os.chmod(dir_path, 0o755)

        self.log("✅ Directory structure created")

    async def install_dependencies(self):
        """Install Python and system dependencies"""
        self.log("📦 Installing dependencies...")

        # Create virtual environment if it doesn't exist
        venv_path = self.project_root / 'venv'
        if not venv_path.exists():
            self.log("Creating Python virtual environment...")
            subprocess.run([sys.executable, '-m', 'venv', 'venv'], check=True)

        # Activate virtual environment and install dependencies
        python_executable = venv_path / ('Scripts/python.exe' if platform.system() == 'Windows' else 'bin/python')

        self.log("Installing Python dependencies...")
        requirements_path = self.project_root / 'requirements.txt'
        if requirements_path.exists():
            pip_cmd = [str(python_executable), '-m', 'pip', 'install', '-r', str(requirements_path)]
            subprocess.run(pip_cmd, check=True)

        # Install Node.js dependencies if package.json exists
        package_json = self.project_root / 'web_ui' / 'package.json'
        if package_json.exists():
            self.log("Installing Node.js dependencies...")
            subprocess.run(['npm', 'install'], cwd=self.project_root / 'web_ui', check=True)

        self.log("✅ Dependencies installed")

    async def generate_configuration(self):
        """Generate configuration files based on deployment mode"""
        self.log("⚙️  Generating configuration files...")

        # Generate JWT secret
        jwt_secret = secrets.token_urlsafe(32)

        # Base configuration
        config = {
            "deployment": {
                "mode": self.config.mode.value,
                "platform": self.config.platform.value,
                "deployed_at": self.start_time.isoformat(),
                "version": "1.0.0"
            },
            "security": {
                "jwt_secret": jwt_secret,
                "algorithm": "HS256",
                "access_token_expire_minutes": 30,
                "ssl_enabled": self.config.enable_ssl
            },
            "services": {
                "api_port": self.config.custom_ports["api"],
                "web_ui_port": self.config.custom_ports["web_ui"],
                "monitoring_port": self.config.custom_ports["monitoring"]
            },
            "features": {
                "auto_healing": True,
                "auto_updates": True,
                "cross_device_sync": True,
                "domain_builder": True,
                "universal_hosting": True
            }
        }

        # Mode-specific configuration
        if self.config.mode == DeploymentMode.CUSTOM:
            config["domain"] = {
                "name": self.config.domain_name,
                "auto_ssl": True,
                "international_tlds": True
            }
            config["monitoring"] = {
                "enabled": True,
                "retention_days": 30
            }

        elif self.config.mode == DeploymentMode.ENTERPRISE:
            config["enterprise"] = {
                "high_availability": True,
                "load_balancing": True,
                "backup_redundancy": True,
                "compliance_mode": True
            }
            config["monitoring"] = {
                "enabled": True,
                "advanced_metrics": True,
                "alerting": True,
                "retention_days": 90
            }

        # Write configuration files
        config_path = self.project_root / 'config' / 'auto_generated.json'
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)

        # Update main config.json with generated values
        main_config_path = self.project_root / 'config.json'
        if main_config_path.exists():
            with open(main_config_path, 'r') as f:
                main_config = json.load(f)

            main_config['security']['secret_key'] = f'${{JWT_SECRET:-{jwt_secret}}}'
            main_config['deployment'] = config['deployment']

            with open(main_config_path, 'w') as f:
                json.dump(main_config, f, indent=2)

        self.log("✅ Configuration files generated")

    async def setup_database(self):
        """Initialize and configure database"""
        self.log("🗄️  Setting up database...")

        db_path = self.project_root / 'ultra_pinnacle.db'

        # Database will be initialized by the application
        # Just ensure the file is writable
        if db_path.exists():
            db_path.unlink()  # Remove old database for fresh start

        self.log("✅ Database setup completed")

    async def configure_services(self):
        """Configure system services and startup scripts"""
        self.log("🔧 Configuring services...")

        # Create startup script
        startup_script = self._generate_startup_script()
        startup_path = self.project_root / 'start_autonomous.sh'

        with open(startup_path, 'w') as f:
            f.write(startup_script)

        # Make executable on Unix systems
        if platform.system() != 'Windows':
            os.chmod(startup_path, 0o755)

        # Create systemd service file for Linux
        if self.config.platform == PlatformType.LINUX:
            await self._create_systemd_service()

        self.log("✅ Services configured")

    async def setup_security(self):
        """Configure security settings and certificates"""
        self.log("🔒 Setting up security...")

        # Generate SSL certificates if enabled
        if self.config.enable_ssl:
            await self._generate_ssl_certificates()

        # Create .env file with secrets
        env_content = self._generate_environment_file()
        env_path = self.project_root / '.env'

        with open(env_path, 'w') as f:
            f.write(env_content)

        self.log("✅ Security setup completed")

    async def setup_domain_networking(self):
        """Configure domain and networking"""
        self.log("🌐 Setting up domain and networking...")

        if self.config.domain_name:
            # Generate nginx configuration for custom domain
            nginx_config = self._generate_nginx_config()
            nginx_path = self.project_root / 'nginx' / 'nginx.conf'

            nginx_path.parent.mkdir(parents=True, exist_ok=True)
            with open(nginx_path, 'w') as f:
                f.write(nginx_config)

        self.log("✅ Domain and networking configured")

    async def final_setup(self):
        """Perform final setup tasks"""
        self.log("🎯 Performing final setup...")

        # Create deployment manifest
        manifest = {
            "deployment_id": secrets.token_hex(16),
            "timestamp": self.start_time.isoformat(),
            "config": asdict(self.config),
            "platform_info": {
                "system": platform.system(),
                "release": platform.release(),
                "version": platform.version(),
                "machine": platform.machine(),
                "processor": platform.processor()
            },
            "checksums": await self._generate_checksums()
        }

        manifest_path = self.project_root / 'deployment_manifest.json'
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f, indent=2)

        # Create uninstall script
        uninstall_script = self._generate_uninstall_script()
        uninstall_path = self.project_root / 'uninstall.sh'

        with open(uninstall_path, 'w') as f:
            f.write(uninstall_script)

        if platform.system() != 'Windows':
            os.chmod(uninstall_path, 0o755)

        self.log("✅ Final setup completed")

    def _generate_startup_script(self) -> str:
        """Generate platform-specific startup script"""
        if platform.system() == 'Windows':
            return self._generate_windows_startup_script()
        else:
            return self._generate_unix_startup_script()

    def _generate_unix_startup_script(self) -> str:
        return '''#!/bin/bash
# Ultra Pinnacle Studio - Autonomous Startup Script

cd "$(dirname "$0")"

echo "🚀 Starting Ultra Pinnacle Studio (Autonomous Mode)..."
echo "Platform: Linux/macOS"
echo "Mode: {self.config.mode.value}"
echo "Time: $(date)"

# Activate virtual environment
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Start the main application
python start_server.py &

# Start monitoring if enabled
if [ "{self.config.enable_monitoring}" = "True" ]; then
    python -m uvicorn api_gateway.metrics_dashboard:app --port {self.config.custom_ports["monitoring"]} --host 0.0.0.0 &
fi

echo "✅ Ultra Pinnacle Studio is running!"
echo "📡 API: http://localhost:{self.config.custom_ports["api"]}"
echo "🌐 Web UI: http://localhost:{self.config.custom_ports["web_ui"]}"
echo "📊 Monitoring: http://localhost:{self.config.custom_ports["monitoring"]}"

# Wait for processes
wait
'''

    def _generate_windows_startup_script(self) -> str:
        return '''@echo off
REM Ultra Pinnacle Studio - Autonomous Startup Script (Windows)

echo 🚀 Starting Ultra Pinnacle Studio (Autonomous Mode)...
echo Platform: Windows
echo Mode: {self.config.mode.value}
echo Time: %date% %time%

REM Activate virtual environment
if exist venv\\Scripts\\activate.bat (
    call venv\\Scripts\\activate.bat
)

REM Start the main application
start /B python start_server.py

REM Start monitoring if enabled
if "{self.config.enable_monitoring}" == "True" (
    start /B python -m uvicorn api_gateway.metrics_dashboard:app --port {self.config.custom_ports["monitoring"]} --host 0.0.0.0
)

echo ✅ Ultra Pinnacle Studio is running!
echo 📡 API: http://localhost:{self.config.custom_ports["api"]}
echo 🌐 Web UI: http://localhost:{self.config.custom_ports["web_ui"]}
echo 📊 Monitoring: http://localhost:{self.config.custom_ports["monitoring"]}

pause
'''

    async def _create_systemd_service(self):
        """Create systemd service file for Linux"""
        service_content = f'''[Unit]
Description=Ultra Pinnacle Studio - Autonomous AI Platform
After=network.target

[Service]
Type=simple
User={os.getlogin()}
WorkingDirectory={self.project_root}
ExecStart={self.project_root}/venv/bin/python {self.project_root}/start_server.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
'''

        service_path = self.project_root / 'ultra-pinnacle-studio.service'
        with open(service_path, 'w') as f:
            f.write(service_content)

        self.log("📄 Systemd service file created")

    async def _generate_ssl_certificates(self):
        """Generate self-signed SSL certificates"""
        self.log("🔐 Generating SSL certificates...")

        ssl_dir = self.project_root / 'ssl' / 'certs'
        key_path = self.project_root / 'ssl' / 'private' / 'key.pem'
        cert_path = ssl_dir / 'cert.pem'

        # Create SSL directories
        ssl_dir.mkdir(parents=True, exist_ok=True)
        key_path.parent.mkdir(parents=True, exist_ok=True)

        # Generate private key
        subprocess.run([
            'openssl', 'genpkey', '-algorithm', 'RSA', '-out', str(key_path), '-pkcs8'
        ], check=True)

        # Generate self-signed certificate
        subprocess.run([
            'openssl', 'req', '-new', '-x509', '-key', str(key_path), '-out', str(cert_path),
            '-days', '365', '-subj', '/C=US/ST=State/L=City/O=Organization/CN=localhost'
        ], check=True)

        self.log("✅ SSL certificates generated")

    def _generate_environment_file(self) -> str:
        """Generate .env file with secrets"""
        jwt_secret = secrets.token_urlsafe(32)

        env_vars = [
            f"JWT_SECRET={jwt_secret}",
            f"ENVIRONMENT={self.config.mode.value}",
            f"PLATFORM={self.config.platform.value}",
            "LOG_LEVEL=INFO",
            "DATABASE_URL=sqlite:///./ultra_pinnacle.db",
            "AUTO_DEPLOYMENT=true",
            "AUTO_HEALING=true",
            "CROSS_DEVICE_SYNC=true"
        ]

        if self.config.domain_name:
            env_vars.append(f"CUSTOM_DOMAIN={self.config.domain_name}")

        return '\n'.join(env_vars)

    def _generate_nginx_config(self) -> str:
        """Generate nginx configuration for custom domain"""
        return f'''server {{
    listen 80;
    server_name {self.config.domain_name} *.{self.config.domain_name};

    location / {{
        proxy_pass http://localhost:{self.config.custom_ports["api"]};
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }}

    location /web_ui {{
        proxy_pass http://localhost:{self.config.custom_ports["web_ui"]};
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }}
}}

server {{
    listen 443 ssl http2;
    server_name {self.config.domain_name} *.{self.config.domain_name};

    ssl_certificate ssl/certs/cert.pem;
    ssl_certificate_key ssl/private/key.pem;

    location / {{
        proxy_pass http://localhost:{self.config.custom_ports["api"]};
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }}
}}
'''

    def _generate_uninstall_script(self) -> str:
        """Generate uninstall script"""
        return '''#!/bin/bash
# Ultra Pinnacle Studio - Uninstall Script

echo "🗑️  Uninstalling Ultra Pinnacle Studio..."

# Stop services
echo "Stopping services..."
pkill -f "python.*start_server.py" || true
pkill -f "uvicorn" || true

# Remove directories
echo "Removing files..."
rm -rf venv
rm -rf models/*
rm -rf logs/*
rm -rf uploads/*
rm -rf ssl
rm -f ultra_pinnacle.db
rm -f deployment_manifest.json

echo "✅ Ultra Pinnacle Studio has been uninstalled"
'''

    async def _generate_checksums(self) -> Dict[str, str]:
        """Generate checksums for verification"""
        checksums = {}

        important_files = [
            'requirements.txt', 'config.json', 'start_server.py'
        ]

        for file_path in important_files:
            full_path = self.project_root / file_path
            if full_path.exists():
                with open(full_path, 'rb') as f:
                    checksums[file_path] = hashlib.sha256(f.read()).hexdigest()

        return checksums

    def detect_platform(self) -> PlatformType:
        """Detect current platform"""
        system = platform.system().lower()
        if system == 'windows':
            return PlatformType.WINDOWS
        elif system == 'darwin':
            return PlatformType.MACOS
        elif system == 'linux':
            return PlatformType.LINUX
        else:
            return PlatformType.LINUX  # Default fallback

    def log(self, message: str, level: str = "info"):
        """Log deployment messages"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}"

        self.deployment_log.append({
            "timestamp": timestamp,
            "level": level,
            "message": message
        })

        print(log_entry)

        # Also write to deployment log file
        log_path = self.project_root / 'logs' / 'deployment.log'
        with open(log_path, 'a') as f:
            f.write(log_entry + '\n')

async def main():
    """Main deployment function"""
    if len(sys.argv) < 2:
        print("Usage: python deployment_engine.py <mode> [domain]")
        print("Modes: quick, custom, enterprise")
        sys.exit(1)

    mode_str = sys.argv[1]
    domain = sys.argv[2] if len(sys.argv) > 2 else ""

    try:
        mode = DeploymentMode(mode_str)
    except ValueError:
        print(f"Invalid mode: {mode_str}")
        print("Valid modes: quick, custom, enterprise")
        sys.exit(1)

    # Create deployment configuration
    config = DeploymentConfig(
        mode=mode,
        platform=PlatformType.DOCKER if os.environ.get('DOCKER') else PlatformType.LINUX,
        domain_name=domain,
        enable_ssl=True,
        enable_monitoring=True,
        enable_backups=True
    )

    # Run deployment
    engine = DeploymentEngine(config)
    success = await engine.deploy()

    if success:
        print("\n🎉 Deployment completed successfully!")
        print("🚀 You can now start Ultra Pinnacle Studio with: python start_server.py")
        sys.exit(0)
    else:
        print("\n❌ Deployment failed!")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())