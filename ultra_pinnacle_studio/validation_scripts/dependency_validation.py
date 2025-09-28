#!/usr/bin/env python3
"""
Dependency Validation Script for Ultra Pinnacle AI Studio
Validates that all Python dependencies in requirements.txt are properly formatted
"""

import pkg_resources

def validate_dependencies():
    """Validate all dependencies in requirements.txt"""
    print("🔍 DEPENDENCY VALIDATION")
    print("=" * 50)

    try:
        with open('../requirements.txt', 'r') as f:
            deps = [line.strip() for line in f if line.strip() and not line.startswith('#')]

        print(f"Found {len(deps)} dependencies in requirements.txt")
        print()

        valid_deps = 0
        invalid_deps = []

        for dep in deps:
            try:
                pkg_resources.Requirement.parse(dep)
                print(f"✅ Valid: {dep}")
                valid_deps += 1
            except Exception as e:
                print(f"❌ Invalid: {dep} - {e}")
                invalid_deps.append(dep)

        print()
        print(f"Results: {valid_deps}/{len(deps)} dependencies are valid")

        if invalid_deps:
            print(f"❌ {len(invalid_deps)} invalid dependencies found:")
            for dep in invalid_deps:
                print(f"   - {dep}")
            return False
        else:
            print("✅ All dependencies are properly formatted!")
            return True

    except FileNotFoundError:
        print("❌ requirements.txt file not found")
        return False
    except Exception as e:
        print(f"❌ Error reading requirements.txt: {e}")
        return False

if __name__ == "__main__":
    success = validate_dependencies()
    exit(0 if success else 1)