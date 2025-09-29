#!/bin/bash

# VS Code GitLab Workflow Troubleshooting Script
# This script automates some troubleshooting steps for VS Code GitLab Workflow extension
# Manual steps are indicated with instructions

set -euo pipefail

echo "##########################################"
echo "# VS Code GitLab Workflow Troubleshooting #"
echo "##########################################"

# 1. Verify Extension Installation & Compatibility
echo ""
echo "1. Verify Extension Installation & Compatibility"
echo "-----------------------------------------------"
echo "Manual steps:"
echo "- In VS Code: Press Ctrl+Shift+X → search 'GitLab Workflow'"
echo "- Ensure installed & enabled"
echo "- Check version → update if outdated"
echo "- Help > About → confirm VS Code version (update if needed)"
echo ""

# Check if VS Code is installed
if command -v code >/dev/null 2>&1; then
    echo "✅ VS Code is installed"
    code --version
else
    echo "❌ VS Code not found in PATH. Please install VS Code."
fi

# 2. Restart Extension
echo ""
echo "2. Restart Extension"
echo "-----------------------------------------------"
echo "Manual steps:"
echo "- Extensions view → Right-click GitLab Workflow → Disable → Enable"
echo "- OR Ctrl+Shift+P → 'Developer: Reload Window'"
echo ""

# 3. Configure Network / Proxy Settings
echo ""
echo "3. Configure Network / Proxy Settings"
echo "-----------------------------------------------"
echo "Manual steps:"
echo "- Ctrl+Shift+P → 'Preferences: Open Settings (UI)'"
echo "- Search 'proxy':"
echo "  • If using proxy → set 'Http: Proxy' = http://proxy.company.com:8080"
echo "  • If no proxy   → leave empty, set 'Http: Proxy Support' = off"
echo "- Search 'gitlab':"
echo "  • Configure 'GitLab: Ca' / 'GitLab: Cert' only if using custom certs"
echo "  • Otherwise leave empty"
echo "Save and reload VS Code"
echo ""

# Check current proxy settings (if any)
echo "Current proxy environment variables:"
echo "HTTP_PROXY: ${HTTP_PROXY:-not set}"
echo "HTTPS_PROXY: ${HTTPS_PROXY:-not set}"
echo ""

# 4. Enable Logs & Debugging
echo ""
echo "4. Enable Logs & Debugging"
echo "-----------------------------------------------"
echo "Manual steps:"
echo "- In Settings: Set 'GitLab: Log Level' = trace"
echo "- Ctrl+Shift+P → 'Output: Show Output Channels' → Select 'GitLab Workflow'"
echo "- Reproduce issue (e.g., open workspace)"
echo "- Check logs for errors: network issues, stack traces, repo parsing"
echo ""

# 5. Test Repository Detection
echo ""
echo "5. Test Repository Detection"
echo "-----------------------------------------------"

# Check if we're in a git repository
if git rev-parse --git-dir >/dev/null 2>&1; then
    echo "✅ Git repository detected"
    echo "Repository status:"
    git status --short
    echo ""

    # Check for remote
    if git remote get-url origin >/dev/null 2>&1; then
        echo "✅ Remote 'origin' exists:"
        git remote get-url origin
        echo ""

        # Check if branch exists on remote
        current_branch=$(git branch --show-current)
        if git ls-remote --heads origin "$current_branch" >/dev/null 2>&1; then
            echo "✅ Branch '$current_branch' exists on remote"
        else
            echo "❌ Branch '$current_branch' not found on remote"
            echo "Try pushing the branch: git push -u origin $current_branch"
        fi
    else
        echo "❌ No remote 'origin' configured"
        echo "To add a GitLab remote:"
        echo "git remote add origin https://gitlab.com/your-username/your-repo.git"
        echo "git push -u origin main"
    fi

    # Check if repository is not empty
    if [ "$(git log --oneline | wc -l)" -gt 0 ]; then
        echo "✅ Repository has commits"
    else
        echo "❌ Repository has no commits"
        echo "Make an initial commit:"
        echo "git add ."
        echo "git commit -m 'Initial commit'"
    fi
else
    echo "❌ Not in a git repository"
    echo "Initialize git: git init"
    echo "Add files: git add ."
    echo "Commit: git commit -m 'Initial commit'"
fi

echo ""

# 6. If Issues Persist
echo ""
echo "6. If Issues Persist"
echo "-----------------------------------------------"
echo "- Disable other Git-related extensions temporarily"
echo "- Uninstall & reinstall GitLab Workflow extension"
echo "- If still broken, report issue:"
echo "  https://github.com/gitlab/gitlab-workflow"
echo "  Include:"
echo "  • VS Code version"
echo "  • Extension version"
echo "  • Logs from 'GitLab Workflow' output"
echo ""

echo "##########################################"
echo "# End of Troubleshooting Script          #"
echo "##########################################"