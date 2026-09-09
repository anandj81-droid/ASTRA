#!/bin/bash

# ===================================================
# ASTRA PLATFORM - Environment Startup Script
# ===================================================
# This script starts all three services in separate terminals
# Usage: ./start_environments.sh
# ===================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Configuration
PROJECT_DIR="$HOME/fx-tool-project"
VENV_DIR="$PROJECT_DIR/venv"
LOG_DIR="$PROJECT_DIR/logs"
PID_DIR="$PROJECT_DIR/pids"
LOG_RETENTION_DAYS=7  # Keep logs for 7 days

# Create directories if they don't exist
mkdir -p "$LOG_DIR" 2>/dev/null
mkdir -p "$PID_DIR" 2>/dev/null

print_message() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] ✅ $1${NC}"
}

print_error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] ⚠️ $1${NC}"
}

print_header() {
    echo -e "${CYAN}$1${NC}"
}

# ===================================================
# LOG MANAGEMENT FUNCTIONS
# ===================================================

rotate_logs() {
    """Rotate old logs and keep only recent ones"""
    print_message "Rotating old logs (keeping last ${LOG_RETENTION_DAYS} days)..."
    
    if [ -d "$LOG_DIR" ]; then
        # Find and remove logs older than LOG_RETENTION_DAYS
        find "$LOG_DIR" -name "*.log" -type f -mtime +${LOG_RETENTION_DAYS} -delete 2>/dev/null
        find "$LOG_DIR" -name "*.log.*" -type f -mtime +${LOG_RETENTION_DAYS} -delete 2>/dev/null
        print_success "Old logs cleaned up"
    fi
}

clear_logs() {
    """Clear all log files"""
    print_message "Clearing all logs..."
    
    if [ -d "$LOG_DIR" ]; then
        # Archive logs before clearing (optional)
        if [ "$(ls -A $LOG_DIR 2>/dev/null)" ]; then
            local archive_dir="$LOG_DIR/archive_$(date +'%Y%m%d_%H%M%S')"
            mkdir -p "$archive_dir"
            mv "$LOG_DIR"/*.log "$archive_dir/" 2>/dev/null
            print_success "Logs archived to: $archive_dir"
        else
            print_message "No logs to clear"
        fi
    else
        mkdir -p "$LOG_DIR"
    fi
    
    # Create empty log files
    touch "$LOG_DIR/fastapi.log"
    touch "$LOG_DIR/celery_worker.log"
    touch "$LOG_DIR/celery_beat.log"
    print_success "Log files cleared and recreated"
}

view_logs() {
    """View logs with options"""
    local service=$1
    local lines=${2:-50}
    
    case $service in
        fastapi)
            tail -f "$LOG_DIR/fastapi.log"
            ;;
        worker)
            tail -f "$LOG_DIR/celery_worker.log"
            ;;
        beat)
            tail -f "$LOG_DIR/celery_beat.log"
            ;;
        all)
            tail -f "$LOG_DIR/fastapi.log" "$LOG_DIR/celery_worker.log" "$LOG_DIR/celery_beat.log"
            ;;
        errors)
            echo "=== Recent Errors ==="
            grep -i "error\|fail\|exception\|critical" "$LOG_DIR"/*.log 2>/dev/null | tail -$lines
            ;;
        stats)
            echo "=== Log Statistics ==="
            for log in "$LOG_DIR"/*.log; do
                if [ -f "$log" ]; then
                    local name=$(basename "$log")
                    local size=$(du -h "$log" | cut -f1)
                    local lines_count=$(wc -l < "$log")
                    local errors=$(grep -i "error" "$log" 2>/dev/null | wc -l)
                    echo "  $name: $lines_count lines, $size, $errors errors"
                fi
            done
            ;;
        *)
            echo "Usage: view_logs [fastapi|worker|beat|all|errors|stats] [lines]"
            ;;
    esac
}

# ===================================================
# SERVICE MANAGEMENT FUNCTIONS
# ===================================================

is_running() {
    local pid_file="$PID_DIR/$1.pid"
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file" 2>/dev/null)
        if [ -n "$pid" ] && ps -p "$pid" > /dev/null 2>&1; then
            return 0
        fi
    fi
    return 1
}

kill_process() {
    local pid_file="$PID_DIR/$1.pid"
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file" 2>/dev/null)
        if [ -n "$pid" ] && ps -p "$pid" > /dev/null 2>&1; then
            print_warning "Stopping $1 (PID: $pid)..."
            kill -TERM "$pid" 2>/dev/null || kill -9 "$pid" 2>/dev/null
            sleep 1
            rm -f "$pid_file"
            print_success "$1 stopped"
        else
            rm -f "$pid_file"
        fi
    fi
}

start_fastapi() {
    print_message "Starting FastAPI server..."
    
    if is_running "fastapi"; then
        print_warning "FastAPI is already running"
        return 0
    fi
    
    cd "$PROJECT_DIR"
    source "$VENV_DIR/bin/activate"
    
    # Start FastAPI in background with nohup
    nohup uvicorn main:app --host 0.0.0.0 --port 8000 --reload > "$LOG_DIR/fastapi.log" 2>&1 &
    local pid=$!
    echo $pid > "$PID_DIR/fastapi.pid"
    
    sleep 3
    if is_running "fastapi"; then
        print_success "FastAPI started successfully (PID: $pid)"
        print_message "   📍 http://localhost:8000"
        print_message "   📍 http://localhost:8000/docs"
        print_message "   📍 http://localhost:8000/login"
    else
        print_error "FastAPI failed to start. Check logs: $LOG_DIR/fastapi.log"
        return 1
    fi
}

start_celery_worker() {
    print_message "Starting Celery Worker..."
    
    if is_running "celery_worker"; then
        print_warning "Celery Worker is already running"
        return 0
    fi
    
    cd "$PROJECT_DIR"
    source "$VENV_DIR/bin/activate"
    
    # Start Celery Worker in background
    nohup celery -A celery_app worker --loglevel=info --concurrency=2 > "$LOG_DIR/celery_worker.log" 2>&1 &
    local pid=$!
    echo $pid > "$PID_DIR/celery_worker.pid"
    
    sleep 3
    if is_running "celery_worker"; then
        print_success "Celery Worker started successfully (PID: $pid)"
    else
        print_error "Celery Worker failed to start. Check logs: $LOG_DIR/celery_worker.log"
        return 1
    fi
}

start_celery_beat() {
    print_message "Starting Celery Beat scheduler..."
    
    if is_running "celery_beat"; then
        print_warning "Celery Beat is already running"
        return 0
    fi
    
    cd "$PROJECT_DIR"
    source "$VENV_DIR/bin/activate"
    
    # Start Celery Beat in background
    nohup celery -A celery_app beat --loglevel=info > "$LOG_DIR/celery_beat.log" 2>&1 &
    local pid=$!
    echo $pid > "$PID_DIR/celery_beat.pid"
    
    sleep 3
    if is_running "celery_beat"; then
        print_success "Celery Beat started successfully (PID: $pid)"
    else
        print_error "Celery Beat failed to start. Check logs: $LOG_DIR/celery_beat.log"
        return 1
    fi
}

stop_all() {
    print_message "Stopping all services..."
    kill_process "fastapi"
    kill_process "celery_worker"
    kill_process "celery_beat"
    print_success "All services stopped"
}

show_status() {
    echo ""
    print_header "=== Service Status ==="
    echo ""
    
    if is_running "fastapi"; then
        local pid=$(cat "$PID_DIR/fastapi.pid" 2>/dev/null)
        echo -e "  ${GREEN}✅ FastAPI: Running (PID: $pid)${NC}"
        echo -e "     📍 http://localhost:8000"
    else
        echo -e "  ${RED}❌ FastAPI: Stopped${NC}"
    fi
    
    if is_running "celery_worker"; then
        local pid=$(cat "$PID_DIR/celery_worker.pid" 2>/dev/null)
        echo -e "  ${GREEN}✅ Celery Worker: Running (PID: $pid)${NC}"
    else
        echo -e "  ${RED}❌ Celery Worker: Stopped${NC}"
    fi
    
    if is_running "celery_beat"; then
        local pid=$(cat "$PID_DIR/celery_beat.pid" 2>/dev/null)
        echo -e "  ${GREEN}✅ Celery Beat: Running (PID: $pid)${NC}"
    else
        echo -e "  ${RED}❌ Celery Beat: Stopped${NC}"
    fi
    echo ""
}

start_all() {
    # Clear logs before starting fresh
    clear_logs
    
    print_message "Starting all services..."
    echo ""
    start_fastapi || print_error "Failed to start FastAPI"
    echo ""
    start_celery_worker || print_error "Failed to start Celery Worker"
    echo ""
    start_celery_beat || print_error "Failed to start Celery Beat"
    echo ""
    show_status
    echo ""
    print_message "📊 Services started!"
    print_message "   📍 View logs: ./start_environments.sh logs"
    print_message "   🌐 Access dashboard: http://localhost:8000/login"
    echo ""
}

# ===================================================
# MAIN MENU
# ===================================================

show_menu() {
    echo ""
    print_header "╔════════════════════════════════════════════════════════════╗"
    print_header "║         🚀 ASTRA PLATFORM - Service Manager              ║"
    print_header "╚════════════════════════════════════════════════════════════╝"
    echo ""
    echo "  1. Start All Services (clears logs)"
    echo "  2. Stop All Services"
    echo "  3. Restart All Services (clears logs)"
    echo "  4. Show Service Status"
    echo ""
    echo "  📊 Log Management:"
    echo "  5. View Logs (Real-time)"
    echo "  6. View Logs with Line Numbers"
    echo "  7. Clear All Logs"
    echo "  8. Archive Logs"
    echo "  9. Show Log Statistics"
    echo " 10. Check for Errors in Logs"
    echo ""
    echo "  🔧 Advanced:"
    echo " 11. Start Individual Service"
    echo " 12. Rotate Old Logs (keep 7 days)"
    echo ""
    echo "  0. Exit"
    echo ""
    read -p "Select an option: " choice
    
    case $choice in
        1) start_all ;;
        2) stop_all ;;
        3) stop_all; sleep 2; start_all ;;
        4) show_status ;;
        5) 
            echo ""
            echo "Select log to view:"
            echo " 1. FastAPI"
            echo " 2. Celery Worker"
            echo " 3. Celery Beat"
            echo " 4. All (combined)"
            read -p "Select [1-4]: " log_choice
            case $log_choice in
                1) view_logs fastapi ;;
                2) view_logs worker ;;
                3) view_logs beat ;;
                4) view_logs all ;;
                *) print_error "Invalid option" ;;
            esac
            ;;
        6)
            echo ""
            echo "Select log with line numbers:"
            echo " 1. FastAPI"
            echo " 2. Celery Worker"
            echo " 3. Celery Beat"
            read -p "Select [1-3]: " log_choice
            case $log_choice in
                1) cat -n "$LOG_DIR/fastapi.log" | tail -50 ;;
                2) cat -n "$LOG_DIR/celery_worker.log" | tail -50 ;;
                3) cat -n "$LOG_DIR/celery_beat.log" | tail -50 ;;
                *) print_error "Invalid option" ;;
            esac
            ;;
        7) clear_logs ;;
        8)
            print_message "Archiving logs..."
            local archive_name="logs_archive_$(date +'%Y%m%d_%H%M%S').tar.gz"
            if [ -d "$LOG_DIR" ] && [ "$(ls -A $LOG_DIR 2>/dev/null)" ]; then
                tar -czf "$PROJECT_DIR/$archive_name" -C "$PROJECT_DIR" logs/
                rm -f "$LOG_DIR"/*.log
                print_success "Logs archived to: $archive_name"
                print_success "Log files cleared"
            else
                print_warning "No logs to archive"
            fi
            ;;
        9) view_logs stats ;;
        10) view_logs errors 50 ;;
        11)
            echo ""
            echo "Start Individual Service:"
            echo " 1. FastAPI"
            echo " 2. Celery Worker"
            echo " 3. Celery Beat"
            read -p "Select [1-3]: " service_choice
            case $service_choice in
                1) start_fastapi ;;
                2) start_celery_worker ;;
                3) start_celery_beat ;;
                *) print_error "Invalid option" ;;
            esac
            ;;
        12) rotate_logs ;;
        0) 
            echo "Goodbye! 👋"
            exit 0
            ;;
        *)
            print_error "Invalid option"
            ;;
    esac
}

# ===================================================
# INITIALIZATION AND MAIN
# ===================================================

check_venv() {
    if [ ! -d "$VENV_DIR" ]; then
        print_error "Virtual environment not found at $VENV_DIR"
        print_message "Please create it first: python -m venv venv"
        exit 1
    fi
}

check_project() {
    if [ ! -d "$PROJECT_DIR" ]; then
        print_error "Project directory not found at $PROJECT_DIR"
        print_message "Please update PROJECT_DIR in the script"
        exit 1
    fi
}

# Main execution
main() {
    check_project
    check_venv
    
    # Rotate old logs on startup
    rotate_logs
    
    case "$1" in
        start)
            start_all
            ;;
        stop)
            stop_all
            ;;
        restart)
            stop_all
            sleep 2
            start_all
            ;;
        status)
            show_status
            ;;
        logs)
            shift
            view_logs "$@"
            ;;
        clear-logs)
            clear_logs
            ;;
        *)
            while true; do
                show_menu
                echo ""
                read -p "Press Enter to continue or 'q' to quit: " continue_choice
                if [[ "$continue_choice" == "q" || "$continue_choice" == "Q" ]]; then
                    echo "Goodbye! 👋"
                    exit 0
                fi
            done
            ;;
    esac
}

# Run main function
main "$@"