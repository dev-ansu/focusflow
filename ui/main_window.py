from PySide6.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QStackedWidget, QMessageBox
from PySide6.QtCore import Qt

from ui.dashboard import DashboardView
from ui.subjects import SubjectView
from ui.pdf_import import PDFImportView
from ui.toc_review import TOCReviewView
from ui.study_session import StudySessionView
from ui.settings import SettingsView
from ui.reader import StudyReaderView

from services.toc_detector import TOCDetector
from services.topic_parser import TopicParser
from services.pdf_parser import PDFParser

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("EstudoFlow - Organização de Estudos")
        self.resize(1024, 700)

        self.import_queue = []
        self.current_import_subject_id = None
        self.total_imports = 0

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QHBoxLayout(main_widget)
        layout.setContentsMargins(0, 0, 0, 0)

        # -------------------------------------------------------------
        # 1. Menu Lateral Esquerdo (Sidebar Esquerda)
        # -------------------------------------------------------------
        self.sidebar_widget = QWidget()  # Envelopado em um QWidget para permitir .setVisible()
        sidebar_layout = QVBoxLayout(self.sidebar_widget)
        sidebar_layout.setAlignment(Qt.AlignTop)

        btn_dash = QPushButton("📊 Dashboard")
        btn_dash.clicked.connect(lambda: self.switch_view(0))
        
        btn_subj = QPushButton("📚 Matérias & Ciclo")
        btn_subj.clicked.connect(lambda: self.switch_view(1))

        btn_reader = QPushButton("📖 Leitor & Estudo")
        btn_reader.clicked.connect(lambda: self.switch_view(2))

        btn_import = QPushButton("📥 Importar PDF")
        btn_import.clicked.connect(lambda: self.switch_view(3))

        btn_settings = QPushButton("⚙️ Configurações")
        btn_settings.clicked.connect(lambda: self.switch_view(4))

        sidebar_layout.addWidget(btn_dash)
        sidebar_layout.addWidget(btn_subj)
        sidebar_layout.addWidget(btn_reader)
        sidebar_layout.addWidget(btn_import)
        sidebar_layout.addWidget(btn_settings)

        layout.addWidget(self.sidebar_widget, stretch=0)

        # -------------------------------------------------------------
        # 2. Central Stacked Views (Pilha de Telas)
        # -------------------------------------------------------------
        self.stack = QStackedWidget()
        
        self.dash_view = DashboardView()
        self.dash_view.start_study_signal.connect(self.open_study_session)

        self.subj_view = SubjectView()
        self.reader_view = StudyReaderView()

        # Conecta o sinal do leitor para alternar/esconder a sidebar esquerda
        if hasattr(self.reader_view, 'toggle_left_sidebar_requested'):
            self.reader_view.toggle_left_sidebar_requested.connect(self.toggle_left_sidebar)

        self.reader_view.back_requested.connect(lambda: self.switch_view(0))

        self.import_view = PDFImportView()
        self.import_view.import_requested.connect(self.handle_import)
        self.settings_view = SettingsView()

        self.stack.addWidget(self.dash_view)      # Index 0
        self.stack.addWidget(self.subj_view)      # Index 1
        self.stack.addWidget(self.reader_view)    # Index 2
        self.stack.addWidget(self.import_view)    # Index 3
        self.stack.addWidget(self.settings_view)  # Index 4
        
        layout.addWidget(self.stack, stretch=1)
        
        self.settings_view.app_reset.connect(self.handle_app_reset)

    def toggle_left_sidebar(self):
        """Alterna a visibilidade do menu principal esquerdo."""
        is_visible = self.sidebar_widget.isVisible()
        self.sidebar_widget.setVisible(not is_visible)

    def switch_view(self, index: int):
        # Garante que ao sair do leitor, o menu esquerdo volte a ficar visível
        if index != 2:
            self.sidebar_widget.setVisible(True)

        if index == 0:
            self.dash_view.refresh()
        elif index == 1:
            self.subj_view.refresh()
        self.stack.setCurrentIndex(index)

    def handle_app_reset(self):
        if hasattr(self, 'reader_view'):
            self.reader_view.unload_pdf()
        self.switch_view(0)

    def handle_import(self, file_paths: list, subject_id: int):
        self.import_queue = file_paths.copy()
        self.current_import_subject_id = subject_id
        self.total_imports = len(file_paths)
        self.process_next_pdf_in_queue()

    def process_next_pdf_in_queue(self):
        if not self.import_queue:
            QMessageBox.information(
                self, 
                "Importação Concluída", 
                f"Todos os {self.total_imports} PDF(s) foram processados e importados com sucesso!"
            )
            self.switch_view(0)
            return

        file_path = self.import_queue.pop(0)
        current_index = self.total_imports - len(self.import_queue)

        info = PDFParser.get_info(file_path)
        toc_pages, confidence = TOCDetector.detect_toc_pages(file_path)
        
        topics = []
        if toc_pages:
            topics = TopicParser.parse_toc(file_path, toc_pages, info["pages"])

        review_view = TOCReviewView(file_path, self.current_import_subject_id, topics)
        
        if hasattr(review_view, 'set_progress_info'):
            review_view.set_progress_info(current_index, self.total_imports)

        review_view.completed.connect(self.process_next_pdf_in_queue)
        
        self.stack.addWidget(review_view)
        self.stack.setCurrentWidget(review_view)

    def open_study_session(self, block_id: int):
        self.reader_view.load_block(block_id)
        self.switch_view(2)