#!/bin/bash
# Ultra Pinnacle Studio Unified Orchestrator
# Starts all services for the complete offline fashion design & AI suite

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LOG_FILE="$PROJECT_ROOT/logs/orchestrator.log"

# Device detection
detect_device() {
    if [[ "$OSTYPE" == "linux-android" ]]; then
        echo "android"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        echo "macos"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        echo "linux"
    else
        echo "unknown"
    fi
}

DEVICE_TYPE=$(detect_device)

log() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')] $1${NC}" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[ERROR] $1${NC}" | tee -a "$LOG_FILE"
}

warning() {
    echo -e "${YELLOW}[WARNING] $1${NC}" | tee -a "$LOG_FILE"
}

info() {
    echo -e "${BLUE}[INFO] $1${NC}" | tee -a "$LOG_FILE"
}

# Check if port is available
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null ; then
        return 1
    else
        return 0
    fi
}

# Wait for service to be ready
wait_for_service() {
    local url=$1
    local timeout=${2:-30}
    local count=0

    info "Waiting for $url to be ready..."
    while ! curl -s "$url" >/dev/null 2>&1; do
        sleep 1
        count=$((count + 1))
        if [ $count -ge $timeout ]; then
            warning "Timeout waiting for $url"
            return 1
        fi
    done
    log "$url is ready!"
    return 0
}

# Start backend API
start_backend() {
    log "Starting Ultra Pinnacle Backend API..."

    cd "$PROJECT_ROOT/api_gateway"

    # Check if virtual environment exists
    if [ ! -d "venv" ]; then
        log "Creating Python virtual environment..."
        python3 -m venv venv
    fi

    # Activate virtual environment
    source venv/bin/activate

    # Install/update requirements
    if [ ! -f ".installed" ] || [ requirements.txt -nt .installed ]; then
        log "Installing Python requirements..."
        pip install -r requirements.txt
        touch .installed
    fi

    # Start FastAPI server
    if check_port 8000; then
        log "Starting FastAPI server on port 8000..."
        nohup uvicorn main:app --host 0.0.0.0 --port 8000 --reload > "$PROJECT_ROOT/logs/backend.log" 2>&1 &
        echo $! > "$PROJECT_ROOT/logs/backend.pid"
        wait_for_service "http://localhost:8000/health"
    else
        warning "Port 8000 already in use, skipping backend start"
    fi
}

# Start frontend
start_frontend() {
    log "Starting Ultra Pinnacle Frontend..."

    cd "$PROJECT_ROOT/web_ui"

    # Check if node_modules exists
    if [ ! -d "node_modules" ]; then
        log "Installing Node.js dependencies..."
        npm install
    fi

    # Start development server
    if check_port 3000; then
        log "Starting React development server on port 3000..."
        nohup npm start > "$PROJECT_ROOT/logs/frontend.log" 2>&1 &
        echo $! > "$PROJECT_ROOT/logs/frontend.pid"
        wait_for_service "http://localhost:3000"
    else
        warning "Port 3000 already in use, skipping frontend start"
    fi
}

# Start AI services
start_ai_services() {
    log "Checking for AI model runtimes..."

    # Start Stable Diffusion if available
    if [ -d "$PROJECT_ROOT/ai_runtimes/sd_automatic" ] && [ -f "$PROJECT_ROOT/ai_runtimes/models/sd/model.ckpt" ]; then
        if check_port 7860; then
            log "Starting Stable Diffusion WebUI..."
            cd "$PROJECT_ROOT/ai_runtimes/sd_automatic"
            nohup ./start_auto1111.sh > "$PROJECT_ROOT/logs/sd.log" 2>&1 &
            echo $! > "$PROJECT_ROOT/logs/sd.pid"
        fi
    else
        info "Stable Diffusion models not found, skipping SD startup"
    fi

    # Start Llama.cpp if available
    if [ -d "$PROJECT_ROOT/ai_runtimes/llama_service" ]; then
        if find "$PROJECT_ROOT/ai_runtimes/models" -name "*.gguf" -o -name "*.bin" | grep -q .; then
            if check_port 8080; then
                log "Starting Llama.cpp server..."
                cd "$PROJECT_ROOT/ai_runtimes/llama_service"
                nohup ./start_llama_service.sh > "$PROJECT_ROOT/logs/llama.log" 2>&1 &
                echo $! > "$PROJECT_ROOT/logs/llama.pid"
            fi
        else
            info "LLM models not found, skipping Llama startup"
        fi
    fi
}

# Start WooCommerce (if configured)
start_woocommerce() {
    if [ -f "$PROJECT_ROOT/config.json" ]; then
        if grep -q '"woocommerce"' "$PROJECT_ROOT/config.json" && grep -q '"api_url"' "$PROJECT_ROOT/config.json"; then
            log "WooCommerce integration configured"
            info "WooCommerce will be accessed via API when needed"
        fi
    fi
}

# Device-specific optimizations
device_optimizations() {
    case $DEVICE_TYPE in
        "android")
            log "Applying Android/Termux optimizations..."
            # Reduce memory usage for low-power devices
            export PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:512
            export CUDA_VISIBLE_DEVICES=""
            ;;
        "macos")
            log "Running on macOS"
            # macOS specific settings
            ;;
        "linux")
            log "Running on Linux"
            # Linux specific settings
            ;;
        *)
            warning "Unknown device type: $DEVICE_TYPE"
            ;;
    esac
}

# Cleanup function
cleanup() {
    log "Cleaning up processes..."
    for pidfile in "$PROJECT_ROOT/logs"/*.pid; do
        if [ -f "$pidfile" ]; then
            pid=$(cat "$pidfile")
            if kill -0 "$pid" 2>/dev/null; then
                kill "$pid"
                log "Killed process $pid"
            fi
            rm -f "$pidfile"
        fi
    done
}

# Main startup sequence
main() {
    log "=== Ultra Pinnacle Studio Orchestrator ==="
    log "Device type: $DEVICE_TYPE"
    log "Project root: $PROJECT_ROOT"

    # Create log directory
    mkdir -p "$PROJECT_ROOT/logs"

    # Set up cleanup on exit
    trap cleanup EXIT

    # Apply device optimizations
    device_optimizations

    # Start services in order
    start_backend
    start_frontend
    start_ai_services
    start_woocommerce

    log "=== All services started successfully! ==="
    log "🌐 Frontend: http://localhost:3000"
    log "🔧 Backend API: http://localhost:8000"
    log "📊 API Docs: http://localhost:8000/docs"
    log "🎨 Health Check: http://localhost:8000/health"

    if [ -f "$PROJECT_ROOT/logs/sd.pid" ]; then
        log "🖼️  Stable Diffusion: http://localhost:7860"
    fi

    if [ -f "$PROJECT_ROOT/logs/llama.pid" ]; then
        log "🤖 LLM API: http://localhost:8080"
    fi

    log "Press Ctrl+C to stop all services"

    # Wait for interrupt
    wait
}

# Handle command line arguments
case "${1:-start}" in
    "start")
        main
        ;;
    "stop")
        cleanup
        log "All services stopped"
        ;;
    "restart")
        cleanup
        sleep 2
        main
        ;;
    "status")
        echo "Ultra Pinnacle Studio Status:"
        echo "============================"
        for pidfile in "$PROJECT_ROOT/logs"/*.pid; do
            if [ -f "$pidfile" ]; then
                service=$(basename "$pidfile" .pid)
                pid=$(cat "$pidfile")
                if kill -0 "$pid" 2>/dev/null; then
                    echo "✅ $service: Running (PID: $pid)"
                else
                    echo "❌ $service: Dead (PID: $pid)"
                fi
            fi
        done
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status}"
        exit 1
        ;;
esac
# Start auto-healing service
start_auto_healer() {
    log "Starting Auto-Healing Service..."

    if check_port 8001; then
        log "Starting auto-healer on port 8001..."
        nohup python scripts/auto_healer.py > "$PROJECT_ROOT/logs/auto_healer.log" 2>&1 &
        echo $! > "$PROJECT_ROOT/logs/auto_healer.pid"
        log "Auto-healing service started"
    else
        warning "Port 8001 already in use, skipping auto-healer start"
    fi
}

start_auto_healer

start_auto_upgrader() {
    log "Starting Auto-Upgrade Service..."

    if check_port 8002; then
        log "Starting auto-upgrader on port 8002..."
        nohup python scripts/auto_upgrader.py > "$PROJECT_ROOT/logs/auto_upgrader.log" 2>&1 &
        echo $! > "$PROJECT_ROOT/logs/auto_upgrader.pid"
        log "Auto-upgrade service started"
    else
        warning "Port 8002 already in use, skipping auto-upgrader start"
    fi
}

start_auto_upgrader
