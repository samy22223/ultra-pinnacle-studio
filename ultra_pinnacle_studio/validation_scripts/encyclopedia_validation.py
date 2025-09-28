#!/usr/bin/env python3
"""
Encyclopedia Validation Script for Ultra Pinnacle AI Studio
Validates the structure and content of encyclopedia markdown files
"""

import os

def validate_encyclopedia():
    """Validate encyclopedia files and structure"""
    print("📚 ENCYCLOPEDIA VALIDATION")
    print("=" * 50)

    encyclopedia_dir = '../encyclopedia'

    if not os.path.exists(encyclopedia_dir):
        print("❌ Encyclopedia directory not found")
        return False

    try:
        files = [f for f in os.listdir(encyclopedia_dir) if f.endswith('.md')]
        print(f"Found {len(files)} encyclopedia files")
        print()

        if len(files) < 5:
            print(f"❌ Insufficient encyclopedia files: {len(files)} (expected >= 5)")
            return False

        total_lines = 0
        total_headers = 0
        valid_files = 0

        for file in files:
            file_path = os.path.join(encyclopedia_dir, file)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                lines = content.split('\n')
                headers = [line for line in lines if line.startswith('#')]
                non_empty_lines = [line for line in lines if line.strip()]

                # Validate file structure
                has_title = content.startswith('# ')
                has_content = len(non_empty_lines) > 1
                has_headers = len(headers) > 0

                file_valid = has_title and has_content and has_headers

                if file_valid:
                    print(f"✅ {file}: {len(lines)} lines, {len(headers)} headers")
                    valid_files += 1
                else:
                    print(f"❌ {file}: Missing required elements")
                    if not has_title:
                        print("   └─ Missing title header (# )")
                    if not has_content:
                        print("   └─ No content found")
                    if not has_headers:
                        print("   └─ No headers found")

                total_lines += len(lines)
                total_headers += len(headers)

                # Extract title for reporting
                if has_title:
                    title_line = next((line for line in lines if line.startswith('# ')), '')
                    title = title_line[2:].strip()
                    print(f"   └─ Title: {title}")

            except Exception as e:
                print(f"❌ Error reading {file}: {e}")

        print()
        print("Summary:")
        print(f"  Total files: {len(files)}")
        print(f"  Valid files: {valid_files}")
        print(f"  Total lines: {total_lines}")
        print(f"  Total headers: {total_headers}")

        # Expected domains check
        expected_domains = [
            'math_sequences', 'ai_algorithms', 'dev_tools',
            'fashion_design', 'cross_domain', 'software_architecture',
            'machine_learning', 'blockchain_cryptography'
        ]

        found_domains = [f.replace('.md', '') for f in files]
        missing_domains = [d for d in expected_domains if d not in found_domains]

        if missing_domains:
            print(f"⚠️  Missing expected domains: {missing_domains}")
        else:
            print("✅ All expected knowledge domains present")

        success = valid_files >= len(files) * 0.8  # 80% of files must be valid
        if success:
            print("✅ Encyclopedia validation passed!")
        else:
            print("❌ Encyclopedia validation failed - too many invalid files")

        return success

    except Exception as e:
        print(f"❌ Error during encyclopedia validation: {e}")
        return False

if __name__ == "__main__":
    success = validate_encyclopedia()
    exit(0 if success else 1)