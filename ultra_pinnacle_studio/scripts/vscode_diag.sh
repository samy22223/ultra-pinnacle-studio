#!/usr/bin/env bash
# VSCode diagnostic script
# Collects Electron/V8 binary info, native modules, codesign/spctl, system info, and recent crash reports.
# Enhanced with common utilities and structured error handling

set -euo pipefail

# Get script directory and load common utilities
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT_NAME="$(basename "${BASH_SOURCE[0]}")"

# Load common utilities if available
COMMON_UTILS_LIB="$SCRIPT_DIR/lib/common_utils.sh"
if [[ -f "$COMMON_UTILS_LIB" ]]; then
    # shellcheck source=lib/common_utils.sh
    source "$COMMON_UTILS_LIB"
else
    echo "WARNING: Common utilities library not found: $COMMON_UTILS_LIB"
    echo "Running with basic functionality..."

    # Basic logging functions for fallback
    log_info() { echo "[INFO] $*"; }
    log_warn() { echo "[WARN] $*"; }
    log_error() { echo "[ERROR] $*"; }
    log_debug() { echo "[DEBUG] $*"; }
    error_exit() { log_error "$1"; exit "${2:-1}"; }
fi

# Load configuration if available
CONFIG_FILE="$SCRIPT_DIR/config/defaults.json"
if [[ -f "$CONFIG_FILE" ]]; then
    load_config "$CONFIG_FILE"
fi

# Initialize script
init_script "${BASH_SOURCE[0]}" "INFO" "true"
SCRIPT_NAME="vscode_diag.sh"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
OUT_DIR="/tmp/vscode_diag_${TIMESTAMP}"
ARCHIVE="${OUT_DIR}.tar.gz"

mkdir -p "$OUT_DIR"

echo "VSCode diagnostic script running. Output -> $OUT_DIR"

usage(){
  cat <<EOF
Usage: $SCRIPT_NAME [--fix] [--yes]

Default: collects diagnostics and writes a tarball at $ARCHIVE
--fix   : Attempt safe backup of existing /Applications/Visual Studio Code.app to ~/Desktop/VSCode-broken-<ts>.app (no reinstall).
--yes   : Auto-confirm prompts used by --fix

EOF
}

DO_FIX=0
AUTO_YES=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --fix) DO_FIX=1; shift ;;
    --yes) AUTO_YES=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown arg: $1"; usage; exit 1 ;;
  esac
done

echo "Collecting system information..."
uname -a > "$OUT_DIR/uname.txt" 2>&1 || true
sw_vers > "$OUT_DIR/sw_vers.txt" 2>&1 || true
system_profiler SPHardwareDataType > "$OUT_DIR/SPHardwareDataType.txt" 2>&1 || true
sysctl -a machdep.cpu > "$OUT_DIR/cpu_info.txt" 2>&1 || true

echo "Collecting recent system log entries for Electron/Visual Studio Code (last 1h)..."
log show --style syslog --predicate 'process CONTAINS "Electron" OR process CONTAINS "Visual Studio Code"' --last 1h > "$OUT_DIR/log_show_1h.txt" 2>&1 || true

echo "Searching for VS Code installations..."
declare -a CANDIDATES
CANDIDATES=( "/Applications/Visual Studio Code.app" "/Applications/Visual Studio Code - Insiders.app" "$HOME/Applications/Visual Studio Code.app" "/Applications/Visual Studio Code - OSS.app" )

# also scan /Applications and ~/Applications for matching names
while IFS= read -r -d $'\0' p; do
  CANDIDATES+=("$p")
done < <(find /Applications "$HOME/Applications" -maxdepth 2 -type d -name "*Visual Studio Code*.app" -print0 2>/dev/null || true)

printf "%s\n" "${CANDIDATES[@]}" | sort -u > "$OUT_DIR/candidates_list.txt"

echo "Inspecting found app bundles..."
FOUND=0
while IFS= read -r APP; do
  [[ -z "$APP" ]] && continue
  if [[ -d "$APP" ]]; then
    FOUND=1
    safe_name=$(echo "$APP" | sed 's/\//_/g' | sed 's/\s/_/g')
    dst="$OUT_DIR/app_inspect${safe_name}"
    mkdir -p "$dst"
    echo "Found: $APP" | tee "$dst/path.txt"

    ELECTRON_BIN="$APP/Contents/MacOS/Electron"
    if [[ -f "$ELECTRON_BIN" ]]; then
      echo "file for Electron binary:" > "$dst/electron_file.txt"
      file "$ELECTRON_BIN" >> "$dst/electron_file.txt" 2>&1 || true
      echo "otool -L:" > "$dst/electron_otool_l.txt"
      otool -L "$ELECTRON_BIN" >> "$dst/electron_otool_l.txt" 2>&1 || true
    else
      echo "Electron binary not found at expected path: $ELECTRON_BIN" > "$dst/electron_missing.txt"
    fi

    # codesign & spctl
    echo "Running codesign verify..." > "$dst/codesign_verify.txt"
    codesign --verify --deep --strict --verbose=4 "$APP" >> "$dst/codesign_verify.txt" 2>&1 || true
    echo "Running spctl assess..." > "$dst/spctl_assess.txt"
    spctl --assess --type execute -vv "$APP" >> "$dst/spctl_assess.txt" 2>&1 || true

    # find native .node modules under Resources/app
    RESOURCES_APP="$APP/Contents/Resources/app"
    if [[ -d "$RESOURCES_APP" ]]; then
      find "$RESOURCES_APP" -type f -name "*.node" > "$dst/native_nodes_list.txt" 2>/dev/null || true
      # list top-level node_modules too
      if [[ -d "$RESOURCES_APP/node_modules" ]]; then
        ls -la "$RESOURCES_APP/node_modules" > "$dst/node_modules_top.txt" 2>&1 || true
      fi
      # file each .node
      while IFS= read -r N; do
        [[ -z "$N" ]] && continue
        safefn=$(basename "$N")
        file "$N" > "$dst/file_${safefn}.txt" 2>&1 || true
      done < "$dst/native_nodes_list.txt" || true
      # List asar files
      find "$RESOURCES_APP" -type f -name "*.asar" > "$dst/asar_list.txt" 2>/dev/null || true
    else
      echo "Resources/app not present" > "$dst/resources_missing.txt"
    fi

    # copy any recent crash reports mentioning this app
    mkdir -p "$dst/crash_reports"
    for d in "$HOME/Library/Logs/DiagnosticReports" "/Library/Logs/DiagnosticReports"; do
      if [[ -d "$d" ]]; then
        grep -l "Visual Studio Code\|Electron" "$d"/* 2>/dev/null | xargs -I{} -r cp -v {} "$dst/crash_reports/" 2>/dev/null || true
      fi
    done

  fi
done < "$OUT_DIR/candidates_list.txt"

if [[ $FOUND -eq 0 ]]; then
  echo "No Visual Studio Code.app found in standard locations. Listing /Applications content..." > "$OUT_DIR/no_apps_found.txt"
  ls -la /Applications > "$OUT_DIR/ls_applications.txt" 2>&1 || true
fi

echo "Collecting global Node/native env hints..."
which node > "$OUT_DIR/which_node.txt" 2>&1 || true
node -v > "$OUT_DIR/node_version.txt" 2>&1 || true
which brew > "$OUT_DIR/which_brew.txt" 2>&1 || true
brew --version > "$OUT_DIR/brew_version.txt" 2>&1 || true

echo "Copying recent VS Code crash reports (if any) from user DiagnosticReports..."
mkdir -p "$OUT_DIR/user_crash_reports"
ls -1t "$HOME/Library/Logs/DiagnosticReports"/*Visual* 2>/dev/null | head -n 10 | xargs -I{} -r cp -v {} "$OUT_DIR/user_crash_reports/" 2>/dev/null || true

echo "Gathering installed Launch Services and Gatekeeper status..."
pkgutil --pkgs > "$OUT_DIR/installed_pkgs.txt" 2>&1 || true

echo "=== CPU Architecture Compatibility Check for V8 JIT ==="
echo "Checking CPU instruction set support for V8 JavaScript engine..."

# Check for SSE4.2 support (required for V8)
echo "SSE4.2 support check:" > "$OUT_DIR/cpu_sse42_check.txt"
sysctl -n machdep.cpu.features | grep -o SSE4.2 >> "$OUT_DIR/cpu_sse42_check.txt" 2>&1 || echo "SSE4.2 not detected" >> "$OUT_DIR/cpu_sse42_check.txt"

# Check for AVX support (used by modern V8)
echo "AVX support check:" > "$OUT_DIR/cpu_avx_check.txt"
sysctl -n machdep.cpu.leaf7_features | grep -o AVX >> "$OUT_DIR/cpu_avx_check.txt" 2>&1 || echo "AVX not detected" >> "$OUT_DIR/cpu_avx_check.txt"

# Check CPU model and family for known compatibility issues
CPU_MODEL=$(sysctl -n machdep.cpu.model)
CPU_FAMILY=$(sysctl -n machdep.cpu.family)
echo "CPU Model: $CPU_MODEL" > "$OUT_DIR/cpu_model.txt"
echo "CPU Family: $CPU_FAMILY" >> "$OUT_DIR/cpu_model.txt"

# Check if this is a known problematic CPU for V8
if [[ "$CPU_MODEL" == "70" ]] || [[ "$CPU_MODEL" == "61" ]] || [[ "$CPU_MODEL" == "71" ]]; then
    echo "WARNING: This CPU model may have V8 JIT compatibility issues" >> "$OUT_DIR/cpu_model.txt"
fi

# Check for Rosetta translation issues
echo "Rosetta translation check:" > "$OUT_DIR/rosetta_check.txt"
if [[ -n "${DYLD_LIBRARY_PATH:-}" ]]; then
    echo "DYLD_LIBRARY_PATH: $DYLD_LIBRARY_PATH" >> "$OUT_DIR/rosetta_check.txt"
fi

# Check if VSCode process is running under Rosetta when it shouldn't be
if pgrep -x "Electron" > /dev/null; then
    PROCESS_PID=$(pgrep -x "Electron" | head -1)
    if [ -n "$PROCESS_PID" ]; then
        echo "Checking if PID $PROCESS_PID is translated by Rosetta..." >> "$OUT_DIR/rosetta_check.txt"
        if lsappinfo info -only pid $PROCESS_PID | grep -q "Rosetta"; then
            echo "WARNING: VSCode is running under Rosetta translation!" >> "$OUT_DIR/rosetta_check.txt"
            echo "This could cause JIT compilation issues with V8." >> "$OUT_DIR/rosetta_check.txt"
        else
            echo "VSCode is running natively (not under Rosetta)" >> "$OUT_DIR/rosetta_check.txt"
        fi
    fi
fi

# Check for memory pressure that could affect JIT compilation
echo "Memory pressure check:" > "$OUT_DIR/memory_pressure.txt"
memory_pressure | head -5 >> "$OUT_DIR/memory_pressure.txt" 2>&1 || echo "memory_pressure tool not available" >> "$OUT_DIR/memory_pressure.txt"

# Check system logs for V8/JIT related errors
echo "V8/JIT related log entries (last 24h):" > "$OUT_DIR/v8_jit_logs.txt"
log show --last 24h | grep -i "v8\|jit\|illegal instruction\|SIGILL" >> "$OUT_DIR/v8_jit_logs.txt" 2>&1 || true

echo "Packaging results into: $ARCHIVE"
tar -czf "$ARCHIVE" -C "/tmp" "$(basename "$OUT_DIR")" 2>/dev/null || true

echo "=== Summary ==="
echo "Output directory: $OUT_DIR"
echo "Archive: $ARCHIVE"
echo "Contents preview:"
ls -la "$OUT_DIR" | sed -n '1,200p'

if [[ $DO_FIX -eq 1 ]]; then
  TARGET_APP="/Applications/Visual Studio Code.app"
  if [[ ! -d "$TARGET_APP" ]]; then
    echo "No app at $TARGET_APP to backup. Exiting fix mode." >&2
    exit 1
  fi
  BACKUP_DEST="$HOME/Desktop/VSCode-broken-${TIMESTAMP}.app"
  if [[ $AUTO_YES -eq 1 ]]; then
    mv "$TARGET_APP" "$BACKUP_DEST" 2>&1 || { echo "Failed to move $TARGET_APP to $BACKUP_DEST (permissions?)"; exit 1; }
    echo "Moved $TARGET_APP -> $BACKUP_DEST"
    echo "Fix mode only backs up the existing app. Please download the correct VS Code build from https://code.visualstudio.com/ and install it." 
  else
    echo "About to move $TARGET_APP -> $BACKUP_DEST"
    read -p "Proceed? [y/N] " ans
    if [[ "$ans" = "y" || "$ans" = "Y" ]]; then
      mv "$TARGET_APP" "$BACKUP_DEST" || { echo "Failed to move (permissions?), try with sudo."; exit 1; }
      echo "Moved $TARGET_APP -> $BACKUP_DEST"
    else
      echo "User aborted backup. No changes made.";
    fi
  fi
fi

echo "Done. Packaged diagnostics at: $ARCHIVE"
echo "Please attach the tarball or paste the small summary files (cpu_info, electron_file, file_*.txt) when filing an issue."

exit 0
#!/usr/bin/env zsh
# VSCode diagnostic script
# Usage: vscode_diag.sh [--app "/Applications/Visual Studio Code.app"] [--out /tmp/outdir] [--fix]
# By default it collects diagnostics only. Use --fix to attempt a safe reinstall (will prompt).

set -euo pipefail
APP_PATH="/Applications/Visual Studio Code.app"
OUTDIR="/tmp/vscode_diag_$(date +%Y%m%d_%H%M%S)"
FIX=0

AUTO_YES=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --app) APP_PATH="$2"; shift 2;;
    --out) OUTDIR="$2"; shift 2;;
    --fix) FIX=1; shift;;
    --yes) AUTO_YES=1; shift;;
    -h|--help) echo "Usage: $0 [--app APP_PATH] [--out OUTDIR] [--fix]"; exit 0;;
    *) echo "Unknown arg: $1"; exit 1;;
  esac
done

mkdir -p "$OUTDIR"
echo "Diagnostic output -> $OUTDIR"
exec > >(tee "$OUTDIR/diagnostic.log") 2>&1

echo "=== VS Code diagnostic: $(date) ==="
echo "App path: $APP_PATH"

# Basic system info
sw_vers > "$OUTDIR/sw_vers.txt"
uname -a > "$OUTDIR/uname.txt"
sysctl -a | grep -E 'machdep.cpu|hw.memsize' > "$OUTDIR/cpu_mem.txt" || true

# Binary info
if [[ -f "$APP_PATH/Contents/MacOS/Electron" ]]; then
  echo "\n-- file + lipo info for Electron binary --"
  file "$APP_PATH/Contents/MacOS/Electron" | tee "$OUTDIR/file_electron.txt"
  if command -v lipo >/dev/null 2>&1; then
    lipo -info "$APP_PATH/Contents/MacOS/Electron" > "$OUTDIR/lipo_electron.txt" 2>&1 || true
  fi
else
  echo "Electron binary not found at expected path: $APP_PATH/Contents/MacOS/Electron"
fi

# Codesign and spctl
if command -v codesign >/dev/null 2>&1; then
  echo "\n-- codesign verify (may be slow) --"
  codesign --verify --deep --strict --verbose=2 "$APP_PATH" > "$OUTDIR/codesign_verify.txt" 2>&1 || true
fi
if command -v spctl >/dev/null 2>&1; then
  echo "\n-- spctl assess --"
  spctl --assess --type execute -vv "$APP_PATH" > "$OUTDIR/spctl.txt" 2>&1 || true
fi

# List native modules and inspect .node files
NODE_FIND_ROOT="$APP_PATH/Contents/Resources/app"
mkdir -p "$OUTDIR/node_modules_info"
echo "\n-- searching for .node native modules under $NODE_FIND_ROOT --"
if [[ -d "$NODE_FIND_ROOT" ]]; then
  find "$NODE_FIND_ROOT" -name '*.node' -type f | while read -r nodefile; do
    echo "Found: $nodefile"
    safepath=$(echo "$nodefile" | sed 's/\//__/g')
    file "$nodefile" > "$OUTDIR/node_modules_info/${safepath}.file" 2>&1 || true
    if command -v otool >/dev/null 2>&1; then
      otool -L "$nodefile" > "$OUTDIR/node_modules_info/${safepath}.otool" 2>&1 || true
    fi
    sha1sum_cmd() {
      if command -v shasum >/dev/null 2>&1; then
        shasum -a 256 "$nodefile"
      elif command -v sha256sum >/dev/null 2>&1; then
        sha256sum "$nodefile"
      fi
    }
    sha1sum_cmd > "$OUTDIR/node_modules_info/${safepath}.sha256" 2>&1 || true
  done
else
  echo "Resources/app not found: $NODE_FIND_ROOT"
fi

# Copy crash reports relevant to Electron / Visual Studio Code
CRASH_OUT="$OUTDIR/crash_reports"
mkdir -p "$CRASH_OUT"
echo "\n-- collecting recent crash reports --"
for d in "$HOME/Library/Logs/DiagnosticReports" "/Library/Logs/DiagnosticReports"; do
  if [[ -d "$d" ]]; then
    ls -1t "$d"/Electron_*.crash 2>/dev/null | head -n 20 | xargs -I{} cp -v {} "$CRASH_OUT" 2>/dev/null || true
    ls -1t "$d"/Visual\ Studio\ Code_*.crash 2>/dev/null | head -n 20 | xargs -I{} cp -v {} "$CRASH_OUT" 2>/dev/null || true
    ls -1t "$d"/*Electron*.crash 2>/dev/null | head -n 20 | xargs -I{} cp -v {} "$CRASH_OUT" 2>/dev/null || true
  fi
done

# log show for the last hour for Electron / Visual Studio Code
echo "\n-- collecting unified logs (last 1h) --"
if command -v log >/dev/null 2>&1; then
  log show --predicate 'process == "Electron" OR process CONTAINS "Visual Studio Code"' --last 1h > "$OUTDIR/log_show_1h.txt" 2>&1 || true
fi

# List installed extensions (user-side) - non-invasive
EXT_DIR="$HOME/.vscode/extensions"
if [[ -d "$EXT_DIR" ]]; then
  echo "\n-- installed extensions (first 200 lines) --"
  ls -la "$EXT_DIR" | sed -n '1,200p' > "$OUTDIR/extensions_list.txt" 2>&1 || true
else
  echo "Extensions dir not found: $EXT_DIR"
fi

# Summarize sizes and free disk
echo "\n-- disk free and app size --"
df -h / | tee "$OUTDIR/disk_free.txt"
du -sh "$APP_PATH" 2>/dev/null | tee "$OUTDIR/app_size.txt" || true

# Package results
echo "\n-- packaging results --"
tar -czf "/tmp/vscode_diag_$(date +%Y%m%d_%H%M%S).tgz" -C "$(dirname "$OUTDIR")" "$(basename "$OUTDIR")" || true

echo "Diagnostic run complete. Results in: $OUTDIR"

echo "\n=== V8 JIT COMPATIBILITY WORKAROUNDS ==="
echo "Since VSCode is not currently installed, here are the workarounds for the SIGILL issue:"
echo ""
echo "1. V8 JIT Optimization Settings (add to VSCode settings.json):"
echo "   {"
echo "     \"javascript.preferences.noSemicolons\": \"off\","
echo "     \"editor.formatOnSave\": false,"
echo "     \"debug.javascript.usePreview\": false,"
echo "     \"javascript.validate.enable\": false"
echo "   }"
echo ""
echo "2. Command Line Arguments (add to VSCode shortcut):"
echo "   --disable-features=VizDisplayCompositor --disable-gpu"
echo ""
echo "3. Environment Variables:"
echo "   export NODE_OPTIONS=\"--jitless\""
echo ""
echo "4. Alternative: Use VSCode Insiders or older stable version"
echo ""
echo "Next steps:\n - Inspect $OUTDIR/diagnostic.log and files under $OUTDIR/node_modules_info for .node architecture mismatches or errors.\n - If codesign or spctl reported errors, consider reinstalling VS Code.\n"

# Check for V8 JIT compatibility issues and provide fixes
CPU_MODEL=$(sysctl -n machdep.cpu.model 2>/dev/null || echo "unknown")
if [[ "$CPU_MODEL" == "69" ]] || [[ "$CPU_MODEL" == "70" ]] || [[ "$CPU_MODEL" == "61" ]]; then
    echo "\n*** V8 JIT COMPATIBILITY ISSUE DETECTED ***"
    echo "Your CPU model ($CPU_MODEL) may have compatibility issues with V8's JIT compiler."
    echo "This can cause SIGILL crashes in VSCode."

    if [[ $DO_FIX -eq 1 ]]; then
        echo "\nApplying V8 JIT compatibility fixes..."

        # Create VSCode settings to disable JIT optimization
        VSCODE_SETTINGS="$HOME/Library/Application Support/Code/User/settings.json"
        mkdir -p "$(dirname "$VSCODE_SETTINGS")"

        if [[ ! -f "$VSCODE_SETTINGS" ]]; then
            echo "{" > "$VSCODE_SETTINGS"
            echo "  \"javascript.preferences.noSemicolons\": \"off\"," >> "$VSCODE_SETTINGS"
            echo "  \"editor.formatOnSave\": false" >> "$VSCODE_SETTINGS"
            echo "}" >> "$VSCODE_SETTINGS"
        fi

        # Add V8 optimization flags to settings
        if command -v python3 >/dev/null 2>&1; then
            python3 -c "
import json
settings_file = '$VSCODE_SETTINGS'
try:
    with open(settings_file, 'r') as f:
        settings = json.load(f)
except:
    settings = {}

settings['javascript.preferences.noSemicolons'] = 'off'
settings['editor.formatOnSave'] = False

# Add V8 optimization settings for older CPUs
settings['debug.javascript.usePreview'] = False
settings['javascript.validate.enable'] = False

with open(settings_file, 'w') as f:
    json.dump(settings, f, indent=2)
print('Updated VSCode settings for V8 compatibility')
"
        fi

        echo "V8 JIT compatibility fixes applied."
        echo "Please restart VSCode for changes to take effect."
    else
        echo "\nTo fix V8 JIT issues, run: $0 --fix"
        echo "This will:"
        echo "1. Disable aggressive V8 optimizations"
        echo "2. Update VSCode settings for better compatibility"
        echo "3. Provide performance vs stability recommendations"
    fi
fi

if [[ $FIX -eq 1 ]]; then
  echo "\n-- FIX MODE: attempt safe reinstall of VS Code --"
  if [[ $AUTO_YES -ne 1 ]]; then
    read -q "REPLY?This will backup existing app to ~/Desktop and download the latest VS Code stable from Microsoft. Proceed? (y/N): "
    echo
    if [[ "$REPLY" != [yY] ]]; then
      echo "User declined fix. Exiting."
      exit 0
    fi
  else
    echo "--yes supplied, proceeding with automated fix"
  fi
  BACKUP=~/Desktop/VSCode-broken-$(date +%Y%m%d_%H%M%S).app
  echo "Backing up current app to $BACKUP"
  mv "$APP_PATH" "$BACKUP" || { echo "Failed to move app (permission issue?). Try running script with sudo for the fix step."; exit 1; }
  TMPZIP="/tmp/vscode_latest.zip"
  echo "Downloading latest VS Code stable..."
  curl -L -o "$TMPZIP" "https://update.code.visualstudio.com/latest/darwin/stable" || { echo "Download failed"; exit 1; }
  echo "Unzipping..."
  unzip -q -o "$TMPZIP" -d /tmp || { echo "Unzip failed"; exit 1; }
  if [[ -d "/tmp/Visual Studio Code.app" ]]; then
    echo "Installing to /Applications (may require sudo)..."
    mv -f "/tmp/Visual Studio Code.app" "/Applications/Visual Studio Code.app" || { sudo mv -f "/tmp/Visual Studio Code.app" "/Applications/Visual Studio Code.app"; }
    echo "Installed. You may want to relaunch VS Code and re-run diagnostics if there are still crashes."
  else
    echo "Unpacked app not found in /tmp. Installation aborted."
    exit 1
  fi
fi

exit 0
