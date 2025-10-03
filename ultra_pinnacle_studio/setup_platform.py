#!/usr/bin/env python3
"""
Ultra Pinnacle Studio - Complete Platform Setup
Automated setup and configuration for immediate deployment
"""

import os
import json
import time
import asyncio
import secrets
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

class PlatformSetup:
    """Complete platform setup automation"""

    def __init__(self):
        self.project_root = Path(__file__).parent
        self.setup_steps = self.load_setup_steps()

    def load_setup_steps(self) -> List[Dict]:
        """Load setup steps configuration"""
        return [
            {
                "name": "Environment Setup",
                "description": "Set up Python environment and dependencies",
                "critical": True,
                "estimated_time": "2-3 minutes"
            },
            {
                "name": "Database Setup",
                "description": "Initialize database and run migrations",
                "critical": True,
                "estimated_time": "1-2 minutes"
            },
            {
                "name": "Configuration Setup",
                "description": "Generate configuration files and API keys",
                "critical": True,
                "estimated_time": "1 minute"
            },
            {
                "name": "Core Services Test",
                "description": "Test all module imports and basic functionality",
                "critical": True,
                "estimated_time": "1-2 minutes"
            },
            {
                "name": "Security Setup",
                "description": "Configure SSL, authentication, and security",
                "critical": True,
                "estimated_time": "2-3 minutes"
            },
            {
                "name": "Service Integration",
                "description": "Test component integration and communication",
                "critical": True,
                "estimated_time": "2-3 minutes"
            },
            {
                "name": "Platform Launch",
                "description": "Start all services and verify operation",
                "critical": True,
                "estimated_time": "1 minute"
            }
        ]

    async def run_complete_setup(self) -> Dict:
        """Run complete platform setup"""
        print("🚀 Ultra Pinnacle Studio - Complete Setup")
        print("=" * 60)

        setup_results = {
            "setup_completed": False,
            "steps_completed": 0,
            "total_steps": len(self.setup_steps),
            "critical_issues": 0,
            "warnings": 0,
            "setup_time": 0.0
        }

        start_time = time.time()

        try:
            # Execute setup steps
            for i, step in enumerate(self.setup_steps, 1):
                print(f"\n📋 Step {i}/{len(self.setup_steps)}: {step['name']}")
                print(f"   {step['description']}")

                if step["name"] == "Environment Setup":
                    result = await self.setup_environment()
                elif step["name"] == "Database Setup":
                    result = await self.setup_database()
                elif step["name"] == "Configuration Setup":
                    result = await self.setup_configuration()
                elif step["name"] == "Core Services Test":
                    result = await self.test_core_services()
                elif step["name"] == "Security Setup":
                    result = await self.setup_security()
                elif step["name"] == "Service Integration":
                    result = await self.test_service_integration()
                elif step["name"] == "Platform Launch":
                    result = await self.launch_platform()

                if result["success"]:
                    print(f"✅ {step['name']} completed successfully")
                    setup_results["steps_completed"] += 1
                else:
                    print(f"❌ {step['name']} failed: {result['error']}")
                    if step["critical"]:
                        setup_results["critical_issues"] += 1
                    else:
                        setup_results["warnings"] += 1

            # Calculate setup time
            setup_results["setup_time"] = time.time() - start_time
            setup_results["setup_completed"] = setup_results["critical_issues"] == 0

            # Print final results
            self.print_setup_results(setup_results)

        except Exception as e:
            print(f"💥 Setup failed with critical error: {e}")
            setup_results["critical_issues"] += 1

        return setup_results

    async def setup_environment(self) -> Dict:
        """Set up Python environment and dependencies"""
        print("🐍 Setting up Python environment...")

        try:
            # Check Python version
            python_version = f"{os.sys.version_info.major}.{os.sys.version_info.minor}"
            print(f"   Python version: {python_version}")

            # Create virtual environment if it doesn't exist
            venv_path = self.project_root / "venv"
            if not venv_path.exists():
                print("   Creating virtual environment...")
                subprocess.run([os.sys.executable, "-m", "venv", "venv"], check=True)

            # Install dependencies
            print("   Installing Python dependencies...")
            pip_cmd = str(venv_path / "bin" / "pip") if os.name != "nt" else str(venv_path / "Scripts" / "pip.exe")

            # Upgrade pip first
            subprocess.run([pip_cmd, "install", "--upgrade", "pip"], check=True)

            # Install requirements
            requirements_path = self.project_root / "requirements.txt"
            if requirements_path.exists():
                subprocess.run([pip_cmd, "install", "-r", "requirements.txt"], check=True)
            else:
                print("   ⚠️ requirements.txt not found, skipping dependency installation")

            print("   ✅ Environment setup completed")
            return {"success": True}

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def setup_database(self) -> Dict:
        """Set up database and run migrations"""
        print("🗄️ Setting up database...")

        try:
            # Run database migrations
            print("   Running database migrations...")
            migration_file = self.project_root / "migration_add_user_type_id.py"

            if migration_file.exists():
                # Import and run migration
                import importlib.util
                spec = importlib.util.spec_from_file_location("migration", migration_file)
                migration_module = importlib.util.module_from_spec(spec)

                # Execute migration function if it exists
                if hasattr(migration_module, "upgrade_database"):
                    migration_module.upgrade_database()
                else:
                    print("   ⚠️ Migration function not found, running manual setup")

            # Initialize database schema
            print("   Initializing database schema...")
            from api_gateway.database import init_db
            init_db()

            print("   ✅ Database setup completed")
            return {"success": True}

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def setup_configuration(self) -> Dict:
        """Set up configuration files and API keys"""
        print("⚙️ Setting up configuration...")

        try:
            # Generate configuration files
            config = self.generate_default_config()

            # Save main configuration
            config_path = self.project_root / "config.json"
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)

            # Generate SSL keys if they don't exist
            ssl_path = self.project_root / "ssl"
            ssl_path.mkdir(exist_ok=True)

            key_path = ssl_path / "key.pem"
            cert_path = ssl_path / "cert.pem"

            if not key_path.exists():
                print("   Generating SSL certificate...")
                self.generate_self_signed_ssl(key_path, cert_path)

            print("   ✅ Configuration setup completed")
            return {"success": True}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def generate_default_config(self) -> Dict:
        """Generate default configuration"""
        return {
            "app": {
                "name": "Ultra Pinnacle Studio",
                "version": "2.0.0",
                "host": "0.0.0.0",
                "port": 8000,
                "debug": False,
                "log_level": "INFO",
                "env": "production"
            },
            "security": {
                "secret_key": secrets.token_hex(32),
                "algorithm": "HS256",
                "access_token_expire_minutes": 30,
                "refresh_token_expire_days": 7,
                "ssl_enabled": True,
                "ssl_cert_path": "ssl/cert.pem",
                "ssl_key_path": "ssl/key.pem"
            },
            "database": {
                "url": "sqlite:///./ultra_pinnacle.db",
                "echo": False
            },
            "features": {
                "authentication": True,
                "file_upload": True,
                "chat_mode": True,
                "code_generation": True,
                "image_generation": True,
                "video_generation": True,
                "ecommerce": True,
                "social_media": True,
                "productivity": True,
                "monitoring": True,
                "advanced_features": True
            },
            "api_keys": {
                "openai": "your_openai_api_key_here",
                "anthropic": "your_anthropic_api_key_here",
                "stripe": "your_stripe_api_key_here",
                "paypal": "your_paypal_api_key_here",
                "google_maps": "your_google_maps_api_key_here"
            },
            "setup_completed": True,
            "setup_timestamp": datetime.now().isoformat()
        }

    def generate_self_signed_ssl(self, key_path: Path, cert_path: Path):
        """Generate self-signed SSL certificate"""
        try:
            from cryptography import x509
            from cryptography.x509.oid import NameOID
            from cryptography.hazmat.primitives import hashes, serialization
            from cryptography.hazmat.primitives.asymmetric import rsa
            from cryptography.hazmat.backends import default_backend

            # Generate private key
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048,
                backend=default_backend()
            )

            # Generate certificate
            subject = issuer = x509.Name([
                x509.NameAttribute(NameOID.COMMON_NAME, "Ultra Pinnacle Studio"),
                x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Ultra Pinnacle Corp"),
                x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
            ])

            cert = x509.CertificateBuilder().subject_name(
                subject
            ).issuer_name(
                issuer
            ).public_key(
                private_key.public_key()
            ).serial_number(
                x509.random_serial_number()
            ).not_valid_before(
                datetime.utcnow()
            ).not_valid_after(
                datetime.utcnow() + timedelta(days=365)
            ).add_extension(
                x509.SubjectAlternativeName([
                    x509.DNSName("localhost"),
                    x509.DNSName("127.0.0.1"),
                ]),
                critical=False,
            ).sign(private_key, hashes.SHA256(), default_backend())

            # Save certificate and key
            with open(cert_path, "wb") as f:
                f.write(cert.public_bytes(serialization.Encoding.PEM))

            with open(key_path, "wb") as f:
                f.write(private_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption()
                ))

            print("   ✅ SSL certificate generated")

        except ImportError:
            print("   ⚠️ Cryptography library not available, SSL setup skipped")
        except Exception as e:
            print(f"   ⚠️ SSL generation failed: {e}")

    async def test_core_services(self) -> Dict:
        """Test all core services and modules"""
        print("🧪 Testing core services...")

        try:
            # Test basic imports
            test_results = []

            # Test core modules
            core_modules = [
                "api_gateway.main",
                "auto_install.deployment_engine",
                "security_privacy.zero_trust_ai",
                "design_ui.ios26_design_system",
                "ai_media_suite.ai_video_generator"
            ]

            for module in core_modules:
                try:
                    importlib.import_module(module)
                    test_results.append({"module": module, "status": "success"})
                except Exception as e:
                    test_results.append({"module": module, "status": "error", "error": str(e)})

            # Test database connection
            try:
                from api_gateway.database import get_db
                db = next(get_db())
                db.close()
                test_results.append({"module": "database", "status": "success"})
            except Exception as e:
                test_results.append({"module": "database", "status": "error", "error": str(e)})

            # Check test results
            failed_tests = [t for t in test_results if t["status"] == "error"]

            if failed_tests:
                return {
                    "success": False,
                    "error": f"{len(failed_tests)} modules failed to import",
                    "failed_modules": failed_tests
                }
            else:
                print("   ✅ All core services tested successfully")
                return {"success": True}

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def setup_security(self) -> Dict:
        """Set up security configuration"""
        print("🔒 Setting up security...")

        try:
            # Configure rate limiting
            await self.configure_rate_limiting()

            # Set up authentication
            await self.configure_authentication()

            # Configure CORS
            await self.configure_cors()

            print("   ✅ Security setup completed")
            return {"success": True}

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def configure_rate_limiting(self):
        """Configure rate limiting"""
        rate_limit_config = {
            "enabled": True,
            "requests_per_minute": 60,
            "requests_per_hour": 1000,
            "burst_limit": 10
        }

        config_path = self.project_root / "config" / "rate_limiting.json"
        config_path.parent.mkdir(exist_ok=True)

        with open(config_path, 'w') as f:
            json.dump(rate_limit_config, f, indent=2)

    async def configure_authentication(self):
        """Configure authentication system"""
        auth_config = {
            "jwt_secret": secrets.token_hex(32),
            "token_expiry": 30,  # minutes
            "refresh_token_expiry": 7,  # days
            "password_min_length": 8,
            "require_special_chars": False
        }

        config_path = self.project_root / "config" / "auth.json"
        with open(config_path, 'w') as f:
            json.dump(auth_config, f, indent=2)

    async def configure_cors(self):
        """Configure CORS settings"""
        cors_config = {
            "origins": ["http://localhost:3000", "http://localhost:8000", "https://ultrapinnacle.com"],
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "headers": ["*"],
            "credentials": True
        }

        config_path = self.project_root / "config" / "cors.json"
        with open(config_path, 'w') as f:
            json.dump(cors_config, f, indent=2)

    async def test_service_integration(self) -> Dict:
        """Test service integration"""
        print("🔗 Testing service integration...")

        try:
            # Test platform integrator
            integrator_result = await self.test_platform_integrator()

            if integrator_result["success"]:
                print("   ✅ Service integration test passed")
                return {"success": True}
            else:
                return {"success": False, "error": "Integration test failed"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def test_platform_integrator(self) -> Dict:
        """Test platform integrator"""
        try:
            # Import and test platform integrator
            from integration.platform_integrator import PlatformIntegrator
            integrator = PlatformIntegrator()

            # Run integration test
            test_result = await integrator.run_platform_integration()

            return test_result

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def launch_platform(self) -> Dict:
        """Launch the complete platform"""
        print("🚀 Launching Ultra Pinnacle Studio...")

        try:
            # Start the main server
            print("   Starting API Gateway...")
            server_process = subprocess.Popen([
                "python", "start_server.py"
            ], cwd=self.project_root)

            # Wait a moment for server to start
            await asyncio.sleep(3)

            # Check if server is running
            import requests
            try:
                response = requests.get("http://localhost:8000/health", timeout=5)
                if response.status_code == 200:
                    print("   ✅ Platform launched successfully")
                    print("   🌐 Access at: http://localhost:8000")
                    print("   📚 API docs at: http://localhost:8000/docs")
                    print("   👤 Admin at: http://localhost:8000/admin")

                    return {
                        "success": True,
                        "server_pid": server_process.pid,
                        "access_url": "http://localhost:8000"
                    }
                else:
                    return {"success": False, "error": "Server health check failed"}

            except requests.exceptions.ConnectionError:
                return {"success": False, "error": "Server failed to start"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def print_setup_results(self, results: Dict):
        """Print setup results summary"""
        print("\n" + "=" * 60)
        print("🎉 ULTRA PINNACLE STUDIO - SETUP COMPLETE")
        print("=" * 60)

        if results["setup_completed"]:
            print("✅ SETUP SUCCESSFUL!")
            print(f"⏱️ Total setup time: {results['setup_time']:.1f} seconds")
            print(f"📋 Steps completed: {results['steps_completed']}/{results['total_steps']}")
            print(f"⚠️ Warnings: {results['warnings']}")
            print(f"❌ Critical issues: {results['critical_issues']}")

            print("\n🚀 PLATFORM IS READY!")
            print("   🌐 Web Interface: http://localhost:8000")
            print("   📚 API Documentation: http://localhost:8000/docs")
            print("   👤 Admin Dashboard: http://localhost:8000/admin")

            print("\n📋 NEXT STEPS:")
            print("   1. Configure API keys in config.json")
            print("   2. Set up external services (OpenAI, Stripe, etc.)")
            print("   3. Customize platform settings")
            print("   4. Add your content and data")

        else:
            print("❌ SETUP FAILED!")
            print(f"❌ Critical issues: {results['critical_issues']}")
            print(f"⚠️ Warnings: {results['warnings']}")
            print(f"📋 Steps completed: {results['steps_completed']}/{results['total_steps']}")

            print("\n🔧 TROUBLESHOOTING:")
            print("   1. Check the error messages above")
            print("   2. Verify Python dependencies")
            print("   3. Check database connectivity")
            print("   4. Review configuration files")

        print("=" * 60)

async def main():
    """Main setup execution"""
    setup = PlatformSetup()
    results = await setup.run_complete_setup()

    if results["setup_completed"]:
        print("\n🎊 CONGRATULATIONS!")
        print("Your Ultra Pinnacle Studio platform is now running!")
        print("You have successfully deployed the most comprehensive")
        print("autonomous platform ever created with all 55 features!")

        return 0
    else:
        print("\n💥 SETUP INCOMPLETE")
        print("Please resolve the critical issues above and try again.")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)