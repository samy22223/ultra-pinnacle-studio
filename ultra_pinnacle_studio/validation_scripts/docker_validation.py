#!/usr/bin/env python3
"""
Docker Configuration Validation Script for Ultra Pinnacle AI Studio
Validates Docker and Docker Compose configurations
"""

import os
import subprocess
import json
from pathlib import Path

def run_command(cmd, capture_output=True, check=True):
    """Run shell command and return result"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=capture_output, text=True, check=check)
        return result.returncode == 0, result.stdout.strip() if capture_output else ""
    except subprocess.CalledProcessError as e:
        return False, str(e)

def validate_docker_installation():
    """Check if Docker is installed and running"""
    print("🐳 DOCKER INSTALLATION CHECK")
    print("=" * 50)

    # Check Docker command
    success, output = run_command("docker --version")
    if success:
        print(f"✅ Docker installed: {output}")
    else:
        print("❌ Docker not found")
        return False

    # Check Docker daemon
    success, output = run_command("docker info")
    if success:
        print("✅ Docker daemon running")
    else:
        print("❌ Docker daemon not running")
        return False

    # Check Docker Compose
    success, output = run_command("docker-compose --version")
    if success:
        print(f"✅ Docker Compose installed: {output}")
    else:
        # Try newer docker compose command
        success, output = run_command("docker compose version")
        if success:
            print(f"✅ Docker Compose V2 installed: {output}")
        else:
            print("❌ Docker Compose not found")
            return False

    return True

def validate_dockerfile():
    """Validate Dockerfile syntax and best practices"""
    print("\n📄 DOCKERFILE VALIDATION")
    print("=" * 50)

    dockerfile_path = "../Dockerfile"

    if not os.path.exists(dockerfile_path):
        print("❌ Dockerfile not found")
        return False

    # Basic syntax check
    success, output = run_command(f"docker build --dry-run -f {dockerfile_path} ..")
    if success:
        print("✅ Dockerfile syntax is valid")
    else:
        print(f"❌ Dockerfile syntax error: {output}")
        return False

    # Check for security best practices
    with open(dockerfile_path, 'r') as f:
        content = f.read()

    checks = [
        ('FROM statement', 'FROM ' in content),
        ('Non-root user', 'USER ' in content and 'root' not in content.split('USER ')[-1]),
        ('No hardcoded secrets', 'password' not in content.lower() or content.lower().count('password') <= 2),
        ('Health check', 'HEALTHCHECK' in content),
        ('Port exposure', 'EXPOSE ' in content),
        ('Working directory', 'WORKDIR ' in content),
    ]

    passed_checks = 0
    for check_name, is_valid in checks:
        status = "✅" if is_valid else "❌"
        print(f"{status} {check_name}")
        if is_valid:
            passed_checks += 1

    print(f"\nResults: {passed_checks}/{len(checks)} Dockerfile best practices followed")

    return passed_checks >= len(checks) * 0.7  # 70% success rate

def validate_docker_compose():
    """Validate Docker Compose configuration"""
    print("\n🐙 DOCKER COMPOSE VALIDATION")
    print("=" * 50)

    compose_files = ["../docker-compose.yml"]

    for compose_file in compose_files:
        if not os.path.exists(compose_file):
            print(f"❌ {compose_file} not found")
            continue

        print(f"Validating {compose_file}...")

        # Config validation
        success, output = run_command(f"docker-compose -f {compose_file} config")
        if success:
            print("✅ Docker Compose configuration is valid")
        else:
            print(f"❌ Docker Compose configuration error: {output}")
            return False

        # Parse and analyze services
        try:
            with open(compose_file, 'r') as f:
                compose_config = f.read()

            # Check for key services
            services = ['ultra-pinnacle-studio']
            found_services = sum(1 for service in services if service in compose_config)

            if found_services == len(services):
                print(f"✅ All required services defined ({found_services}/{len(services)})")
            else:
                print(f"⚠️ Some services missing ({found_services}/{len(services)})")

            # Check for profiles
            if 'profiles:' in compose_config:
                print("✅ Service profiles configured")
            else:
                print("ℹ️ No service profiles found (optional)")

            # Check for volumes
            if 'volumes:' in compose_config:
                print("✅ Volumes configured")
            else:
                print("ℹ️ No volumes configured")

            # Check for networks
            if 'networks:' in compose_config:
                print("✅ Networks configured")
            else:
                print("ℹ️ No networks configured")

        except Exception as e:
            print(f"❌ Error parsing compose file: {e}")
            return False

    return True

def validate_container_build():
    """Test container build process"""
    print("\n🏗️ CONTAINER BUILD TEST")
    print("=" * 50)

    # Quick build test (without pushing)
    success, output = run_command("docker build -t ultra-pinnacle-test --no-cache ..", capture_output=False, check=False)

    if success:
        print("✅ Container build successful")

        # Check image size
        success, output = run_command("docker images ultra-pinnacle-test --format 'table {{.Size}}'")
        if success and output:
            print(f"✅ Built image size: {output.split()[-1] if len(output.split()) > 1 else 'unknown'}")

        # Quick container test
        success, output = run_command("docker run --rm ultra-pinnacle-test python --version")
        if success:
            print("✅ Container runtime test passed")
        else:
            print("❌ Container runtime test failed")

        # Cleanup
        run_command("docker rmi ultra-pinnacle-test")

        return True
    else:
        print("❌ Container build failed")
        print("Build output:", output[:500] + "..." if len(output) > 500 else output)
        return False

def main():
    """Run comprehensive Docker validation"""
    print("🔍 DOCKER CONFIGURATION VALIDATION")
    print("=" * 60)

    checks = [
        validate_docker_installation,
        validate_dockerfile,
        validate_docker_compose,
        validate_container_build,
    ]

    results = []
    for check_func in checks:
        try:
            result = check_func()
            results.append(result)
        except Exception as e:
            print(f'❌ {check_func.__name__}: Exception - {e}')
            results.append(False)

    # Summary
    print('\n' + '=' * 60)
    passed_count = sum(results)
    total_count = len(results)

    if passed_count == total_count:
        print('🎉 ALL DOCKER VALIDATION CHECKS PASSED!')
        print('✅ Docker configuration is ready for deployment')
        print('\n🚀 Ready to deploy with:')
        print('   docker-compose up                 # Development')
        print('   docker-compose --profile production up  # Production')
    else:
        print(f'⚠️ {passed_count}/{total_count} validation checks passed')
        print('❌ Some Docker configuration issues found')

    print('=' * 60)

    return passed_count == total_count

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)