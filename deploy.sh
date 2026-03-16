#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/yhyyz/aos-sizing-tool.git"
INSTALL_DIR="/opt/app/aos/aos-sizing-tool"
SERVICE_NAME="aos-api"
SERVICE_PORT=9989
PYTHON_VERSION="3.12"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()  { echo -e "${GREEN}[INFO]${NC} $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }

check_root() {
    if [[ $EUID -ne 0 ]]; then
        error "Please run as root: sudo bash deploy.sh"
    fi
}

install_uv() {
    if command -v uv &>/dev/null; then
        info "uv already installed: $(uv --version)"
        return
    fi
    info "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
    if ! command -v uv &>/dev/null; then
        error "uv installation failed"
    fi
    info "uv installed: $(uv --version)"
}

install_node() {
    if command -v node &>/dev/null; then
        info "Node.js already installed: $(node -v)"
        return
    fi
    info "Installing Node.js 22 LTS..."
    if command -v dnf &>/dev/null; then
        curl -fsSL https://rpm.nodesource.com/setup_22.x | bash -
        dnf install -y nodejs
    elif command -v yum &>/dev/null; then
        curl -fsSL https://rpm.nodesource.com/setup_22.x | bash -
        yum install -y nodejs
    elif command -v apt-get &>/dev/null; then
        curl -fsSL https://deb.nodesource.com/setup_22.x | bash -
        apt-get install -y nodejs
    else
        error "Unsupported package manager. Install Node.js 18+ manually."
    fi
    info "Node.js installed: $(node -v)"
}

clone_repo() {
    if [[ -d "$INSTALL_DIR/.git" ]]; then
        info "Updating existing repo..."
        cd "$INSTALL_DIR"
        git fetch origin
        git reset --hard origin/main || git reset --hard origin/master
    else
        info "Cloning repo to $INSTALL_DIR..."
        mkdir -p "$(dirname "$INSTALL_DIR")"
        git clone "$REPO_URL" "$INSTALL_DIR"
        cd "$INSTALL_DIR"
    fi
    info "Code ready at $INSTALL_DIR"
}

setup_python() {
    info "Creating Python $PYTHON_VERSION venv..."
    cd "$INSTALL_DIR"
    uv venv -p "$PYTHON_VERSION" .venv
    info "Installing Python dependencies..."
    uv pip install -r requirements.txt --python .venv/bin/python
    info "Python environment ready"
}

build_frontend() {
    info "Building frontend..."
    cd "$INSTALL_DIR"
    bash build.sh
}

setup_systemd() {
    info "Creating systemd service: $SERVICE_NAME"

    cat > "/etc/systemd/system/${SERVICE_NAME}.service" <<EOF
[Unit]
Description=AOS Sizing API
After=network.target

[Service]
Type=simple
ExecStart=${INSTALL_DIR}/.venv/bin/python ${INSTALL_DIR}/app.py
WorkingDirectory=${INSTALL_DIR}
Restart=always
RestartSec=5
User=root
Environment="PATH=${INSTALL_DIR}/.venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin"
Environment="DATA_SOURCE=api"

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    systemctl enable "$SERVICE_NAME"
    info "systemd service created and enabled"
}

start_service() {
    info "Starting $SERVICE_NAME..."
    systemctl restart "$SERVICE_NAME"
    sleep 3

    if systemctl is-active --quiet "$SERVICE_NAME"; then
        info "Service is running"
        info "Access: http://$(hostname -I | awk '{print $1}'):${SERVICE_PORT}/"
    else
        warn "Service may still be loading data (first start takes 1-2 minutes)..."
        warn "Check status: systemctl status $SERVICE_NAME"
        warn "Check logs:   journalctl -u $SERVICE_NAME -f"
    fi
}

main() {
    echo "=========================================="
    echo "  AOS Sizing Tool — One-Click Deploy"
    echo "=========================================="
    echo ""

    check_root
    install_uv
    install_node
    clone_repo
    setup_python
    build_frontend
    setup_systemd
    start_service

    echo ""
    info "Deploy complete!"
    echo ""
    echo "  Service:  systemctl status $SERVICE_NAME"
    echo "  Logs:     journalctl -u $SERVICE_NAME -f"
    echo "  Restart:  systemctl restart $SERVICE_NAME"
    echo "  URL:      http://localhost:${SERVICE_PORT}/"
    echo ""
}

main "$@"
