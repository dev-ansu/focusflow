from datetime import datetime, timezone
import pymupdf as fitz
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QScrollArea, QMessageBox, QFrame, QCheckBox, QTextEdit, QProgressBar, QComboBox
)
from PySide6.QtGui import QImage, QPixmap, QPainter, QPen, QColor, QKeySequence, QShortcut
from PySide6.QtCore import Qt, QTimer, QTime, Signal, QRect, QPoint, QUrl
from PySide6.QtMultimedia import QSoundEffect

from database.connection import SessionLocal
from models.models import StudyBlock, BlockStatus, Topic, PdfDocument, Subject, Highlight, Note
from services.study_manager import StudyManager

from PySide6.QtWidgets import QDialog, QSpinBox, QFormLayout, QDialogButtonBox, QTreeWidget, QTreeWidgetItem

class PomodoroSettingsDialog(QDialog):
    def __init__(self, work_min=25, short_min=5, long_min=15, parent=None):
        super().__init__(parent)
        self.setWindowTitle("⚙️ Configurações do Pomodoro")
        self.setFixedWidth(280)
        
        self.setStyleSheet("""
            QDialog {
                background-color: #1E1E2E;
                color: #CDD6F4;
                font-family: 'Segoe UI', system-ui, sans-serif;
            }
            QLabel {
                color: #CDD6F4;
                font-size: 13px;
            }
            QSpinBox {
                background-color: #181825;
                color: #CDD6F4;
                border: 1px solid #313244;
                border-radius: 5px;
                padding: 4px;
                font-size: 13px;
            }
            QSpinBox::up-button, QSpinBox::down-button {
                background-color: #313244;
                border-radius: 2px;
            }
            QPushButton {
                background-color: #313244;
                color: #CDD6F4;
                border: 1px solid #45475A;
                border-radius: 5px;
                padding: 6px 14px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #45475A;
            }
        """)

        layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        form_layout.setSpacing(10)

        # Campos de minutos
        self.sb_work = QSpinBox()
        self.sb_work.setRange(1, 180)
        self.sb_work.setValue(work_min)
        self.sb_work.setSuffix(" min")

        self.sb_short = QSpinBox()
        self.sb_short.setRange(1, 60)
        self.sb_short.setValue(short_min)
        self.sb_short.setSuffix(" min")

        self.sb_long = QSpinBox()
        self.sb_long.setRange(1, 120)
        self.sb_long.setValue(long_min)
        self.sb_long.setSuffix(" min")

        form_layout.addRow("🎯 Tempo de Foco:", self.sb_work)
        form_layout.addRow("☕ Pausa Curta:", self.sb_short)
        form_layout.addRow("🎉 Pausa Longa:", self.sb_long)

        layout.addLayout(form_layout)

        # Botões do Modal
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addSpacing(10)
        layout.addWidget(buttons)

    def get_values(self):
        """Retorna os valores selecionados em minutos."""
        return self.sb_work.value(), self.sb_short.value(), self.sb_long.value()

class PDFSelectableLabel(QLabel):
    area_selected = Signal(QRect)
    point_clicked = Signal(QPoint)

    def __init__(self, text=""):
        super().__init__(text)
        self.selection_start = None
        self.selection_end = None
        self.is_selecting = False
        self.selected_color = "#FFFF00"
        
    def set_selection_color(self, hex_color: str):
        self.selected_color = hex_color

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.selection_start = event.position().toPoint()
            self.selection_end = self.selection_start
            self.is_selecting = True
            self.update()

    def mouseMoveEvent(self, event):
        if self.is_selecting:
            self.selection_end = event.position().toPoint()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.is_selecting:
            self.is_selecting = False
            self.selection_end = event.position().toPoint()
            
            rect = QRect(self.selection_start, self.selection_end).normalized()
            if rect.width() <= 5 and rect.height() <= 5:
                self.point_clicked.emit(self.selection_start)
            else:
                self.area_selected.emit(rect)

            self.selection_start = None
            self.selection_end = None
            self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.is_selecting and self.selection_start and self.selection_end:
            painter = QPainter(self)
            rect = QRect(self.selection_start, self.selection_end).normalized()
            
            fill_color = QColor(self.selected_color)
            fill_color.setAlpha(80)
            
            painter.setPen(QPen(fill_color.darker(120), 1, Qt.PenStyle.SolidLine))
            painter.setBrush(fill_color)
            painter.drawRect(rect)

class PDFOutlineTreeWidget(QTreeWidget):
    page_requested = Signal(int)  # Emite o número da página (base 1)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setHeaderHidden(True)
        self.setAnimated(True)
        self.setStyleSheet("""
            QTreeWidget {
                background-color: #181825;
                color: #CDD6F4;
                border: 1px solid #313244;
                border-radius: 6px;
                padding: 4px;
                font-size: 12px;
            }
            QTreeWidget::item {
                padding: 4px;
                border-radius: 4px;
            }
            QTreeWidget::item:hover {
                background-color: #313244;
            }
            QTreeWidget::item:selected {
                background-color: #45475A;
                color: #89B4FA;
            }
        """)
        self.itemClicked.connect(self.on_item_clicked)

    def load_toc(self, toc_list):
        """
        Recebe a lista TOC no formato PyMuPDF: [[level, title, page], ...]
        """
        self.clear()
        if not toc_list:
            item = QTreeWidgetItem(self, ["Nenhum sumário disponível"])
            item.setFlags(item.flags() & ~Qt.ItemIsSelectable)
            return

        parents = {0: self}
        for level, title, page in toc_list:
            parent = parents.get(level - 1, self)
            item = QTreeWidgetItem(parent, [f"{title} (p. {page})"])
            item.setData(0, Qt.UserRole, page)
            parents[level] = item

        self.expandToDepth(0)

    def on_item_clicked(self, item, column):
        page = item.data(0, Qt.UserRole)
        if page is not None and isinstance(page, int):
            self.page_requested.emit(page)


class StudyReaderView(QWidget):
    back_requested = Signal()
    toggle_left_sidebar_requested = Signal()
    block_completed = Signal()

    def __init__(self, block_id=None):
        super().__init__()
        self.block_id = block_id
        self.doc = None
        self.current_pdf_id = None
        self.current_page = 0
        self.total_pages = 0
        self.zoom_factor = 1.0
        self.auto_fit_width = True
        self.dark_mode = False
        self.is_focus_mode = False  # Estado do Modo Foco Total
        
        self.selected_color = "#FFFF00"
        self.color_buttons = {}

        self.dont_show_completion_msg = False
        self.page_start = 1
        self.page_end = 1
        self.block_status = None
        
        # --- CONFIGURAÇÃO DO TIMER / POMODORO ---
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_timer)
        self.elapsed_seconds = 0  # Segundos reais acumulados de estudo (salvos no BD)

        # Estados do Modo
        self.timer_mode = "STOPWATCH"  # "STOPWATCH" ou "POMODORO"
        self.work_duration = 25 * 60     # 25 minutos
        self.short_break = 5 * 60        # 5 minutos
        self.long_break = 15 * 60       # 15 minutos
        self.pomodoro_state = "WORK"     # "WORK", "BREAK", "LONG_BREAK"
        self.pomodoro_remaining = self.work_duration
        self.pomodoros_completed = 0

        # Alerta Sonoro
        self.alarm_sound = QSoundEffect(self)
        self.alarm_sound.setSource(QUrl.fromLocalFile("assets/sounds/bell.wav"))
        self.alarm_sound.setVolume(0.8)

        self.setup_shortcuts()
        self.init_ui()
        
    def setup_shortcuts(self):
        QShortcut(QKeySequence("Right"), self, self.next_page)
        QShortcut(QKeySequence("PageDown"), self, self.next_page)
        QShortcut(QKeySequence("Left"), self, self.prev_page)
        QShortcut(QKeySequence("PageUp"), self, self.prev_page)
        
        QShortcut(QKeySequence("Ctrl++"), self, self.zoom_in)
        QShortcut(QKeySequence("Ctrl+-"), self, self.zoom_out)
        QShortcut(QKeySequence("Ctrl+D"), self, lambda: self.btn_dark_mode.animateClick())

        # Atalhos para Modo Foco (F11 para alternar, Esc para sair)
        QShortcut(QKeySequence("F11"), self, self.toggle_focus_mode)
        QShortcut(QKeySequence("Escape"), self, self.exit_focus_mode)

        QShortcut(QKeySequence("1"), self, lambda: self.set_highlight_color("#FFFF00"))
        QShortcut(QKeySequence("2"), self, lambda: self.set_highlight_color("#2ECC71"))
        QShortcut(QKeySequence("3"), self, lambda: self.set_highlight_color("#3498DB"))
        QShortcut(QKeySequence("4"), self, lambda: self.set_highlight_color("#E91E63"))

    def init_ui(self):
        self.setStyleSheet("""
            QWidget {
                background-color: #232534;
                color: #CDD6F4;
                font-family: 'Segoe UI', system-ui, sans-serif;
            }
            QScrollBar:vertical, QScrollBar:horizontal {
                background-color: #1E1E2E;
                width: 10px;
                height: 10px;
                border: none;
            }
            QScrollBar::handle:vertical, QScrollBar::handle:horizontal {
                background-color: #45475A;
                border-radius: 5px;
            }
            QScrollBar::handle:hover {
                background-color: #585B70;
            }
            QPushButton.tool-btn {
                background-color: #1E1E2E;
                color: #CDD6F4;
                border: 1px solid #313244;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 13px;
                font-weight: 500;
            }
            QPushButton.tool-btn:hover {
                background-color: #313244;
                border-color: #45475A;
            }
            QPushButton.tool-btn:checked {
                background-color: #45475A;
                color: #89B4FA;
                border-color: #89B4FA;
            }
        """)

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        # 1. TOOLBAR SUPERIOR
        self.header_widget = QWidget()
        self.header_widget.setStyleSheet("""
            QWidget {
                background-color: #1E1E2E;
                border-bottom: 1px solid #313244;
            }
        """)
        header_layout = QHBoxLayout(self.header_widget)
        header_layout.setContentsMargins(12, 8, 12, 8)

        self.btn_toggle_left = QPushButton("📑 Sumário")
        self.btn_toggle_left.setProperty("class", "tool-btn")
        self.btn_toggle_left.setToolTip("Ocultar/Exibir Sumário do PDF")
        self.btn_toggle_left.clicked.connect(self.toggle_left_sidebar)

        self.btn_back = QPushButton("⬅️ Voltar")
        self.btn_back.setProperty("class", "tool-btn")
        self.btn_back.clicked.connect(self.save_and_pause)

        self.lbl_header_title = QLabel("Leitor de Estudos")
        self.lbl_header_title.setStyleSheet("font-weight: bold; font-size: 15px; color: #89B4FA; border: none;")

        # Timer compacto do topo (visível quando a barra de anotações estiver oculta)
        self.lbl_header_timer = QLabel("⏱️ 00:00:00")
        self.lbl_header_timer.setStyleSheet("""
            font-size: 14px; 
            font-weight: bold; 
            color: #A6E3A1; 
            background-color: #181825; 
            border: 1px solid #313244; 
            border-radius: 6px; 
            padding: 4px 10px;
        """)
        self.lbl_header_timer.setToolTip("Tempo Dedicado / Pomodoro")
        self.lbl_header_timer.setVisible(False)

        # Botão Modo Foco Total (F11)
        self.btn_focus_mode = QPushButton("🖥️ Foco")
        self.btn_focus_mode.setProperty("class", "tool-btn")
        self.btn_focus_mode.setToolTip("Modo Foco Total (Atalho: F11)")
        self.btn_focus_mode.clicked.connect(self.toggle_focus_mode)

        self.btn_toggle_right = QPushButton("📝 Anotações")
        self.btn_toggle_right.setProperty("class", "tool-btn")
        self.btn_toggle_right.setToolTip("Ocultar/Exibir Painel de Anotações")
        self.btn_toggle_right.clicked.connect(self.toggle_right_sidebar)

        header_layout.addWidget(self.btn_toggle_left)
        header_layout.addWidget(self.btn_back)
        header_layout.addSpacing(15)
        header_layout.addWidget(self.lbl_header_title)
        header_layout.addStretch()
        header_layout.addWidget(self.lbl_header_timer)
        header_layout.addSpacing(10)
        header_layout.addWidget(self.btn_focus_mode)
        header_layout.addSpacing(10)
        header_layout.addWidget(self.btn_toggle_right)

        outer_layout.addWidget(self.header_widget)

        # 2. ÁREA CENTRAL
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # === PAINEL LATERAL ESQUERDO (SUMÁRIO / TOC) ===
        self.left_sidebar = QFrame()
        self.left_sidebar.setFixedWidth(240)
        self.left_sidebar.setVisible(False)  # Inicia oculta por padrão
        self.left_sidebar.setStyleSheet("""
            QFrame#LeftSidebar {
                background-color: #1E1E2E;
                border-right: 1px solid #313244;
            }
        """)
        self.left_sidebar.setObjectName("LeftSidebar")
        
        left_sidebar_layout = QVBoxLayout(self.left_sidebar)
        left_sidebar_layout.setContentsMargins(10, 10, 10, 10)
        left_sidebar_layout.setSpacing(8)

        lbl_toc_title = QLabel("<b>📌 Sumário do PDF</b>")
        lbl_toc_title.setStyleSheet("font-size: 13px; color: #CDD6F4; border: none;")
        left_sidebar_layout.addWidget(lbl_toc_title)

        self.toc_tree = PDFOutlineTreeWidget()
        self.toc_tree.page_requested.connect(self.go_to_page_from_toc)
        left_sidebar_layout.addWidget(self.toc_tree)

        # Adiciona a barra da esquerda no layout principal
        main_layout.addWidget(self.left_sidebar, stretch=0)

        pdf_container_widget = QWidget()
        pdf_container_layout = QVBoxLayout(pdf_container_widget)
        pdf_container_layout.setContentsMargins(12, 12, 12, 12)
        pdf_container_layout.setSpacing(8)
        

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setAlignment(Qt.AlignCenter)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                background-color: #2D2F42;
                border: 1px solid #363952;
                border-radius: 8px;
            }
        """)

        self.lbl_pdf_page = PDFSelectableLabel("Nenhum PDF carregado.")
        self.lbl_pdf_page.setAlignment(Qt.AlignCenter)
        self.lbl_pdf_page.area_selected.connect(self.handle_area_selected)
        self.lbl_pdf_page.point_clicked.connect(self.handle_point_clicked)
        self.scroll_area.setWidget(self.lbl_pdf_page)
        
        pdf_container_layout.addWidget(self.scroll_area, stretch=1)

        # BARRA INFERIOR UNIFICADA
        self.bottom_bar = QFrame()
        self.bottom_bar.setStyleSheet("""
            QFrame {
                background-color: #1E1E2E;
                border: 1px solid #313244;
                border-radius: 8px;
                padding: 4px;
            }
            QLabel { border: none; font-size: 12px; }
        """)
        bottom_layout = QHBoxLayout(self.bottom_bar)
        bottom_layout.setContentsMargins(8, 4, 8, 4)
        bottom_layout.setSpacing(6)

        # Paginação
        self.btn_prev_page = QPushButton("◀")
        self.btn_prev_page.setProperty("class", "tool-btn")
        self.btn_prev_page.clicked.connect(self.prev_page)

        self.lbl_page_info = QLabel("Pág: 0 / 0")
        self.lbl_page_info.setAlignment(Qt.AlignCenter)

        self.btn_next_page = QPushButton("▶")
        self.btn_next_page.setProperty("class", "tool-btn")
        self.btn_next_page.clicked.connect(self.next_page)

        bottom_layout.addWidget(self.btn_prev_page)
        bottom_layout.addWidget(self.lbl_page_info)
        bottom_layout.addWidget(self.btn_next_page)

        bottom_layout.addSpacing(12)

        # Zoom
        self.btn_zoom_out = QPushButton("🔍 -")
        self.btn_zoom_out.setProperty("class", "tool-btn")
        self.btn_zoom_out.clicked.connect(self.zoom_out)

        self.btn_zoom_fit = QPushButton("📐 Fit")
        self.btn_zoom_fit.setProperty("class", "tool-btn")
        self.btn_zoom_fit.clicked.connect(self.reset_zoom_to_fit)

        self.btn_zoom_in = QPushButton("🔍 +")
        self.btn_zoom_in.setProperty("class", "tool-btn")
        self.btn_zoom_in.clicked.connect(self.zoom_in)

        bottom_layout.addWidget(self.btn_zoom_out)
        bottom_layout.addWidget(self.btn_zoom_fit)
        bottom_layout.addWidget(self.btn_zoom_in)

        bottom_layout.addSpacing(12)

        # Modo Escuro
        self.btn_dark_mode = QPushButton("🌙 Escuro")
        self.btn_dark_mode.setProperty("class", "tool-btn")
        self.btn_dark_mode.setCheckable(True)
        self.btn_dark_mode.clicked.connect(self.toggle_dark_mode)
        bottom_layout.addWidget(self.btn_dark_mode)

        bottom_layout.addStretch()

        # Seleção de Cores para Grifo
        colors_config = [
            ("🟡", "#FFFF00", "1"),
            ("🟢", "#2ECC71", "2"),
            ("🔵", "#3498DB", "3"),
            ("🩷", "#E91E63", "4"),
        ]

        for icon_symbol, hex_code, key in colors_config:
            btn = QPushButton(icon_symbol)
            btn.setFixedSize(30, 30)
            btn.setToolTip(f"Cor: {hex_code} (Atalho: {key})")
            btn.clicked.connect(lambda _, c=hex_code: self.set_highlight_color(c))
            bottom_layout.addWidget(btn)
            self.color_buttons[hex_code] = btn

        self.update_color_button_styles()

        # Desfazer Grifo
        self.btn_undo_highlight = QPushButton("↩️")
        self.btn_undo_highlight.setProperty("class", "tool-btn")
        self.btn_undo_highlight.setToolTip("Desfazer Último Grifo")
        self.btn_undo_highlight.clicked.connect(self.undo_last_highlight)
        bottom_layout.addWidget(self.btn_undo_highlight)

        pdf_container_layout.addWidget(self.bottom_bar)
        main_layout.addWidget(pdf_container_widget, stretch=4)

        # 3. PAINEL DIREITO
        self.sidebar = QFrame()
        self.sidebar.setFixedWidth(300)
        self.sidebar.setStyleSheet("""
            QFrame#RightSidebar {
                background-color: #1E1E2E;
                border-left: 1px solid #313244;
            }
            QLabel { border: none; }
        """)
        self.sidebar.setObjectName("RightSidebar")
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(14, 14, 14, 14)
        sidebar_layout.setSpacing(12)
        
        # Info do Bloco
        self.lbl_info = QLabel("<b>Nenhum bloco selecionado</b>")
        self.lbl_info.setWordWrap(True)
        self.lbl_info.setStyleSheet("font-size: 13px; color: #BAC2DE;")
        sidebar_layout.addWidget(self.lbl_info)

        # Progresso
        self.block_progress = QProgressBar()
        self.block_progress.setStyleSheet("""
            QProgressBar {
                border: 1px solid #313244;
                border-radius: 6px;
                text-align: center;
                color: #CDD6F4;
                background-color: #181825;
                height: 18px;
                font-size: 11px;
                font-weight: bold;
            }
            QProgressBar::chunk {
                background-color: #89B4FA;
                border-radius: 5px;
            }
        """)
        sidebar_layout.addWidget(self.block_progress)

        # Cronômetro / Pomodoro Card
        timer_frame = QFrame()
        timer_frame.setStyleSheet("background-color: #181825; border: 1px solid #313244; border-radius: 8px; padding: 10px;")
        timer_layout = QVBoxLayout(timer_frame)
        timer_layout.setSpacing(6)
        
        lbl_timer_title = QLabel("TEMPO DEDICADO")
        lbl_timer_title.setStyleSheet("color: #A6ADC8; font-size: 11px; font-weight: bold;")
        lbl_timer_title.setAlignment(Qt.AlignCenter)
        timer_layout.addWidget(lbl_timer_title)

        # Seletor de Modo (Cronômetro / Pomodoro)
        mode_layout = QHBoxLayout()
        mode_layout.setSpacing(6)

        self.cmb_timer_mode = QComboBox()
        self.cmb_timer_mode.addItems(["⏱️ Cronômetro Livre", f"🍅 Pomodoro ({int(self.work_duration/60)}m)"])
        self.cmb_timer_mode.setStyleSheet("""
            QComboBox {
                background-color: #1E1E2E;
                color: #CDD6F4;
                border: 1px solid #313244;
                border-radius: 5px;
                padding: 4px;
                font-size: 12px;
            }
            QComboBox QAbstractItemView {
                background-color: #181825;
                color: #CDD6F4;
                selection-background-color: #313244;
            }
        """)
        self.cmb_timer_mode.currentIndexChanged.connect(self.on_timer_mode_changed)
        mode_layout.addWidget(self.cmb_timer_mode, stretch=1)

        # Botão para abrir o Modal
        self.btn_pomodoro_settings = QPushButton("⚙️")
        self.btn_pomodoro_settings.setFixedSize(28, 28)
        self.btn_pomodoro_settings.setToolTip("Configurar tempos do Pomodoro")
        self.btn_pomodoro_settings.setStyleSheet("""
            QPushButton {
                background-color: #1E1E2E;
                color: #CDD6F4;
                border: 1px solid #313244;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #313244;
            }
        """)
        self.btn_pomodoro_settings.clicked.connect(self.open_pomodoro_settings)
        mode_layout.addWidget(self.btn_pomodoro_settings)

        timer_layout.addLayout(mode_layout)

        self.lbl_timer = QLabel("00:00:00")
        self.lbl_timer.setStyleSheet("font-size: 26px; font-weight: bold; color: #A6E3A1; border: none;")
        self.lbl_timer.setAlignment(Qt.AlignCenter)
        timer_layout.addWidget(self.lbl_timer)

        btn_timer_layout = QHBoxLayout()
        
        self.btn_start_timer = QPushButton("▶ Iniciar")
        self.btn_start_timer.setStyleSheet("""
            QPushButton { background-color: #2D4F3E; color: #A6E3A1; border: 1px solid #A6E3A1; border-radius: 5px; padding: 6px; font-weight: bold; }
            QPushButton:hover { background-color: #3A6650; }
        """)
        self.btn_start_timer.clicked.connect(self.start_timer)
        btn_timer_layout.addWidget(self.btn_start_timer)

        self.btn_pause_timer = QPushButton("⏸ Pausar")
        self.btn_pause_timer.setStyleSheet("""
            QPushButton { background-color: #523D26; color: #F9E2AF; border: 1px solid #F9E2AF; border-radius: 5px; padding: 6px; font-weight: bold; }
            QPushButton:hover { background-color: #6B5032; }
        """)
        self.btn_pause_timer.clicked.connect(self.pause_timer)
        btn_timer_layout.addWidget(self.btn_pause_timer)

        timer_layout.addLayout(btn_timer_layout)

        self.btn_reset_timer = QPushButton("⏹ Reiniciar Timer")
        self.btn_reset_timer.setStyleSheet("""
            QPushButton { background-color: transparent; color: #F38BA8; border: none; font-size: 11px; margin-top: 4px; }
            QPushButton:hover { text-decoration: underline; }
        """)
        self.btn_reset_timer.clicked.connect(self.reset_timer)
        timer_layout.addWidget(self.btn_reset_timer)

        sidebar_layout.addWidget(timer_frame)

        # Campo de Anotações
        lbl_notes_title = QLabel("<b>📝 Anotações da Página</b>")
        lbl_notes_title.setStyleSheet("font-size: 13px; color: #CDD6F4;")
        sidebar_layout.addWidget(lbl_notes_title)

        self.txt_notes = QTextEdit()
        self.txt_notes.setPlaceholderText("Escreva aqui suas anotações...")
        self.txt_notes.setStyleSheet("""
            QTextEdit {
                background-color: #181825;
                color: #CDD6F4;
                border: 1px solid #313244;
                border-radius: 6px;
                padding: 8px;
                font-size: 13px;
            }
            QTextEdit:focus {
                border-color: #89B4FA;
            }
        """)
        self.txt_notes.textChanged.connect(self.save_notes)
        sidebar_layout.addWidget(self.txt_notes)

        # Ações do Bloco
        self.btn_save_pause = QPushButton("💾 Pausar e Voltar")
        self.btn_save_pause.setStyleSheet("""
            QPushButton {
                background-color: #89B4FA; 
                color: #11111B; 
                font-size: 13px; 
                font-weight: bold; 
                padding: 10px;
                border-radius: 6px;
                border: none;
            }
            QPushButton:hover { background-color: #B4BEFE; }
        """)
        self.btn_save_pause.clicked.connect(self.save_and_pause)
        sidebar_layout.addWidget(self.btn_save_pause)

        self.btn_complete_block = QPushButton("✅ Concluir Bloco")
        self.btn_complete_block.setStyleSheet("""
            QPushButton {
                background-color: #A6E3A1; 
                color: #11111B; 
                font-size: 13px; 
                font-weight: bold; 
                padding: 10px;
                border-radius: 6px;
                border: none;
            }
            QPushButton:hover { background-color: #94E2D5; }
        """)
        self.btn_complete_block.clicked.connect(self.complete_block)
        sidebar_layout.addWidget(self.btn_complete_block)

        main_layout.addWidget(self.sidebar, stretch=0)
        outer_layout.addLayout(main_layout)
    
    def toggle_left_sidebar(self):
        if hasattr(self, 'left_sidebar'):
            is_visible = not self.left_sidebar.isVisible()
            self.left_sidebar.setVisible(is_visible)

    def go_to_page_from_toc(self, page_num_1based: int):
        """Navega para a página clicada no Sumário."""
        if 1 <= page_num_1based <= self.total_pages:
            self.save_notes()
            self.current_page = page_num_1based - 1
            self.render_page()
            self.scroll_area.verticalScrollBar().setValue(0)
            self.save_current_page()
            self.check_block_completion()

    def open_pomodoro_settings(self):
        work_min = int(self.work_duration / 60)
        short_min = int(self.short_break / 60)
        long_min = int(self.long_break / 60)

        dialog = PomodoroSettingsDialog(work_min, short_min, long_min, parent=self)
        if dialog.exec() == QDialog.Accepted:
            new_work, new_short, new_long = dialog.get_values()
            
            # Atualiza os valores em segundos
            self.work_duration = new_work * 60
            self.short_break = new_short * 60
            self.long_break = new_long * 60

            # Atualiza o texto do item no ComboBox sem disparar o evento de mudança
            self.cmb_timer_mode.blockSignals(True)
            self.cmb_timer_mode.setItemText(1, f"🍅 Pomodoro ({new_work}m)")
            self.cmb_timer_mode.blockSignals(False)

            # Se o modo atual for Pomodoro e o temporizador estiver parado, atualiza a contagem
            if self.timer_mode == "POMODORO" and not self.timer.isActive():
                if self.pomodoro_state == "WORK":
                    self.pomodoro_remaining = self.work_duration
                elif self.pomodoro_state == "BREAK":
                    self.pomodoro_remaining = self.short_break
                elif self.pomodoro_state == "LONG_BREAK":
                    self.pomodoro_remaining = self.long_break
                
                self.refresh_timer_display()

            QMessageBox.information(
                self, 
                "Configurações Salvas", 
                f"Novos tempos salvos:\n• Foco: {new_work} min\n• Pausa Curta: {new_short} min\n• Pausa Longa: {new_long} min"
            )

    # --- LÓGICA DE GERENCIAMENTO DE TIMER E POMODORO ---
    def on_timer_mode_changed(self, index):
        self.pause_timer()
        
        if index == 0:
            self.timer_mode = "STOPWATCH"
            self.lbl_timer.setStyleSheet("font-size: 26px; font-weight: bold; color: #A6E3A1; border: none;")
        else:
            self.timer_mode = "POMODORO"
            self.pomodoro_state = "WORK"
            self.pomodoro_remaining = self.work_duration
            self.lbl_timer.setStyleSheet("font-size: 26px; font-weight: bold; color: #89B4FA; border: none;")
            
        self.refresh_timer_display()

    def start_timer(self):
        if not self.timer.isActive():
            self.timer.start(1000)

        if self.block_id:
            db = SessionLocal()
            try:
                block = db.query(StudyBlock).filter(StudyBlock.id == self.block_id).first()
                if block and block.status == BlockStatus.PENDENTE:
                    block.status = BlockStatus.EM_ANDAMENTO
                    self.block_status = BlockStatus.EM_ANDAMENTO
                    if not block.started_at:
                        block.started_at = datetime.now(timezone.utc)
                    db.commit()
            except Exception as e:
                db.rollback()
                print(f"Erro ao iniciar bloco: {e}")
            finally:
                db.close()

    def update_timer(self):
        if self.timer_mode == "STOPWATCH":
            self.elapsed_seconds += 1
            self.refresh_timer_display()
            
        elif self.timer_mode == "POMODORO":
            if self.pomodoro_remaining > 0:
                self.pomodoro_remaining -= 1
                
                # Apenas acumula tempo de estudo REAL no banco se estiver na fase de foco
                if self.pomodoro_state == "WORK":
                    self.elapsed_seconds += 1
                    
                self.refresh_timer_display()
            else:
                self.handle_pomodoro_completion()

    def refresh_timer_display(self):
        if self.timer_mode == "STOPWATCH":
            time_str = QTime(0, 0, 0).addSecs(self.elapsed_seconds).toString("hh:mm:ss")
            self.lbl_timer.setText(time_str)
            if hasattr(self, 'lbl_header_timer'):
                self.lbl_header_timer.setText(f"⏱️ {time_str}")
                
        elif self.timer_mode == "POMODORO":
            time_str = QTime(0, 0, 0).addSecs(self.pomodoro_remaining).toString("mm:ss")
            icon = "🍅" if self.pomodoro_state == "WORK" else "☕"
            
            self.lbl_timer.setText(time_str)
            if hasattr(self, 'lbl_header_timer'):
                self.lbl_header_timer.setText(f"{icon} {time_str}")

    def handle_pomodoro_completion(self):
        self.timer.stop()
        
        if self.alarm_sound.source().isValid():
            self.alarm_sound.play()

        if self.pomodoro_state == "WORK":
            self.pomodoros_completed += 1
            if self.pomodoros_completed % 4 == 0:
                self.pomodoro_state = "LONG_BREAK"
                self.pomodoro_remaining = self.long_break
                msg = f"<b>Hora de uma Pausa Longa! 🎉</b><br>Você concluiu 4 ciclos de foco. Relaxe {int(self.long_break/60)} minutos."
            else:
                self.pomodoro_state = "BREAK"
                self.pomodoro_remaining = self.short_break
                msg = f"<b>Hora do Descanso! ☕</b><br>Pausa curta de {int(self.short_break/60)} minutos. Levante e tome uma água."
                
            self.lbl_timer.setStyleSheet("font-size: 26px; font-weight: bold; color: #F8BD96; border: none;")
        else:
            self.pomodoro_state = "WORK"
            self.pomodoro_remaining = self.work_duration
            msg = f"<b>Pausa encerrada! 💪</b><br>Pronto para voltar ao foco de {int(self.work_duration/60)} minutos?"
            self.lbl_timer.setStyleSheet("font-size: 26px; font-weight: bold; color: #89B4FA; border: none;")

        self.refresh_timer_display()
        QMessageBox.information(self, "Pomodoro", msg)
        self.timer.start(1000)

    def pause_timer(self):
        self.timer.stop()

    def reset_timer(self, confirm=True):
        if confirm:
            reply = QMessageBox.question(
                self, 
                "Reiniciar Timer", 
                "Deseja reiniciar a contagem atual?",
                QMessageBox.Yes | QMessageBox.No, 
                QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return

        self.timer.stop()
        if self.timer_mode == "STOPWATCH":
            self.elapsed_seconds = 0
        else:
            self.pomodoro_state = "WORK"
            self.pomodoro_remaining = self.work_duration
            self.lbl_timer.setStyleSheet("font-size: 26px; font-weight: bold; color: #89B4FA; border: none;")
            
        self.refresh_timer_display()

    # --- NAVEGAÇÃO E MODOS DA INTERFACE ---
    def toggle_focus_mode(self):
        top_window = self.window()
        if self.is_focus_mode:
            self.exit_focus_mode()
        else:
            self.is_focus_mode = True
            if top_window:
                top_window.showFullScreen()
            
            self.header_widget.setVisible(False)
            self.sidebar.setVisible(False)
            self.bottom_bar.setVisible(False)
            
            if self.auto_fit_width:
                self.render_page()

    def exit_focus_mode(self):
        if not self.is_focus_mode:
            return

        self.is_focus_mode = False
        top_window = self.window()
        if top_window:
            top_window.showNormal()

        self.header_widget.setVisible(True)
        self.sidebar.setVisible(True)
        self.bottom_bar.setVisible(True)
        self.lbl_header_timer.setVisible(False)

        if self.auto_fit_width:
            self.render_page()

    def toggle_dark_mode(self):
        self.dark_mode = self.btn_dark_mode.isChecked()
        self.render_page()

    def set_highlight_color(self, hex_code: str):
        self.selected_color = hex_code
        self.lbl_pdf_page.set_selection_color(hex_code)
        self.update_color_button_styles()

    def update_color_button_styles(self):
        for hex_code, btn in self.color_buttons.items():
            if hex_code == self.selected_color:
                btn.setStyleSheet(f"border: 2px solid white; background-color: {hex_code}; border-radius: 15px;")
            else:
                btn.setStyleSheet(f"border: 1px solid #313244; background-color: {hex_code}; border-radius: 15px;")

    def hex_to_rgb_tuple(self, hex_str: str):
        if not hex_str:
            return (1.0, 1.0, 0.0)
        hex_str = hex_str.lstrip('#')
        if len(hex_str) != 6:
            return (1.0, 1.0, 0.0)
        return tuple(int(hex_str[i:i+2], 16) / 255.0 for i in (0, 2, 4))

    def toggle_right_sidebar(self):
        if hasattr(self, 'sidebar'):
            is_visible = not self.sidebar.isVisible()
            self.sidebar.setVisible(is_visible)
            
            if hasattr(self, 'lbl_header_timer'):
                self.lbl_header_timer.setVisible(not is_visible)

    def handle_point_clicked(self, point: QPoint):
        if not self.doc or not self.current_pdf_id or self.current_page < 0:
            return

        zoom = self.zoom_factor if self.zoom_factor > 0 else 1.0
        pdf_x = point.x() / zoom
        pdf_y = point.y() / zoom

        db = SessionLocal()
        try:
            highlights = StudyManager.get_highlights_by_pdf(
                db=db,
                pdf_id=self.current_pdf_id,
                page_number=self.current_page + 1
            )

            page = self.doc[self.current_page]

            for hl in highlights:
                hit = False
                if all(getattr(hl, attr, None) is not None for attr in ['x', 'y', 'width', 'height']):
                    rect = fitz.Rect(hl.x, hl.y, hl.x + hl.width, hl.y + hl.height)
                    if rect.contains(fitz.Point(pdf_x, pdf_y)):
                        hit = True
                elif hl.selected_text:
                    matches = page.search_for(hl.selected_text)
                    for rect in matches:
                        if rect.contains(fitz.Point(pdf_x, pdf_y)):
                            hit = True
                            break

                if hit:
                    db.delete(hl)
                    db.commit()
                    self.render_page()
                    break
        except Exception as e:
            print(f"Erro ao remover grifo selecionado: {e}")
        finally:
            db.close()

    def save_notes(self):
        db = SessionLocal()
        try:
            target_block_id = self.get_current_active_block_id(db)
            if not target_block_id:
                return

            from sqlalchemy.orm import joinedload
            block = db.query(StudyBlock).options(joinedload(StudyBlock.topic)).filter(StudyBlock.id == target_block_id).first()
            if not block:
                return

            current_page_num = self.current_page + 1
            novo_texto = self.txt_notes.toPlainText()

            note = db.query(Note).filter(
                Note.block_id == target_block_id,
                Note.page_number == current_page_num
            ).first()

            if note:
                note.content = novo_texto
            else:
                if novo_texto.strip():
                    nova_nota = Note(
                        pdf_id=block.topic.pdf_id,
                        page_number=current_page_num,
                        content=novo_texto,
                        block_id=block.id
                    )
                    db.add(nova_nota)

            db.commit()
        except Exception as e:
            db.rollback()
            print(f"Erro ao salvar anotações do bloco: {e}")
        finally:
            db.close()

    def get_zoom_matrix(self, page):
        if self.auto_fit_width:
            viewport_w = self.scroll_area.viewport().width()
            page_width = page.rect.width
            target_width = max(400, viewport_w - 30) if viewport_w > 30 else 400
            scale = target_width / page_width if page_width > 0 else 1.0
            self.zoom_factor = scale
        else:
            scale = self.zoom_factor

        return fitz.Matrix(scale, scale)

    def zoom_in(self):
        self.auto_fit_width = False
        self.zoom_factor *= 1.25
        self.render_page()

    def zoom_out(self):
        self.auto_fit_width = False
        self.zoom_factor /= 1.25
        self.render_page()

    def reset_zoom_to_fit(self):
        self.auto_fit_width = True
        self.render_page()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.doc and self.auto_fit_width:
            self.render_page()

    def unload_pdf(self):
        if self.doc:
            try:
                self.doc.close()
            except Exception:
                pass
            self.doc = None

        self.current_pdf_id = None
        self.block_id = None
        self.current_page = 0
        self.total_pages = 0
        self.lbl_pdf_page.setText("Nenhum PDF carregado.")
        self.lbl_page_info.setText("Pág: 0 / 0")
        self.lbl_info.setText("<b>Nenhum bloco selecionado</b>")
        self.lbl_header_title.setText("Leitor de Estudos")
        
        # --- LIMPEZA E OCULTAÇÃO DO SUMÁRIO (TOC) ---
        if hasattr(self, 'toc_tree'):
            self.toc_tree.clear()
        if hasattr(self, 'left_sidebar'):
            self.left_sidebar.setVisible(False)

        self.txt_notes.blockSignals(True)
        self.txt_notes.clear()
        self.txt_notes.blockSignals(False)

        self.current_pdf_id = None
        self.block_id = None
        self.current_page = 0
        self.total_pages = 0
        self.lbl_pdf_page.setText("Nenhum PDF carregado.")
        self.lbl_page_info.setText("Pág: 0 / 0")
        self.lbl_info.setText("<b>Nenhum bloco selecionado</b>")
        self.lbl_header_title.setText("Leitor de Estudos")
        
        self.txt_notes.blockSignals(True)
        self.txt_notes.clear()
        self.txt_notes.blockSignals(False)

    def load_block(self, block_id):
        self.unload_pdf()
        self.block_id = block_id
        self.reset_timer(confirm=False)
        
        db = SessionLocal()
        try:
            block = db.query(StudyBlock).filter(StudyBlock.id == block_id).first()
            if not block:
                return

            if block.status == BlockStatus.PENDENTE:
                block.status = BlockStatus.EM_ANDAMENTO
                if not block.started_at:
                    block.started_at = datetime.now(timezone.utc)

            topic = db.query(Topic).filter(Topic.id == block.topic_id).first()
            pdf_doc = db.query(PdfDocument).filter(PdfDocument.id == topic.pdf_id).first() if topic else None
            subject = db.query(Subject).filter(Subject.id == pdf_doc.subject_id).first() if pdf_doc else None

            subj_name = subject.name if subject else "Matéria"
            topic_title = topic.title if topic else "Tópico"
            
            self.page_start = getattr(block, 'page_start', 1)
            self.page_end = getattr(block, 'page_end', 1)
            self.block_status = block.status
            
            self.lbl_header_title.setText(f"{subj_name} — {topic_title}")

            self.lbl_info.setText(
                f"📖 <b>{subj_name}</b><br>"
                f"📌 {topic_title}<br><br>"
                f"<b>Meta:</b> Páginas {self.page_start} até {self.page_end}"
            )

            if pdf_doc and pdf_doc.file_path:
                self.current_pdf_id = pdf_doc.id
                self.doc = fitz.open(pdf_doc.file_path)
                self.total_pages = len(self.doc)

                # --- CARREGA O SUMÁRIO DO PDF ---
                toc = self.doc.get_toc()  # Retorna [[level, title, page], ...]
                if hasattr(self, 'toc_tree'):
                    self.toc_tree.load_toc(toc)
                
                saved_page = block.current_page if (block.current_page and block.current_page > 0) else self.page_start
                self.current_page = max(0, saved_page - 1)
                
                block.current_page = self.current_page + 1
                db.commit()

                self.render_page()
                self.load_current_page_notes()
                self.start_timer()
        except Exception as e:
            db.rollback()
            QMessageBox.critical(self, "Erro", f"Não foi possível abrir o PDF: {str(e)}")
        finally:
            db.close()

    def load_current_page_notes(self):
        db = SessionLocal()
        try:
            target_block_id = self.get_current_active_block_id(db)
            if not target_block_id:
                self.txt_notes.blockSignals(True)
                self.txt_notes.setPlainText("")
                self.txt_notes.blockSignals(False)
                return

            current_page_num = self.current_page + 1

            note = db.query(Note).filter(
                Note.block_id == target_block_id,
                Note.page_number == current_page_num
            ).first()

            text_content = note.content if (note and note.content) else ""

            self.txt_notes.blockSignals(True)
            self.txt_notes.setPlainText(text_content)
            self.txt_notes.blockSignals(False)
        except Exception as e:
            print(f"Erro ao carregar anotações da página: {e}")
        finally:
            db.close()

    def get_current_active_block_id(self, db):
        current_page_num = self.current_page + 1

        if hasattr(self, 'current_pdf_id') and self.current_pdf_id:
            block = (
                db.query(StudyBlock)
                .join(Topic)
                .filter(
                    Topic.pdf_id == self.current_pdf_id,
                    StudyBlock.page_start <= current_page_num,
                    StudyBlock.page_end >= current_page_num
                )
                .first()
            )
            if block:
                return block.id

        return self.block_id

    def render_page(self, page_num: int = None):
        if page_num is not None:
            self.current_page = page_num - 1 if page_num > 0 else page_num

        if not self.doc or self.current_page < 0 or self.current_page >= self.total_pages:
            return

        v_scroll = self.scroll_area.verticalScrollBar().value()
        h_scroll = self.scroll_area.horizontalScrollBar().value()

        page = self.doc.load_page(self.current_page)
        
        annot = page.first_annot
        while annot:
            next_annot = annot.next
            if annot.type[0] == 8:
                page.delete_annot(annot)
            annot = next_annot

        if self.current_pdf_id:
            db = SessionLocal()
            try:
                highlights = StudyManager.get_highlights_by_pdf(
                    db=db, 
                    pdf_id=self.current_pdf_id, 
                    page_number=self.current_page + 1
                )
                for hl in highlights:
                    color_hex = getattr(hl, 'color', '#FFFF00') or '#FFFF00'
                    color_rgb = self.hex_to_rgb_tuple(color_hex)

                    if all(getattr(hl, attr, None) is not None for attr in ['x', 'y', 'width', 'height']):
                        rect = fitz.Rect(hl.x, hl.y, hl.x + hl.width, hl.y + hl.height)
                        annot = page.add_highlight_annot(rect)
                        annot.set_colors(stroke=color_rgb)
                        annot.update()
                    elif hl.selected_text:
                        matches = page.search_for(hl.selected_text)
                        for rect in matches:
                            annot = page.add_highlight_annot(rect)
                            annot.set_colors(stroke=color_rgb)
                            annot.update()
            except Exception as e:
                print(f"Erro ao carregar grifos: {e}")
            finally:
                db.close()

        matrix = self.get_zoom_matrix(page)
        pix = page.get_pixmap(matrix=matrix)

        if self.dark_mode:
            inverted_samples = bytes([255 - b for b in pix.samples])
            qimg = QImage(inverted_samples, pix.width, pix.height, pix.stride, QImage.Format_RGB888).copy()
        else:
            qimg = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format_RGB888).copy()

        pixmap = QPixmap.fromImage(qimg)
        self.lbl_pdf_page.setPixmap(pixmap)
        
        self.scroll_area.verticalScrollBar().setValue(v_scroll)
        self.scroll_area.horizontalScrollBar().setValue(h_scroll)
        
        self.lbl_page_info.setText(f"Pág: {self.current_page + 1} / {self.total_pages}")
        self.load_current_page_notes()

        curr_1based = self.current_page + 1
        total_block_pages = max(1, (self.page_end - self.page_start + 1))
        pages_done = max(0, curr_1based - self.page_start + 1)
        pct = min(100, int((pages_done / total_block_pages) * 100))

        if hasattr(self, 'block_progress'):
            self.block_progress.setValue(max(0, pct))
    
    def closeEvent(self, event):
        self.exit_focus_mode()
        self.save_and_pause()
        self.unload_pdf()
        super().closeEvent(event)

    def undo_last_highlight(self):
        if not self.current_pdf_id:
            return

        db = SessionLocal()
        try:
            last_hl = db.query(Highlight).filter(
                Highlight.pdf_id == self.current_pdf_id,
                Highlight.page_number == self.current_page + 1
            ).order_by(Highlight.id.desc()).first()

            if last_hl:
                db.delete(last_hl)
                db.commit()
                self.render_page()
        except Exception as e:
            print(f"Erro ao desfazer grifo: {e}")
        finally:
            db.close()

    def handle_area_selected(self, rect):
        if not self.doc or self.current_page < 0:
            return

        page = self.doc[self.current_page]
        zoom = self.zoom_factor if self.zoom_factor > 0 else 1.0

        pdf_rect = fitz.Rect(
            rect.x() / zoom,
            rect.y() / zoom,
            (rect.x() + rect.width()) / zoom,
            (rect.y() + rect.height()) / zoom
        )

        words = page.get_text("words", clip=pdf_rect)
        if not words:
            return

        selected_text = " ".join([w[4] for w in words]).strip()
        if selected_text:
            self.on_text_selected_to_highlight(selected_text, pdf_rect)

    def on_text_selected_to_highlight(self, selected_text: str, pdf_rect=None):
        if not selected_text.strip() or not self.current_pdf_id:
            return

        db = SessionLocal()
        try:
            x = pdf_rect.x0 if pdf_rect else None
            y = pdf_rect.y0 if pdf_rect else None
            width = pdf_rect.width if pdf_rect else None
            height = pdf_rect.height if pdf_rect else None

            StudyManager.add_highlight(
                db=db,
                pdf_id=self.current_pdf_id,
                page_number=self.current_page + 1,
                selected_text=selected_text.strip(),
                color=self.selected_color,
                x=x,
                y=y,
                width=width,
                height=height
            )
            self.render_page()
        except Exception as e:
            print(f"Erro ao salvar highlight: {e}")
        finally:
            db.close()

    def save_current_page(self):
        if not self.block_id:
            return
        
        db = SessionLocal()
        try:
            block = db.query(StudyBlock).filter(StudyBlock.id == self.block_id).first()
            if block:
                block.current_page = self.current_page + 1
                if block.status == BlockStatus.PENDENTE:
                    block.status = BlockStatus.EM_ANDAMENTO
                db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()

    def prev_page(self):
        if self.current_page > 0:
            self.save_notes()
            self.current_page -= 1
            self.render_page()
            self.scroll_area.verticalScrollBar().setValue(0)
            self.save_current_page()

    def next_page(self):
        if self.current_page < self.total_pages - 1:
            self.save_notes()
            self.current_page += 1
            self.render_page()
            self.scroll_area.verticalScrollBar().setValue(0)
            self.save_current_page()
            self.check_block_completion()

    def check_block_completion(self):
        current_page_1based = self.current_page + 1
        
        if current_page_1based > self.page_end and self.block_status != BlockStatus.CONCLUIDO:
            self.save_notes()
            db = SessionLocal()
            try:
                block = db.query(StudyBlock).filter(StudyBlock.id == self.block_id).first()
                if block:
                    block.status = BlockStatus.CONCLUIDO
                    self.block_completed.emit()
                    block.current_page = self.page_end
                    block.completed_at = datetime.now(timezone.utc)
                    block.time_spent_seconds = (block.time_spent_seconds or 0) + self.elapsed_seconds
                    db.commit()
                    self.elapsed_seconds = 0
            except Exception as e:
                db.rollback()
                print(f"Erro ao salvar conclusão de bloco: {e}")
            finally:
                db.close()

            self.block_status = BlockStatus.CONCLUIDO
            self.pause_timer()

            if self.dont_show_completion_msg:
                self.load_next_sequential_block()
                return

            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Information)
            msg.setWindowTitle("Bloco Concluído! 🎉")
            msg.setText(
                "<b>Parabéns! Você concluiu este bloco de estudos.</b><br><br>"
                f"Faixa concluída: Páginas {self.page_start} até {self.page_end}.<br><br>"
                "Deseja continuar lendo o próximo bloco deste PDF ou voltar para o ciclo no Dashboard?"
            )
            
            cb_dont_show = QCheckBox("Não mostrar esta mensagem novamente durante a leitura")
            msg.setCheckBox(cb_dont_show)

            btn_continue = msg.addButton("Continuar Lendo", QMessageBox.AcceptRole)
            msg.addButton("Voltar ao Dashboard", QMessageBox.RejectRole)
            msg.exec()

            if cb_dont_show.isChecked():
                self.dont_show_completion_msg = True

            if msg.clickedButton() == btn_continue:
                self.load_next_sequential_block()
            else:
                self.back_requested.emit()

    def load_next_sequential_block(self):
        db = SessionLocal()
        try:
            # Pede ao StudyManager a próxima matéria/bloco recomendado no ciclo
            next_block = StudyManager.get_next_block_to_study(db)

            if next_block:
                next_id = next_block.id
                
                next_block.status = BlockStatus.EM_ANDAMENTO
                if not next_block.started_at:
                    next_block.started_at = datetime.now(timezone.utc)
                db.commit()
                db.close()

                # Carrega o próximo bloco recomendado (seja do mesmo PDF ou de outra matéria)
                self.load_block(next_id)
            else:
                db.close()
                QMessageBox.information(
                    self,
                    "Ciclo Concluído",
                    "Parabéns! Você concluiu todos os blocos do seu ciclo de estudos."
                )
                self.back_requested.emit()
        except Exception as e:
            if 'db' in locals():
                db.rollback()
                db.close()
            QMessageBox.critical(self, "Erro", f"Erro ao avançar bloco: {str(e)}")

    def save_and_pause(self):
        self.exit_focus_mode()
        self.pause_timer()
        self.save_current_page()
        self.save_notes()

        if self.block_id:
            db = SessionLocal()
            try:
                block = db.query(StudyBlock).filter(StudyBlock.id == self.block_id).first()
                if block:
                    if self.elapsed_seconds > 0:
                        block.time_spent_seconds = (block.time_spent_seconds or 0) + self.elapsed_seconds
                        self.elapsed_seconds = 0
                    
                    if block.status == BlockStatus.PENDENTE:
                        block.status = BlockStatus.EM_ANDAMENTO
                    
                    db.commit()
            except Exception as e:
                db.rollback()
                print(f"Erro ao salvar tempo de estudo: {e}")
            finally:
                db.close()

        self.back_requested.emit()

    def complete_block(self):
        self.exit_focus_mode()
        self.pause_timer()
        self.save_current_page()
        self.save_notes()

        db = SessionLocal()
        try:
            block = db.query(StudyBlock).filter(StudyBlock.id == self.block_id).first()
            if block:
                block.status = BlockStatus.CONCLUIDO
                block.completed_at = datetime.now(timezone.utc)
                block.time_spent_seconds = (block.time_spent_seconds or 0) + self.elapsed_seconds
                db.commit()
                self.elapsed_seconds = 0
                self.block_status = BlockStatus.CONCLUIDO
        except Exception as e:
            db.rollback()
            QMessageBox.critical(self, "Erro", f"Erro ao concluir o bloco: {e}")
            return
        finally:
            db.close()

        QMessageBox.information(self, "Sucesso", "Bloco marcado como concluído!")
        self.back_requested.emit()