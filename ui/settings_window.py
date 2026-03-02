"""
Modern VoiceType Settings Window using PyQt6.
Features tabs for General, STT/LLM, Vocab/Memory, and Stats.
"""
import sys
import os
import platform
from pathlib import Path
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QStackedWidget, QLabel, QLineEdit, QComboBox, QCheckBox, QPushButton, 
    QTextEdit, QListWidget, QListWidgetItem, QTreeWidget, QTreeWidgetItem, QHeaderView,
    QMessageBox, QFileDialog, QScrollArea, QFrame, QSplitter
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QRect, QUrl, QTimer
from PyQt6.QtGui import QFont, QIcon, QColor, QPainter, QLinearGradient, QBrush, QPixmap, QDesktopServices

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import load_config, save_config
from paths import SOUL_BASE_PATH, SOUL_SCENARIO_DIR, SOUL_FORMAT_DIR, SOUL_TEMPLATE_DIR
STT_ENGINES = ["local_whisper", "mlx_whisper", "qwen3_asr", "groq", "gemini", "openrouter"]
LLM_ENGINES = ["ollama", "openai", "claude", "openrouter", "gemini", "deepseek", "qwen"]
WHISPER_MODELS = ["tiny", "base", "small", "medium", "large"]
TRIGGER_MODES = ["push_to_talk", "toggle"]
HOTKEYS = ["right_option", "left_option", "right_ctrl", "f13", "f14", "f15"]
LLM_MODES = ["replace", "fast"]
BUILD_ID = "BUILD-0301-B"  # v2.6.0 build

from hotkey.listener import key_to_str, str_to_key


class GlassCard(QFrame):
    """A premium looking card with subtle border and background."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            GlassCard {
                background-color: rgba(45, 45, 55, 180);
                border: 1px solid rgba(255, 255, 255, 30);
                border-radius: 12px;
            }
        """)

class SidebarButton(QPushButton):
    def __init__(self, icon_text, label, index, on_click, parent=None):
        super().__init__(parent)
        self.index = index
        self.setCheckable(True)
        import platform
        font_family = "Taipei Sans TC Beta" if platform.system() == "Darwin" else "Microsoft JhengHei"
        self.setText(f"{icon_text}  {label}")
        self.setFont(QFont(font_family, 16, QFont.Weight.Medium))
        self.setFixedHeight(60)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clicked.connect(lambda: on_click(self.index))
        self.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: #8a8d91;
                text-align: left;
                padding-left: 20px;
                border-radius: 12px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 10);
            }
            QPushButton:checked {
                background-color: #252a33;
                color: #7c4dff;
                font-weight: bold;
            }
        """)

class SNSButton(QPushButton):
    def __init__(self, icon_path, url, parent=None):
        super().__init__(parent)
        self.url = url
        self.setIcon(QIcon(icon_path))
        self.setIconSize(QSize(24, 24))
        self.setFixedSize(32, 32)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet("QPushButton { background: transparent; border: none; padding: 0; } QPushButton:hover { background: rgba(255,255,255,20); border-radius: 4px; }")
        self.clicked.connect(self._open_url)

    def _open_url(self):
        QDesktopServices.openUrl(QUrl(self.url))


class HotkeyRecorderButton(QPushButton):
    """A button that captures the next key press to set a hotkey."""
    key_changed = pyqtSignal(str)

    def __init__(self, current_key_str, is_dark=True):
        super().__init__()
        self._key_str = current_key_str
        self._recording = False
        self._is_dark = is_dark
        self._update_text()
        self.clicked.connect(self._start_recording)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMinimumHeight(32)

    def _update_text(self):
        if self._recording:
            self.setText("錄製中...")
            self.setStyleSheet("background: palette(highlight); color: white; border-radius: 6px;")
        else:
            self.setText(self._key_str if self._key_str else "未設定")
            self.setStyleSheet("""
                QPushButton {
                    background: rgba(255, 255, 255, 10);
                    border: 1px solid rgba(255, 255, 255, 20);
                    color: #ddd;
                    border-radius: 6px;
                    padding-left: 10px;
                    text-align: left;
                }
                QPushButton:hover {
                    background: rgba(255, 255, 255, 15);
                }
            """)

    def _start_recording(self):
        self._recording = True
        self._update_text()
        self.setFocus()

    def keyPressEvent(self, event):
        if self._recording:
            key = event.key()
            qt_to_pynput = {
                Qt.Key.Key_Alt: "alt_r",
                Qt.Key.Key_Control: "ctrl_r",
                Qt.Key.Key_Shift: "shift_r",
                Qt.Key.Key_Meta: "cmd_r",
                Qt.Key.Key_F13: "f13",
                Qt.Key.Key_F14: "f14",
                Qt.Key.Key_F15: "f15",
                Qt.Key.Key_Return: "enter",
                Qt.Key.Key_Space: "space",
            }
            p_key = qt_to_pynput.get(key) or event.text()
            if p_key:
                self._key_str = p_key
                self._recording = False
                self._update_text()
                self.key_changed.emit(self._key_str)
                self.clearFocus()
        else:
            super().keyPressEvent(event)

    @property
    def key_str(self): return self._key_str
    @key_str.setter
    def key_str(self, val):
        self._key_str = val
        self._update_text()


class PermissionLight(QWidget):
    def __init__(self, label_text, preference_url):
        super().__init__()
        self.url = preference_url
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 5, 0, 5)

        self.dot = QFrame()
        self.dot.setFixedSize(12, 12)
        self.dot.setStyleSheet("background-color: #555; border-radius: 6px;")
        layout.addWidget(self.dot)

        self.label = QLabel(label_text)
        self.label.setStyleSheet("color: #e2e4e7; font-size: 14px;")
        layout.addWidget(self.label)

        layout.addStretch()

        self.fix_btn = QPushButton("設定")
        self.fix_btn.setFixedWidth(60)
        self.fix_btn.setStyleSheet("""
            QPushButton {
                background-color: #2d333d;
                color: #8a8d91;
                font-size: 11px;
                padding: 2px 5px;
            }
            QPushButton:hover { background-color: #3d4452; color: #fff; }
        """)
        self.fix_btn.clicked.connect(self._open_preference)
        layout.addWidget(self.fix_btn)

    def _open_preference(self):
        import subprocess
        subprocess.run(["open", self.url])

    def set_status(self, authorized: bool):
        color = "#00e676" if authorized else "#ff5252"
        self.dot.setStyleSheet(f"background-color: {color}; border-radius: 6px;")
        status_text = " (已授權)" if authorized else " (未授權)"
        # Note: We keep the original label text and just update the color dot
        self.fix_btn.setVisible(not authorized)



class ModelStatusLight(QWidget):
    def __init__(self, model_name, size_info, desc_text):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 5, 0, 5)
        layout.setSpacing(2)
        
        top_layout = QHBoxLayout()
        self.dot = QFrame()
        self.dot.setFixedSize(10, 10)
        self.dot.setStyleSheet("background-color: #555; border-radius: 5px;")
        top_layout.addWidget(self.dot)
        
        self.label = QLabel(f"{model_name} ({size_info})")
        self.label.setStyleSheet("color: #e2e4e7; font-size: 13px; font-weight: bold;")
        top_layout.addWidget(self.label)
        top_layout.addStretch()
        layout.addLayout(top_layout)
        
        self.desc = QLabel(desc_text)
        self.desc.setStyleSheet("color: #888; font-size: 11px; margin-left: 18px;")
        self.desc.setWordWrap(True)
        layout.addWidget(self.desc)

    def set_status(self, downloaded: bool):
        # 綠色代表已就緒，灰色代表未下載
        color = "#00e676" if downloaded else "#444"
        self.dot.setStyleSheet(f"background-color: {color}; border-radius: 5px;")


class SettingsWindow(QMainWindow):
    def __init__(self, on_save=None, start_page=0):
        super().__init__()
        self.config = load_config()
        self.on_save = on_save
        self._is_dark = True # Pro mode is dark by default
        self._setup_ui()
        self._load_data()
        
        # 根據語言動態設定視窗標題
        lang = self.config.get("language", "zh")
        if "zh" in lang:
            self.setWindowTitle("嘴砲輸入法 2.6.0 Pro")
        else:
            self.setWindowTitle("VoiceType4TW Pro 2.6.0")
        
        # 設定啟動頁面
        if 0 <= start_page < len(self.sidebar_buttons):
            # 延遲一點點執行，避免在 UI 還沒完全掛載時觸發 visibility 切換
            QTimer.singleShot(10, lambda: self._on_sidebar_changed(start_page))

    def _setup_ui(self):
        self.setWindowTitle("VoiceType4TW Pro 2.6.0")
        self.setMinimumSize(900, 680)
        
        # Premium CSS
        self.setStyleSheet("""
            QMainWindow {
                background-color: #0f1115;
            }
            QWidget#sidebar_container {
                background-color: #16191f;
                border-right: 1px solid #252a33;
            }
            QListWidget#sidebar {
                background: transparent;
                border: none;
                outline: none;
                padding: 15px;
            }
            QListWidget#sidebar::item {
                padding: 20px;
                color: #8a8d91;
                border-radius: 12px;
                margin-bottom: 10px;
            }
            QListWidget#sidebar::item:selected {
                background-color: #252a33;
                color: #7c4dff;
                font-weight: bold;
            }
            QLabel {
                color: #e2e4e7;
                font-family: 'PingFang TC';
            }
            QLineEdit, QComboBox, QTextEdit, QListWidget, QTreeWidget {
                background-color: #1c1f26;
                border: 1px solid #2d333d;
                border-radius: 8px;
                color: #e2e4e7;
                padding: 8px;
                selection-background-color: #3d4452;
            }
            QTreeWidget::item { padding: 4px; }
            QHeaderView::section {
                background-color: #1c1f26;
                color: #8a8d91;
                padding: 6px;
                border: none;
                font-weight: bold;
            }
            QPushButton {
                background-color: #7c4dff;
                color: white;
                border-radius: 8px;
                padding: 10px 20px;
                font-weight: bold;
                border: none;
            }
            QPushButton:hover { background-color: #9575cd; }
            QPushButton#secondary {
                background-color: #2d333d;
                color: #e2e4e7;
            }
            QPushButton#danger {
                background-color: transparent;
                border: 1px solid #ff5252;
                color: #ff5252;
            }
            QPushButton#danger:hover {
                background-color: #ff5252;
                color: white;
            }
            QScrollArea { border: none; background: transparent; }
            QScrollBar:vertical {
                border: none;
                background: transparent;
                width: 6px;
            }
            QScrollBar::handle:vertical {
                background: #3d3d4d;
                border-radius: 3px;
                min-height: 20px;
            }
            QCheckBox { color: #e2e4e7; spacing: 10px; }
            QCheckBox::indicator { width: 18px; height: 18px; }
        """)

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Sidebar
        sidebar_container = QWidget()
        sidebar_container.setObjectName("sidebar_container")
        sidebar_container.setFixedWidth(300)
        sidebar_layout = QVBoxLayout(sidebar_container)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        
        logo_container = QWidget()
        logo_vbox = QVBoxLayout(logo_container)
        logo_vbox.setContentsMargins(0, 50, 0, 0) # Apply 50px Margin Top
        logo_vbox.setSpacing(0)
        
        lbl_en = QLabel("VoiceType4TW")
        lbl_en.setStyleSheet("font-family: 'Myriad Pro'; font-weight: bold; font-size: 28px; color: white;")
        lbl_en.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        os_ver = "Mac version" if platform.system() == "Darwin" else "Windows version"
        lbl_os = QLabel(os_ver)
        lbl_os.setStyleSheet("font-family: 'Myriad Pro'; font-style: italic; font-size: 14px; color: #8a8d91;")
        lbl_os.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        logo_vbox.addWidget(lbl_en)
        logo_vbox.addWidget(lbl_os)
        sidebar_layout.addWidget(logo_container)

        # Menu List - Use Layout instead of QListWidget for perfect visibility
        self.menu_group = QWidget()
        self.menu_layout = QVBoxLayout(self.menu_group)
        self.menu_layout.setContentsMargins(10, 20, 10, 0)
        self.menu_layout.setSpacing(5)
        
        self.sidebar_buttons = []
        menus = [
            ("🏠", "Dashboard"),
            ("🎙", "辨識 & AI"),
            ("✨", "靈魂設定"),
            ("📚", "詞彙 & 記憶"),
            ("📊", "數據統計"),
            ("⚙️", "系統設定")
        ]
        
        for i, (icon, label) in enumerate(menus):
            btn = SidebarButton(icon, label, i, self._on_sidebar_changed)
            self.menu_layout.addWidget(btn)
            self.sidebar_buttons.append(btn)
        
        self.sidebar_buttons[0].setChecked(True) # Default
        sidebar_layout.addWidget(self.menu_group)
        
        sidebar_layout.addStretch()
        
        # Credits and SNS at Bottom
        credit_box = QLabel(f"v2.6.0 Pro | {BUILD_ID}\n主要開發者：吉米丘\n協助開發者：Gemini, Nebula")
        credit_box.setStyleSheet("color: #555; font-size: 10px; margin-left: 25px; line-height: 1.2;")
        sidebar_layout.addWidget(credit_box)
        
        sns_container = QWidget()
        sns_layout = QHBoxLayout(sns_container)
        sns_layout.setContentsMargins(25, 5, 25, 20) # Left align with credit box
        sns_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        sns_layout.setSpacing(10)
        
        sns_links = [
            ("/Users/acyk/scripts/voicetype-mac/assets/sns-youtube.png", "https://youtube.com/@Jimmy4TW"),
            ("/Users/acyk/scripts/voicetype-mac/assets/sns-facebook.png", "https://www.facebook.com/acykjcms"),
            ("/Users/acyk/scripts/voicetype-mac/assets/sns-instagram.png", "https://www.instagram.com/jimmy4tw/"),
            ("/Users/acyk/scripts/voicetype-mac/assets/sns-tiktok.png", "https://www.tiktok.com/@jimmy4tw"),
            ("/Users/acyk/scripts/voicetype-mac/assets/sns-threads.png", "https://www.threads.net/@jimmy4tw"),
            ("/Users/acyk/scripts/voicetype-mac/assets/sns-4tw.png", "https://Jimmy4.TW/")
        ]
        
        for icon_path, url in sns_links:
            btn = SNSButton(icon_path, url)
            sns_layout.addWidget(btn)
        
        sidebar_layout.addWidget(sns_container)
        
        main_layout.addWidget(sidebar_container)

        # Content Area
        content_container = QWidget()
        self.content_layout = QVBoxLayout(content_container)
        self.content_layout.setContentsMargins(40, 50, 40, 40) # 50px Top Margin
        
        self.stack = QStackedWidget()
        self.content_layout.addWidget(self.stack)

        # Pages
        self.stack.addWidget(self._create_dashboard_page())
        self.stack.addWidget(self._create_stt_llm_page())
        self.stack.addWidget(self._create_soul_page())
        self.stack.addWidget(self._create_vocab_mem_page())
        self.stack.addWidget(self._create_stats_page())
        self.stack.addWidget(self._create_general_page())

        # Footer Actions (Grouped for visibility control)
        self.footer_widget = QWidget()
        footer = QHBoxLayout(self.footer_widget)
        footer.setContentsMargins(0, 20, 0, 0)
        self.btn_save = QPushButton("儲存並套用變更")
        self.btn_save.clicked.connect(self._save_action)
        self.btn_cancel = QPushButton("捨棄變更")
        self.btn_cancel.setObjectName("secondary")
        self.btn_cancel.clicked.connect(self.close)
        
        footer.addStretch()
        footer.addWidget(self.btn_cancel)
        footer.addWidget(self.btn_save)
        self.content_layout.addWidget(self.footer_widget)
        
        # Initial footer visibility
        self._on_sidebar_changed(0)

        main_layout.addWidget(content_container)

    def _on_sidebar_changed(self, idx):
        # Update button states
        for i, btn in enumerate(self.sidebar_buttons):
            btn.setChecked(i == idx)
        
        self.stack.setCurrentIndex(idx)
        # Dashboard (0) and Stats (4) hide save buttons
        self.footer_widget.setVisible(idx not in [0, 4])

    def _create_dashboard_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        # Shift everything UP: significantly reduce top margin
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(30)

        dash_header = QHBoxLayout()
        header = QLabel("Dashboard")
        header.setStyleSheet("font-size: 28px; font-weight: bold; color: #ffffff;")
        dash_header.addWidget(header)
        
        dash_header.addStretch()
        
        title_cn = QLabel("嘴砲輸入法")
        title_cn.setStyleSheet("font-family: 'Taipei Sans TC Beta'; font-size: 32px; font-weight: bold; color: #ffffff;")
        dash_header.addWidget(title_cn)
        
        # Add side margins to content but not to the header text alignment if needed
        dash_header_container = QWidget()
        dash_header_v = QVBoxLayout(dash_header_container)
        dash_header_v.setContentsMargins(0, 0, 0, 0) # Tight
        dash_header_v.addLayout(dash_header)
        layout.addWidget(dash_header_container)

        # Top Cards: Row 1
        cards_row1 = QHBoxLayout()
        cards_row1.setSpacing(15)
        
        # 1. Permission Card
        perm_card = GlassCard()
        p_layout = QVBoxLayout(perm_card)
        p_layout.setContentsMargins(15, 15, 15, 15)
        lbl_p = QLabel("🛡️ 權限驗證 (macOS)")
        lbl_p.setStyleSheet("font-weight: bold; color: #aaa; margin-bottom: 5px;")
        p_layout.addWidget(lbl_p)
        
        self.light_acc = PermissionLight("輔助功能 (Access)", "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility")
        p_layout.addWidget(self.light_acc)
        
        self.light_input = PermissionLight("輸入監聽 (Monitor)", "x-apple.systempreferences:com.apple.preference.security?Privacy_ListenEvent")
        p_layout.addWidget(self.light_input)
        
        self.light_mic = PermissionLight("麥克風 (Mic)", "x-apple.systempreferences:com.apple.preference.security?Privacy_Microphone")
        p_layout.addWidget(self.light_mic)
        cards_row1.addWidget(perm_card)

        # 2. Model Card (New)
        model_card = GlassCard()
        m_layout = QVBoxLayout(model_card)
        m_layout.setContentsMargins(15, 15, 15, 15)
        lbl_m = QLabel("🧠 AI 本地模型 (Faster-Whisper)")
        lbl_m.setStyleSheet("font-weight: bold; color: #aaa; margin-bottom: 5px;")
        m_layout.addWidget(lbl_m)
        
        self.light_model_small = ModelStatusLight("Small", "500MB", "輕快，但精準度稍遜。")
        self.light_model_medium = ModelStatusLight("Medium", "1.5GB", "均衡型，首選推薦 (精準)。")
        self.light_model_large = ModelStatusLight("Large", "3.0GB", "極致精準，背景嘈雜也能辨識。")
        m_layout.addWidget(self.light_model_small)
        m_layout.addWidget(self.light_model_medium)
        m_layout.addWidget(self.light_model_large)
        cards_row1.addWidget(model_card)

        # 3. Status Card
        status_card = GlassCard()
        status_layout = QVBoxLayout(status_card)
        status_layout.setContentsMargins(15, 15, 15, 15)
        lbl_s = QLabel("📺 運行狀態")
        lbl_s.setStyleSheet("font-weight: bold; color: #aaa; margin-bottom: 5px;")
        status_layout.addWidget(lbl_s)
        
        self.lbl_status_ai = QLabel("AI 潤飾: 已開啟")
        self.lbl_status_ai.setStyleSheet("color: #7c4dff; font-weight: bold; font-size: 16px;")
        status_layout.addWidget(self.lbl_status_ai)
        
        self.lbl_status_stt = QLabel("引擎: Local Whisper")
        self.lbl_status_stt.setStyleSheet("color: #888; font-size: 13px;")
        status_layout.addWidget(self.lbl_status_stt)
        cards_row1.addWidget(status_card)

        layout.addLayout(cards_row1)

        # Bottom Cards: Row 2
        cards_row2 = QHBoxLayout()

        # 3. Quick Stats Card
        stats_card = GlassCard()
        sq_layout = QVBoxLayout(stats_card)
        sq_layout.setContentsMargins(20, 20, 20, 20)
        sq_layout.addWidget(QLabel("今日語效"))
        self.lbl_today_count = QLabel("0 次錄音")
        self.lbl_today_count.setStyleSheet("color: #00e5ff; font-weight: bold; font-size: 16px;")
        sq_layout.addWidget(self.lbl_today_count)
        self.lbl_today_chars = QLabel("錄製約 0 字")
        sq_layout.addWidget(self.lbl_today_chars)
        cards_row2.addWidget(stats_card)

        # 4. Time Saved Card
        time_card = GlassCard()
        t_layout = QVBoxLayout(time_card)
        t_layout.setContentsMargins(20, 20, 20, 20)
        t_layout.addWidget(QLabel("累計省下時間"))
        self.lbl_time_saved = QLabel("0 分鐘")
        self.lbl_time_saved.setStyleSheet("color: #ffab40; font-weight: bold; font-size: 16px;")
        t_layout.addWidget(self.lbl_time_saved)
        self.lbl_total_chars_desc = QLabel("共辨識 0 字")
        self.lbl_total_chars_desc.setStyleSheet("color: #888; font-size: 13px;")
        t_layout.addWidget(self.lbl_total_chars_desc)
        cards_row2.addWidget(time_card)
        
        layout.addLayout(cards_row2)

        # Recent Activity Card
        recent_card = GlassCard()
        rc_layout = QVBoxLayout(recent_card)
        rc_layout.setContentsMargins(20, 20, 20, 20)
        rc_layout.addWidget(QLabel("💡 最近學到的詞彙"))
        self.dashboard_vocab = QListWidget()
        self.dashboard_vocab.setStyleSheet("background: transparent; border: none; font-size: 13px;")
        self.dashboard_vocab.setFixedHeight(120)
        rc_layout.addWidget(self.dashboard_vocab)
        layout.addWidget(recent_card)

        layout.addStretch()
        return page

    def _create_stt_llm_page(self):
        page = QScrollArea()
        page.setWidgetResizable(True)
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(25)

        layout.addWidget(self._page_section_header("🎙 語音辨識配置"))
        self.stt_engine = self._add_grid_row(layout, "核心引擎", QComboBox())
        engine_meta = {
            "local_whisper": "Local Whisper (一般版，支援 CPU/GPU通吃)",
            "mlx_whisper":   "MLX Whisper (Apple 晶片光速加速版)",
            "qwen3_asr":     "Qwen3-ASR (本地 MLX，繁中優化)",
            "groq":          "Groq Whisper (神級雲端超極速)",
            "gemini":        "Gemini (雲端 API)",
            "openrouter":    "OpenRouter (雲端 API)",
        }
        for eng in STT_ENGINES:
            self.stt_engine.addItem(engine_meta.get(eng, eng), eng)
        
        self.whisper_model = self._add_grid_row(layout, "Whisper 規格", QComboBox())
        self._populate_whisper_models()

        self.groq_key = self._add_grid_row(layout, "Groq API Key (選填)", QLineEdit())
        self.groq_key.setEchoMode(QLineEdit.EchoMode.Password)
        
        self.language = self._add_grid_row(layout, "優先辨識語言", QComboBox())
        lang_meta = {
            "zh": "繁體中文",
            "en": "英文",
            "ja": "日文",
            "ko": "韓文",
            "yue": "粵語",
            "auto": "自動偵測"
        }
        for code, name in lang_meta.items():
            self.language.addItem(f"{name} ({code})", code)

        layout.addWidget(self._page_section_header("🤖 大語言模型潤飾 (LLM) 配置"))
        self.llm_enabled = QCheckBox("啟用高階智慧潤飾與翻譯")
        layout.addWidget(self.llm_enabled)

        self.llm_engine = self._add_grid_row(layout, "模型提供者", QComboBox())
        self.llm_engine.addItems(LLM_ENGINES)

        self.llm_mode = self._add_grid_row(layout, "內容注入模式", QComboBox())
        self.llm_mode.addItems(LLM_MODES)

        # API Keys
        self.openai_key = self._add_grid_row(layout, "OpenAI / Claude Key", QLineEdit())
        self.openai_key.setEchoMode(QLineEdit.EchoMode.Password)
        
        self.openrouter_key = self._add_grid_row(layout, "OpenRouter / DeepSeek Key", QLineEdit())
        self.openrouter_key.setEchoMode(QLineEdit.EchoMode.Password)

        layout.addWidget(self._page_section_header("🪄 AI 魔術指令"))
        self.magic_trigger = self._add_grid_row(layout, "啟動咒語 (例如: 嘿 助理)", QLineEdit())
        self.magic_trigger.setPlaceholderText("預設為: 嘿 VoiceType")

        container.setLayout(layout)
        page.setWidget(container)
        return page

    def _create_soul_page(self):
        from PyQt6.QtWidgets import QTabWidget
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(10)

        layout.addWidget(self._page_section_header("✨ AI 靈魂與情境治理"))
        
        self.soul_tabs = QTabWidget()
        self.soul_tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid rgba(255,255,255,10); border-radius: 8px; background: rgba(30,30,40,100); }
            QTabBar::tab { background: transparent; color: #8a8d91; padding: 10px 20px; font-size: 14px; }
            QTabBar::tab:selected { color: #7c4dff; border-bottom: 2px solid #7c4dff; font-weight: bold; }
        """)
        
        # 1. 基底靈魂
        base_tab = QWidget()
        base_layout = QVBoxLayout(base_tab)
        self.soul_prompt = QTextEdit()
        self.soul_prompt.setFont(QFont("Monaco", 12))
        self.soul_prompt.setPlaceholderText("輸入 AI 的基底靈魂提示詞 (人格、風格、去贅詞規則)...")
        self.soul_prompt.setStyleSheet("background: rgba(20,20,30,150); border: 1px solid rgba(255,255,255,10); border-radius: 8px; color: #eee;")
        base_layout.addWidget(self.soul_prompt)
        self.soul_tabs.addTab(base_tab, "🏠 基底靈魂")

        # 2. 情境瀏覽
        scenario_tab = self._create_file_list_tab(SOUL_SCENARIO_DIR, "這裡存放不同場景的提示詞，例如：客訴、IG 貼文、商務簡報。")
        self.soul_tabs.addTab(scenario_tab, "🎭 情境模板")

        # 3. 格式瀏覽
        format_tab = self._create_file_list_tab(SOUL_FORMAT_DIR, "這裡決定輸出的格式，例如：電子郵件、表格、自然段落。")
        self.soul_tabs.addTab(format_tab, "📝 輸出格式")

        # 4. 模板管理
        template_tab = self._create_file_list_tab(SOUL_TEMPLATE_DIR, "這裡存放您儲存過的「好用輸出範例」。", is_json=True)
        self.soul_tabs.addTab(template_tab, "📌 我的模板")

        layout.addWidget(self.soul_tabs)
        return page

    def _create_file_list_tab(self, directory: Path, desc: str, is_json: bool = False):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 頂部操作區
        controls_layout = QVBoxLayout()
        desc_lbl = QLabel(desc)
        desc_lbl.setStyleSheet("color: #888; font-size: 12px;")
        controls_layout.addWidget(desc_lbl)
        
        create_layout = QHBoxLayout()
        new_item_name = QLineEdit()
        new_item_name.setPlaceholderText("輸入新項目名稱...")
        new_item_name.setStyleSheet("background: rgba(0,0,0,50); border: 1px solid #444; border-radius: 4px; padding: 4px; color: #fff;")
        
        btn_add = QPushButton("➕ 新增項目")
        btn_add.setFixedWidth(100)
        btn_add.setStyleSheet("background: #2e7d32; color: white; padding: 5px; border-radius: 4px;")
        
        btn_del = QPushButton("🗑 刪除所選")
        btn_del.setFixedWidth(100)
        btn_del.setStyleSheet("background: #c62828; color: white; padding: 5px; border-radius: 4px;")
        
        create_layout.addWidget(new_item_name)
        create_layout.addWidget(btn_add)
        create_layout.addWidget(btn_del)
        controls_layout.addLayout(create_layout)
        
        layout.addLayout(controls_layout)
        
        lst = QListWidget()
        lst.setStyleSheet("background: rgba(20,20,30,150); border: 1px solid rgba(255,255,255,10); border-radius: 8px; color: #eee;")
        layout.addWidget(lst)
        
        def refresh():
            lst.clear()
            if not directory.exists(): return
            ext = "*.json" if is_json else "*.md"
            for f in sorted(directory.glob(ext)):
                lst.addItem(f.name)
        
        QTimer.singleShot(100, refresh)
        
        # 內容編輯區 (不再是純預覽，改為可編輯)
        layout.addWidget(QLabel("內容編輯："))
        editor = QTextEdit()
        editor.setFont(QFont("Monaco", 11))
        editor.setStyleSheet("background: rgba(40,40,50,150); color: #fff; border: 1px solid rgba(255,255,255,20); border-radius: 8px;")
        layout.addWidget(editor)
        
        btn_save = QPushButton("💾 儲存修改")
        btn_save.setStyleSheet("background: #7c4dff; color: white; padding: 10px; border-radius: 6px; font-weight: bold;")
        btn_save.hide() # 初始隱藏
        layout.addWidget(btn_save)
        
        def on_item_clicked(item):
            fpath = directory / item.text()
            if fpath.exists():
                text = fpath.read_text(encoding="utf-8")
                if is_json:
                    import json
                    try:
                        data = json.loads(text)
                        text = json.dumps(data, indent=2, ensure_ascii=False)
                    except: pass
                editor.setPlainText(text)
                btn_save.show()
        
        def on_save():
            item = lst.currentItem()
            if not item: return
            fpath = directory / item.text()
            try:
                fpath.write_text(editor.toPlainText(), encoding="utf-8")
                QMessageBox.information(self, "成功", f"「{item.text()}」已儲存。")
            except Exception as e:
                QMessageBox.critical(self, "錯誤", f"儲存失敗：{e}")
        
        def on_add():
            name = new_item_name.text().strip()
            if not name:
                QMessageBox.warning(self, "提示", "請輸入項目名稱。")
                return
            
            filename = f"{name}.json" if is_json else f"{name}.md"
            fpath = directory / filename
            if fpath.exists():
                QMessageBox.warning(self, "警告", "名稱已存在！")
                return
            
            try:
                fpath.write_text("# 新項目\n在此輸入設定...", encoding="utf-8")
                new_item_name.clear()
                refresh()
                # 選中新項目
                items = lst.findItems(filename, Qt.MatchFlag.MatchExactly)
                if items:
                    lst.setCurrentItem(items[0])
                    on_item_clicked(items[0])
            except Exception as e:
                QMessageBox.critical(self, "錯誤", f"建立失敗：{e}")

        def on_delete():
            item = lst.currentItem()
            if not item: return
            reply = QMessageBox.question(self, "確認刪除", f"確定要刪除「{item.text()}」嗎？", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                (directory / item.text()).unlink()
                refresh()
                editor.clear()
                btn_save.hide()

        lst.itemClicked.connect(on_item_clicked)
        btn_add.clicked.connect(on_add)
        btn_del.clicked.connect(on_delete)
        btn_save.clicked.connect(on_save)
        
        btn_open = QPushButton("📂 在 Finder 中打開資料夾")
        btn_open.setStyleSheet("background: transparent; border: 1px solid #3d4452; color: #888; font-size: 11px;")
        btn_open.clicked.connect(lambda: os.system(f"open '{directory}'"))
        layout.addWidget(btn_open)

        return tab

    def _create_vocab_mem_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        
        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter)

        # Left: Vocab
        v_box = QWidget()
        v_layout = QVBoxLayout(v_box)
        v_layout.addWidget(QLabel("✏️ 私人詞庫"))
        self.vocab_list = QListWidget()
        v_layout.addWidget(self.vocab_list)
        
        vh = QHBoxLayout()
        self.vocab_input = QLineEdit()
        self.vocab_input.setPlaceholderText("新增...")
        self.btn_add_vocab = QPushButton("+")
        self.btn_add_vocab.setFixedWidth(50)
        self.btn_add_vocab.clicked.connect(self._add_vocab)
        vh.addWidget(self.vocab_input)
        vh.addWidget(self.btn_add_vocab)
        v_layout.addLayout(vh)
        
        self.btn_del_vocab = QPushButton("刪除已選")
        self.btn_del_vocab.setObjectName("danger")
        self.btn_del_vocab.clicked.connect(self._del_vocab)
        v_layout.addWidget(self.btn_del_vocab)

        # Right: Learned & Memory
        right_box = QWidget()
        rl = QVBoxLayout(right_box)
        
        rl.addWidget(QLabel("💡 AI 學習清單"))
        self.learned_list = QListWidget()
        rl.addWidget(self.learned_list)
        lh = QHBoxLayout()
        self.btn_promote = QPushButton("升格自訂")
        self.btn_promote.clicked.connect(self._promote_vocab)
        lh.addWidget(self.btn_promote)
        rl.addLayout(lh)

        rl.addWidget(QLabel("🧠 長期記憶"))
        self.mem_tree = QTreeWidget()
        self.mem_tree.setHeaderLabels(["時間", "快照"])
        rl.addWidget(self.mem_tree)

        splitter.addWidget(v_box)
        splitter.addWidget(right_box)
        return page

    def _create_stats_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(self._page_section_header("詳細分析數據"))
        
        self.stats_tree = QTreeWidget()
        self.stats_tree.setHeaderLabels(["範圍", "對話數", "語音長度", "轉錄字數", "省下時間"])
        layout.addWidget(self.stats_tree)
        
        self.btn_refresh_stats = QPushButton("重新整理數據")
        self.btn_refresh_stats.setObjectName("secondary")
        self.btn_refresh_stats.clicked.connect(self._refresh_stats)
        layout.addWidget(self.btn_refresh_stats)
        
        layout.addStretch()
        return page

    def _create_general_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        
        layout.addWidget(self._page_section_header("⌨️ 控制熱鍵錄製"))
        
        hotkey_grid = QFrame()
        grid_layout = QVBoxLayout(hotkey_grid)
        
        self.btn_ptt = HotkeyRecorderButton(self.config.get("hotkey_ptt", "alt_r"))
        self._add_grid_row(grid_layout, "錄音按住 (PTT)", self.btn_ptt)
        
        layout.addWidget(hotkey_grid)
        
        layout.addWidget(self._page_section_header("⚙️ 偏好偏好"))
        self.auto_paste = QCheckBox("結果自動貼上 (Paste automatically)")
        self.auto_paste.setChecked(self.config.get("auto_paste", True))
        layout.addWidget(self.auto_paste)
        
        self.completion_sound = QCheckBox("錄音完成時播放音效 (Play sound on completion)")
        self.completion_sound.setChecked(self.config.get("completion_sound", True))
        layout.addWidget(self.completion_sound)
        
        self.debug_mode = QCheckBox("啟用詳細日誌輸出 (Debug logging)")
        self.debug_mode.setChecked(self.config.get("debug_mode", False))
        layout.addWidget(self.debug_mode)

        self.debug_demo_mode = QCheckBox("情境模擬 Demo 版 (Debug Scenario Demo Mode)")
        self.debug_demo_mode.setChecked(self.config.get("debug_demo_mode", False))
        layout.addWidget(self.debug_demo_mode)

        layout.addStretch()
        return page

    def _page_section_header(self, text):
        l = QLabel(text)
        l.setStyleSheet("font-weight: bold; font-size: 16px; color: #7c4dff; margin-top: 10px; margin-bottom: 5px;")
        return l

    def _add_grid_row(self, layout, label_text, widget):
        row = QHBoxLayout()
        l = QLabel(label_text)
        l.setFixedWidth(160)
        row.addWidget(l)
        row.addWidget(widget)
        layout.addLayout(row)
        return widget

    # --- Data and Logic ---
    def _load_data(self):
        if SOUL_BASE_PATH.exists():
            self.soul_prompt.setPlainText(SOUL_BASE_PATH.read_text(encoding="utf-8"))
        
        # Load from config
        stt_val = self.config.get("stt_engine", "local_whisper")
        stt_idx = self.stt_engine.findData(stt_val)
        if stt_idx >= 0:
            self.stt_engine.setCurrentIndex(stt_idx)
        else:
            self.stt_engine.setCurrentText(stt_val)
            
        # Whisper model selection
        m_val = self.config.get("whisper_model", "medium")
        m_idx = self.whisper_model.findData(m_val)
        if m_idx >= 0:
            self.whisper_model.setCurrentIndex(m_idx)
        else:
            self.whisper_model.setCurrentText(m_val) # fallback
        self.groq_key.setText(self.config.get("groq_api_key", ""))
        lang_val = self.config.get("language", "zh")
        lang_idx = self.language.findData(lang_val)
        if lang_idx >= 0:
            self.language.setCurrentIndex(lang_idx)
        else:
            self.language.setCurrentText(lang_val)
        self.llm_enabled.setChecked(self.config.get("llm_enabled", False))
        self.llm_engine.setCurrentText(self.config.get("llm_engine", "ollama"))
        self.llm_mode.setCurrentText(self.config.get("llm_mode", "replace"))
        self.openai_key.setText(self.config.get("openai_api_key", ""))
        self.openrouter_key.setText(self.config.get("openrouter_api_key", ""))
        self.magic_trigger.setText(self.config.get("magic_trigger", "嘿 VoiceType"))

        self._refresh_vocab()
        self._refresh_learned_vocab()
        self._refresh_memory()
        self._refresh_stats()
        self._update_dashboard_status()

    def _update_dashboard_status(self):
        ai = "已開啟" if self.config.get("llm_enabled") else "已關閉"
        self.lbl_status_ai.setText(f"AI 潤飾: {ai}")
        self.lbl_status_ai.setStyleSheet(f"color: {'#7c4dff' if ai == '已開啟' else '#666'}; font-weight: bold; font-size: 16px;")
        
        eng = self.config.get("stt_engine", "local_whisper")
        self.lbl_status_stt.setText(f"引擎: {eng.upper()}")
        
        # 檢查權限與模型狀態
        self._check_all_permissions()
        self._check_local_models()

    def _check_all_permissions(self):
        import logging
        log = logging.getLogger("voicetype")
        
        # 1. Accessibility — AXIsProcessTrusted 是 C 函數，必須用 ctypes
        trusted = False
        try:
            import ctypes
            lib = ctypes.cdll.LoadLibrary(
                '/System/Library/Frameworks/ApplicationServices.framework/ApplicationServices')
            lib.AXIsProcessTrusted.restype = ctypes.c_bool
            trusted = lib.AXIsProcessTrusted()
            log.info(f"[PERM] Accessibility: {trusted}")
        except Exception as e:
            log.error(f"[PERM] Accessibility check FAILED: {e}")
            trusted = False
        self.light_acc.set_status(trusted)

        # 2. Input Monitoring（通常與輔助功能同步）
        self.light_input.set_status(trusted)

        # 3. Microphone (macOS)
        try:
            import objc
            # 使用 objc 動態載入 AVFoundation，此查詢方法不會觸發彈窗
            objc.loadBundle('AVFoundation', bundle_path='/System/Library/Frameworks/AVFoundation.framework', module_globals=globals())
            # 'soun' is the type for 'audio' in AVFoundation (AVMediaTypeAudio)
            status = AVCaptureDevice.authorizationStatusForMediaType_('soun')
            mic_ok = (status == 3) # 3 == AVAuthorizationStatusAuthorized
            self.light_mic.set_status(mic_ok)
            log.info(f"[PERM] Microphone Status: {status} (Authorized: {mic_ok})")
        except Exception as e:
            log.error(f"[PERM] Microphone check FAILED: {e}")
            self.light_mic.set_status(False)

    def _check_local_models(self):
        """檢查 Faster-Whisper 模型是否已下載到本機快取"""
        self.light_model_small.set_status(self._is_model_present("small"))
        self.light_model_medium.set_status(self._is_model_present("medium"))
        self.light_model_large.set_status(self._is_model_present("large"))

    def _is_model_present(self, size: str) -> bool:
        try:
            cache_path = Path.home() / ".cache" / "huggingface" / "hub"
            if not cache_path.exists():
                return False
            # faster-whisper 命名規則：models--Systran--faster-whisper-<size>
            folder_prefix = f"models--Systran--faster-whisper-{size}"
            for p in cache_path.iterdir():
                if p.is_dir() and p.name.startswith(folder_prefix):
                    # 檢查是否有 snapshot
                    snap = p / "snapshots"
                    if snap.exists() and any(snap.iterdir()):
                        return True
            return False
        except Exception:
            return False

    def _populate_whisper_models(self):
        """依據模型大小、本機狀態與推薦程度，格式化顯示 COMBOBOX 選單內容"""
        self.whisper_model.clear()
        meta = {
            "tiny":   ("75MB",  "極速辨識"),
            "base":   ("145MB", "快速辨識"),
            "small":  ("500MB", "輕量，速度快"),
            "medium": ("1.5GB", "均衡型，推薦首選"),
            "large":  ("3.0GB", "極限型，最精準"),
        }
        # 依序加入 Tiny 到 Large
        for m in ["tiny", "base", "small", "medium", "large"]:
            if m in meta:
                size, desc = meta[m]
                is_ready = self._is_model_present(m)
                status = " (已就緒)" if is_ready else " (未下載)"
                label = f"{m.upper():<8} [{size}] - {desc}{status}"
                self.whisper_model.addItem(label, m) # m 為內部代號，例如 "medium"

    def _refresh_vocab(self):
        self.vocab_list.clear()
        try:
            from vocab.manager import load_custom_vocab
            for word in load_custom_vocab():
                self.vocab_list.addItem(word)
        except: pass

    def _refresh_learned_vocab(self):
        self.learned_list.clear()
        self.dashboard_vocab.clear()
        try:
            from vocab.manager import load_all_learned_words, load_auto_memory
            memory = load_auto_memory()
            words = load_all_learned_words()
            for word in words:
                count = memory.get(word, 0)
                self.learned_list.addItem(f"{word} ({count})")
            # Dashboard only show top 5
            for word in words[:5]:
                self.dashboard_vocab.addItem(word)
        except: pass

    def _promote_vocab(self):
        item = self.learned_list.currentItem()
        if not item: return
        word = item.text().split(" (")[0]
        try:
            from vocab.manager import promote_learned_word
            promote_learned_word(word)
            self._refresh_vocab()
            self._refresh_learned_vocab()
        except Exception as e:
            QMessageBox.critical(self, "錯誤", str(e))

    def _refresh_memory(self):
        self.mem_tree.clear()
        try:
            from memory.manager import load_memory
            memory = load_memory()
            for entry in reversed(memory.get("entries", [])):
                ts = entry.get("ts", "")[:16]
                text = (entry.get("llm") or entry.get("stt", ""))[:40]
                self.mem_tree.addTopLevelItem(QTreeWidgetItem([ts, text + "..."]))
        except: pass

    def _refresh_stats(self):
        self.stats_tree.clear()
        try:
            from stats.tracker import get_summary
            s = get_summary()
            self.lbl_today_count.setText(f"{s['today']['sessions']} 次錄音")
            self.lbl_today_chars.setText(f"錄製約 {s['today']['chars']} 字")
            
            # 計算省下時間 (以一般人打字速度 40字/分 計算)
            total_chars = s['total']['chars']
            saved_mins = total_chars / 40.0
            if saved_mins < 60:
                self.lbl_time_saved.setText(f"{saved_mins:.1f} 分鐘")
            else:
                self.lbl_time_saved.setText(f"{saved_mins/60.0:.1f} 小時")
            self.lbl_total_chars_desc.setText(f"累計辨識 {total_chars} 字")
            
            def format_saved(chars):
                mins = chars / 40.0
                if mins < 60: return f"{mins:.1f}m"
                return f"{mins/60.0:.1f}h"

            self.stats_tree.addTopLevelItem(QTreeWidgetItem([
                "今日", str(s["today"]["sessions"]), f"{s['today']['duration']}s", str(s["today"]["chars"]), format_saved(s["today"]["chars"])
            ]))
            self.stats_tree.addTopLevelItem(QTreeWidgetItem([
                "本週", str(s["week"]["sessions"]), f"{s['week']['duration']}s", str(s["week"]["chars"]), format_saved(s["week"]["chars"])
            ]))
            self.stats_tree.addTopLevelItem(QTreeWidgetItem([
                "累積", str(s["total"]["sessions"]), f"{s['total']['duration']}s", str(s["total"]["chars"]), format_saved(s["total"]["chars"])
            ]))
        except: pass

    def _add_vocab(self):
        word = self.vocab_input.text().strip()
        if not word: return
        from vocab.manager import add_custom_word
        add_custom_word(word)
        self.vocab_input.clear()
        self._refresh_vocab()

    def _del_vocab(self):
        item = self.vocab_list.currentItem()
        if not item: return
        from vocab.manager import remove_custom_word
        remove_custom_word(item.text())
        self._refresh_vocab()

    def _save_action(self):
        self.config["stt_engine"] = self.stt_engine.currentData() or self.stt_engine.currentText()
        # 使用 currentData 取得內部代號如 "medium" 而非顯示文字
        self.config["whisper_model"] = self.whisper_model.currentData() or self.whisper_model.currentText()
        self.config["groq_api_key"] = self.groq_key.text().strip()
        self.config["language"] = self.language.currentData() or self.language.currentText()
        self.config["llm_enabled"] = self.llm_enabled.isChecked()
        self.config["llm_engine"] = self.llm_engine.currentText()
        self.config["llm_mode"] = self.llm_mode.currentText()
        self.config["openai_api_key"] = self.openai_key.text().strip()
        self.config["openrouter_api_key"] = self.openrouter_key.text().strip()
        self.config["magic_trigger"] = self.magic_trigger.text().strip() or "嘿 VoiceType"
        self.config["hotkey_ptt"] = self.btn_ptt.key_str
        self.config["auto_paste"] = self.auto_paste.isChecked()
        self.config["completion_sound"] = self.completion_sound.isChecked()
        self.config["debug_mode"] = self.debug_mode.isChecked()
        self.config["debug_demo_mode"] = self.debug_demo_mode.isChecked()

        try:
            SOUL_BASE_PATH.write_text(self.soul_prompt.toPlainText().strip(), encoding="utf-8")
        except: pass

        save_config(self.config)
        QMessageBox.information(self, "嘴砲輸入法", "設定已儲存並生效。")
        if self.on_save: self.on_save(self.config)
        self.close()

    def run(self):
        self.show()

def has_api_key(config: dict) -> bool:
    stt = config.get("stt_engine", "local_whisper")
    if stt == "local_whisper" and (not config.get("llm_enabled") or config.get("llm_engine") == "ollama"):
        return True
    for k in ["groq_api_key", "openai_api_key", "openrouter_api_key"]:
        if config.get(k): return True
    return False

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = SettingsWindow()
    win.show()
    sys.exit(app.exec())
