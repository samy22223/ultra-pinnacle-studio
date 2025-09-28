#!/usr/bin/env python3
"""
Comprehensive Validation Script for Ultra Pinnacle AI Studio
Runs all validation checks and provides a complete project health report
"""

import os
import sys
import json
import subprocess
from pathlib import Path

def check_result(name, success, details=''):
    """Format and display validation result"""
    status = '✅' if success else '❌'
    print(f'{status} {name}')
    if details and not success:
        print(f'   └─ {details}')
    return success

def validate_python_compilation():
    """Check Python file compilation"""
    print('\n📄 PYTHON COMPILATION')
    passed = True
    py_files = []

    for root, dirs, files in os.walk('..'):
        for file in files:
            if file.endswith('.py') and not file.startswith('__'):
                py_files.append(os.path.join(root, file))

    for filepath in py_files:
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                source = f.read()
            compile(source, filepath, 'exec')
        except SyntaxError as e:
            check_result(f'Compile {os.path.basename(filepath)}', False, f'Syntax error: {e}')
            passed = False
        except Exception as e:
            check_result(f'Compile {os.path.basename(filepath)}', False, f'Error: {e}')
            passed = False

    return check_result(f'All {len(py_files)} Python files compile successfully', passed)

def validate_imports():
    """Check module imports"""
    print('\n📦 IMPORT VALIDATION')
    # Add the project root to Python path
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, project_root)

    # Change to project root directory for imports
    original_cwd = os.getcwd()
    os.chdir(project_root)

    try:
        modules_to_test = [
            ('api_gateway.main', 'from api_gateway.main import app'),
            ('api_gateway.auth', 'from api_gateway.auth import authenticate_user'),
            ('api_gateway.models', 'from api_gateway.models import ModelManager'),
            ('api_gateway.workers', 'from api_gateway.workers import WorkerManager'),
            ('api_gateway.logging_config', 'from api_gateway.logging_config import logger')
        ]

        passed = True
        for module_name, import_stmt in modules_to_test:
            try:
                exec(import_stmt)
                check_result(f'{module_name} import', True)
            except Exception as e:
                check_result(f'{module_name} import', False, str(e))
                passed = False

        return check_result('All core modules import successfully', passed)
    finally:
        # Restore original working directory
        os.chdir(original_cwd)

def validate_configuration():
    """Check configuration files"""
    print('\n⚙️ CONFIGURATION VALIDATION')

    # Check config.json
    config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config.json')
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)

        required_keys = ['app', 'models', 'security', 'paths', 'features']
        config_valid = all(key in config for key in required_keys)

        if config_valid:
            check_result('config.json structure', True)
        else:
            missing = [k for k in required_keys if k not in config]
            check_result('config.json structure', False, f'Missing keys: {missing}')
            return False

    except Exception as e:
        check_result('config.json validation', False, str(e))
        return False

    # Check requirements.txt exists
    req_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'requirements.txt')
    if os.path.exists(req_path):
        check_result('requirements.txt exists', True)
    else:
        check_result('requirements.txt exists', False)
        return False

    return check_result('Configuration files valid', True)

def validate_dependencies():
    """Check Python dependencies"""
    print('\n📋 DEPENDENCIES VALIDATION')
    try:
        import pkg_resources
        req_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'requirements.txt')
        with open(req_path, 'r') as f:
            deps = [line.strip() for line in f if line.strip() and not line.startswith('#')]

        passed = True
        for dep in deps:
            try:
                pkg_resources.Requirement.parse(dep)
            except Exception:
                passed = False
                break

        return check_result(f'All {len(deps)} dependencies properly formatted', passed)

    except Exception as e:
        return check_result('Dependencies validation', False, str(e))

def validate_web_ui():
    """Check web UI structure"""
    print('\n🌐 WEB UI VALIDATION')
    try:
        web_ui_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'web_ui', 'index.html')
        if os.path.exists(web_ui_path):
            with open(web_ui_path, 'r', encoding='utf-8') as f:
                content = f.read()

            checks = [
                ('DOCTYPE', '<!DOCTYPE html>' in content),
                ('HTML tags', '<html' in content and '</html>' in content),
                ('Head section', '<head>' in content and '</head>' in content),
                ('Body section', '<body>' in content and '</body>' in content),
                ('JavaScript', '<script>' in content and '</script>' in content)
            ]

            html_valid = all(result for _, result in checks)
            return check_result('Web UI HTML structure', html_valid)
        else:
            return check_result('Web UI file exists', False, 'web_ui/index.html not found')

    except Exception as e:
        return check_result('Web UI validation', False, str(e))

def validate_encyclopedia():
    """Check encyclopedia files"""
    print('\n📚 ENCYCLOPEDIA VALIDATION')
    try:
        encyclopedia_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'encyclopedia')
        if os.path.exists(encyclopedia_dir):
            files = [f for f in os.listdir(encyclopedia_dir) if f.endswith('.md')]

            if len(files) >= 5:
                check_result(f'Encyclopedia files ({len(files)} found)', True)

                # Check each file has content
                valid_files = 0
                for file in files:
                    file_path = os.path.join(encyclopedia_dir, file)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            if content.startswith('# ') and len(content.strip()) > 10:
                                valid_files += 1
                    except Exception:
                        pass

                passed = valid_files >= len(files) * 0.8
                return check_result(f'Encyclopedia content validation ({valid_files}/{len(files)} valid)', passed)
            else:
                return check_result('Encyclopedia files', False, f'Only {len(files)} files, expected >= 5')
        else:
            return check_result('Encyclopedia directory', False, 'Directory not found')

    except Exception as e:
        return check_result('Encyclopedia validation', False, str(e))

def validate_directory_structure():
    """Check required directories exist"""
    print('\n📁 DIRECTORY STRUCTURE')
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    required_dirs = ['api_gateway', 'encyclopedia', 'models', 'web_ui', 'tests', 'logs', 'uploads']

    passed = True
    for dir_name in required_dirs:
        full_path = os.path.join(project_root, dir_name)
        if os.path.exists(full_path):
            check_result(f'Directory {dir_name}', True)
        else:
            check_result(f'Directory {dir_name}', False, 'Missing')
            passed = False

    return check_result('All required directories present', passed)

def validate_server_startup():
    """Check server can start"""
    print('\n🚀 SERVER STARTUP VALIDATION')
    try:
        # Change to project root for proper imports
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        original_cwd = os.getcwd()
        os.chdir(project_root)

        sys.path.insert(0, project_root)
        from api_gateway.main import app
        from fastapi.testclient import TestClient

        client = TestClient(app)
        response = client.get('/')
        startup_ok = response.status_code == 200

        return check_result('Server startup and root endpoint', startup_ok)

    except Exception as e:
        return check_result('Server startup', False, str(e))
    finally:
        os.chdir(original_cwd)

def validate_api_endpoints():
    """Check API endpoints are accessible"""
    print('\n🔗 API ENDPOINTS VALIDATION')
    try:
        # Change to project root for proper imports
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        original_cwd = os.getcwd()
        os.chdir(project_root)

        sys.path.insert(0, project_root)
        from api_gateway.main import app
        from fastapi.testclient import TestClient

        client = TestClient(app)

        endpoints_to_test = [
            ('GET', '/'),
            ('GET', '/health'),
            ('GET', '/models'),
            ('GET', '/workers'),
            ('POST', '/auth/login'),
            ('GET', '/encyclopedia/list'),
        ]

        passed = True
        for method, endpoint in endpoints_to_test:
            try:
                if method == 'GET':
                    response = client.get(endpoint)
                elif method == 'POST':
                    if endpoint == '/auth/login':
                        response = client.post(endpoint, json={'username': 'demo', 'password': 'demo123'})
                    else:
                        response = client.post(endpoint, json={})

                if response.status_code not in [200, 201, 422]:
                    check_result(f'{method} {endpoint}', False, f'Status: {response.status_code}')
                    passed = False
            except Exception as e:
                check_result(f'{method} {endpoint}', False, str(e))
                passed = False

        return check_result('All API endpoints accessible', passed)

    except Exception as e:
        return check_result('API endpoints validation', False, str(e))
    finally:
        os.chdir(original_cwd)

def validate_test_suite():
    """Check test suite runs"""
    print('\n🧪 TEST SUITE VALIDATION')
    try:
        # Change to project root for proper test execution
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        original_cwd = os.getcwd()
        os.chdir(project_root)

        result = subprocess.run([sys.executable, '-m', 'pytest', 'tests/test_api.py', '--tb=no', '-q'],
                              capture_output=True, text=True, cwd='.')

        if result.returncode == 0:
            return check_result('Test suite execution', True, 'All tests passed')
        else:
            return check_result('Test suite execution', False, f'Some tests failed: {result.stderr.strip()}')

    except Exception as e:
        return check_result('Test suite validation', False, str(e))
    finally:
        os.chdir(original_cwd)

def main():
    """Run comprehensive validation"""
    print('🔍 COMPREHENSIVE VALIDATION: Ultra Pinnacle AI Studio')
    print('=' * 60)

    # Run all validation checks
    checks = [
        validate_python_compilation,
        validate_imports,
        validate_configuration,
        validate_dependencies,
        validate_web_ui,
        validate_encyclopedia,
        validate_directory_structure,
        validate_server_startup,
        validate_api_endpoints,
        validate_test_suite,
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
        print('🎉 ALL VALIDATION CHECKS PASSED!')
        print('✅ Ultra Pinnacle AI Studio is fully functional and validated')
        print('\n🚀 Ready for offline AI development!')
    else:
        print(f'⚠️ {passed_count}/{total_count} validation checks passed')
        print('❌ Some issues found - review output above')

    print('=' * 60)

    return passed_count == total_count

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)