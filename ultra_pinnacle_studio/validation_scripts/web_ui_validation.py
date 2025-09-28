#!/usr/bin/env python3
"""
Web UI Validation Script for Ultra Pinnacle AI Studio
Validates the HTML structure and components of the web interface
"""

import os

def validate_web_ui():
    """Validate web UI HTML structure"""
    print("🌐 WEB UI VALIDATION")
    print("=" * 50)

    web_ui_path = '../web_ui/index.html'

    if not os.path.exists(web_ui_path):
        print("❌ Web UI file not found at web_ui/index.html")
        return False

    try:
        with open(web_ui_path, 'r', encoding='utf-8') as f:
            content = f.read()

        print(f"Web UI file size: {len(content)} characters")
        print()

        # Define validation checks
        checks = [
            ('HTML5 doctype', '<!DOCTYPE html>' in content),
            ('HTML opening tag', '<html' in content and 'lang=' in content),
            ('HTML closing tag', '</html>' in content),
            ('Head section', '<head>' in content and '</head>' in content),
            ('Body section', '<body>' in content and '</body>' in content),
            ('Title tag', '<title>' in content and '</title>' in content),
            ('Meta charset', '<meta charset=' in content),
            ('Meta viewport', '<meta name="viewport"' in content),
            ('Script tags', '<script>' in content and '</script>' in content),
            ('CSS styling', '<style>' in content or '<link' in content),
            ('JavaScript functions', 'function' in content),
            ('API calls', 'fetch(' in content),
            ('Form elements', '<input' in content or '<textarea' in content),
            ('Button elements', '<button' in content),
        ]

        passed_checks = 0
        total_checks = len(checks)

        for check_name, is_valid in checks:
            status = "✅" if is_valid else "❌"
            print(f"{status} {check_name}")
            if is_valid:
                passed_checks += 1

        print()
        print(f"Results: {passed_checks}/{total_checks} checks passed")

        # Extract and display title if present
        if '<title>' in content:
            title_start = content.find('<title>') + 7
            title_end = content.find('</title>', title_start)
            if title_end > title_start:
                title = content[title_start:title_end].strip()
                print(f"Page title: '{title}'")

        # Check for major sections
        sections = ['Authentication', 'Chat', 'Enhance Prompt', 'Encyclopedia', 'Code Analysis', 'File Upload']
        found_sections = sum(1 for section in sections if section.lower() in content.lower())
        print(f"UI sections found: {found_sections}/{len(sections)}")

        success = passed_checks >= total_checks * 0.8  # 80% success rate
        if success:
            print("✅ Web UI validation passed!")
        else:
            print("❌ Web UI validation failed - too many missing elements")

        return success

    except Exception as e:
        print(f"❌ Error reading web UI file: {e}")
        return False

if __name__ == "__main__":
    success = validate_web_ui()
    exit(0 if success else 1)