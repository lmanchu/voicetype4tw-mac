#!/usr/bin/env bash
# ╔══════════════════════════════════════════════════════════════════╗
# ║  VoiceType4TW-Mac 一鍵安裝腳本                                    ║
# ║  用法: curl -fsSL https://raw.githubusercontent.com/             ║
# ║        jfamily4tw/voicetype4tw-mac/main/install.sh | bash        ║
# ╚══════════════════════════════════════════════════════════════════╝
set -e

# ── 顏色 ──
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color
BOLD='\033[1m'

banner() {
    echo ""
    echo -e "${CYAN}${BOLD}╔══════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}${BOLD}║   🎤 VoiceType4TW-Mac 一鍵安裝程式           ║${NC}"
    echo -e "${CYAN}${BOLD}║   語音輸入，繁體中文，為台灣而生              ║${NC}"
    echo -e "${CYAN}${BOLD}╚══════════════════════════════════════════════╝${NC}"
    echo ""
}

info()    { echo -e "${BLUE}[ℹ]${NC} $1"; }
success() { echo -e "${GREEN}[✅]${NC} $1"; }
warn()    { echo -e "${YELLOW}[⚠️]${NC} $1"; }
fail()    { echo -e "${RED}[❌]${NC} $1"; exit 1; }
step()    { echo -e "\n${BOLD}── $1 ──${NC}"; }

# ── 檢查 macOS ──
check_macos() {
    if [[ "$(uname)" != "Darwin" ]]; then
        fail "此腳本僅支援 macOS。Windows 版請參考 README。"
    fi
    local ver
    ver=$(sw_vers -productVersion)
    info "macOS 版本: $ver"
    
    # 檢查 Apple Silicon
    if [[ "$(uname -m)" == "arm64" ]]; then
        success "Apple Silicon (M系列) 偵測成功 → MLX 加速可用 🚀"
        IS_APPLE_SILICON=1
    else
        warn "Intel Mac 偵測到 → 將使用 faster-whisper (CPU) 模式"
        IS_APPLE_SILICON=0
    fi
}

# ── 檢查/安裝 Homebrew ──
check_homebrew() {
    if command -v brew &>/dev/null; then
        success "Homebrew 已安裝"
    else
        info "正在安裝 Homebrew..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        # Apple Silicon 的 brew 路徑
        if [[ -f /opt/homebrew/bin/brew ]]; then
            eval "$(/opt/homebrew/bin/brew shellenv)"
        fi
        success "Homebrew 安裝完成"
    fi
}

# ── 檢查/安裝 Python ──
check_python() {
    local py_cmd=""
    # 優先找 python3.12+
    for cmd in python3.12 python3.13 python3; do
        if command -v "$cmd" &>/dev/null; then
            local ver
            ver=$("$cmd" --version 2>&1 | awk '{print $2}')
            local major minor
            major=$(echo "$ver" | cut -d. -f1)
            minor=$(echo "$ver" | cut -d. -f2)
            if [[ "$major" -ge 3 && "$minor" -ge 10 ]]; then
                py_cmd="$cmd"
                break
            fi
        fi
    done

    if [[ -z "$py_cmd" ]]; then
        info "需要 Python 3.10+，正在透過 Homebrew 安裝..."
        brew install python@3.12
        py_cmd="python3.12"
    fi

    PYTHON="$py_cmd"
    success "Python: $($PYTHON --version)"
}

# ── 檢查/安裝 portaudio ──
check_portaudio() {
    if brew list portaudio &>/dev/null; then
        success "portaudio 已安裝（麥克風錄音所需）"
    else
        info "正在安裝 portaudio（麥克風錄音所需）..."
        brew install portaudio
        success "portaudio 安裝完成"
    fi
}

# ── Clone 或更新專案 ──
REPO_URL="https://github.com/lmanchu/voicetype4tw-mac.git"
INSTALL_DIR="$HOME/VoiceType4TW-Mac"

setup_project() {
    if [[ -d "$INSTALL_DIR/.git" ]]; then
        info "偵測到已安裝的版本，正在更新..."
        cd "$INSTALL_DIR"
        git pull --ff-only origin main 2>/dev/null || {
            warn "Git pull 失敗，嘗試 reset..."
            git fetch origin
            git reset --hard origin/main
        }
        success "專案已更新至最新版本"
    else
        info "正在下載 VoiceType4TW-Mac..."
        git clone "$REPO_URL" "$INSTALL_DIR"
        success "下載完成"
    fi
    cd "$INSTALL_DIR"
}

# ── 虛擬環境 ──
setup_venv() {
    if [[ ! -d "$INSTALL_DIR/venv" ]]; then
        info "建立 Python 虛擬環境..."
        "$PYTHON" -m venv venv
        success "虛擬環境建立完成"
    else
        success "虛擬環境已存在"
    fi
    
    # 啟動虛擬環境
    source venv/bin/activate
    PYTHON="python"  # venv 內用 python
}

# ── 安裝依賴 ──
install_deps() {
    info "正在安裝 Python 套件（首次安裝可能需要 2-5 分鐘）..."
    pip install --upgrade pip -q
    pip install -r requirements.txt -q
    
    # Apple Silicon: 安裝 MLX 加速引擎
    if [[ "$IS_APPLE_SILICON" -eq 1 ]]; then
        info "安裝 MLX 加速引擎（Apple Silicon 專用）..."
        pip install mlx mlx-whisper mlx_qwen3_asr -q 2>/dev/null || warn "MLX 安裝失敗，將使用 faster-whisper 模式"
    fi
    
    success "所有套件安裝完成"
}

# ── 權限提示 ──
show_permissions_guide() {
    echo ""
    echo -e "${YELLOW}${BOLD}┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓${NC}"
    echo -e "${YELLOW}${BOLD}┃  📋 首次使用前，請授予以下系統權限：          ┃${NC}"
    echo -e "${YELLOW}${BOLD}┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛${NC}"
    echo ""
    echo -e "  ${BOLD}1. 麥克風${NC} → 系統設定 → 隱私權與安全性 → 麥克風"
    echo -e "     允許「終端機 (Terminal)」使用麥克風"
    echo ""
    echo -e "  ${BOLD}2. 輔助使用${NC} → 系統設定 → 隱私權與安全性 → 輔助使用"
    echo -e "     允許「終端機 (Terminal)」控制電腦"
    echo ""
    echo -e "  ${CYAN}💡 這些權限允許 VoiceType 監聽快捷鍵並將文字貼入任何 App。${NC}"
    echo ""
}

# ── 建立啟動捷徑 ──
create_launcher() {
    local launcher="$INSTALL_DIR/start.sh"
    cat > "$launcher" << 'LAUNCH_SCRIPT'
#!/usr/bin/env bash
cd "$(dirname "$0")"
source venv/bin/activate
python main.py
LAUNCH_SCRIPT
    chmod +x "$launcher"
    
    # 也建立一個全域指令
    local bin_link="$HOME/.local/bin/voicetype"
    mkdir -p "$HOME/.local/bin"
    cat > "$bin_link" << EOF
#!/usr/bin/env bash
cd "$INSTALL_DIR"
source venv/bin/activate
python main.py
EOF
    chmod +x "$bin_link"
    
    success "啟動捷徑已建立"
    info "  快速啟動: ${BOLD}$INSTALL_DIR/start.sh${NC}"
    if echo "$PATH" | grep -q "$HOME/.local/bin"; then
        info "  全域指令: ${BOLD}voicetype${NC}"
    else
        info "  全域指令: ${BOLD}~/.local/bin/voicetype${NC}"
        info "  （將 ~/.local/bin 加入 PATH 後可直接輸入 voicetype）"
    fi
}

# ══════════════════════════════════════════════════════════
# 主流程
# ══════════════════════════════════════════════════════════
banner

step "1/7 檢查系統環境"
check_macos

step "2/7 檢查 Homebrew"
check_homebrew

step "3/7 檢查 Python"
check_python

step "4/7 安裝音訊套件"
check_portaudio

step "5/7 下載/更新專案"
setup_project

step "6/7 建立虛擬環境 & 安裝依賴"
setup_venv
install_deps

step "7/7 建立啟動捷徑"
create_launcher

show_permissions_guide

echo -e "${GREEN}${BOLD}╔══════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}${BOLD}║   🎉 安裝完成！                               ║${NC}"
echo -e "${GREEN}${BOLD}╚══════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  輸入以下指令來啟動 VoiceType："
echo -e "  ${CYAN}${BOLD}cd $INSTALL_DIR && bash start.sh${NC}"
echo ""

# 詢問是否立即啟動
read -p "是否立即啟動 VoiceType？[Y/n] " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]] || [[ -z "$REPLY" ]]; then
    info "正在啟動 VoiceType4TW-Mac..."
    python main.py
fi
