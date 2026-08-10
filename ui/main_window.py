from PySide6.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QStackedWidget, QMessageBox
from PySide6.QtCore import Qt

from ui.dashboard import DashboardView
from ui.subjects import SubjectView
from ui.pdf_import import PDFImportView
from ui.toc_review import TOCReviewView
from ui.study_session import StudySessionView
from ui.settings import SettingsView
from ui.reader import StudyReaderView  # Importação do Leitor de PDF

from services.toc_detector import TOCDetector
from services.topic_parser import TopicParser
from services.pdf_parser import PDFParser

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("EstudoFlow - Organização de Estudos")
        self.resize(1024, 700)

        # Controle da Fila de Importação em Lote
        self.import_queue = []
        self.current_import_subject_id = None
        self.total_imports = 0

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QHBoxLayout(main_widget)

        # 1. Menu Lateral (Sidebar)
        sidebar = QVBoxLayout()
        sidebar.setAlignment(Qt.AlignTop)

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

        sidebar.addWidget(btn_dash)
        sidebar.addWidget(btn_subj)
        sidebar.addWidget(btn_reader)
        sidebar.addWidget(btn_import)
        sidebar.addWidget(btn_settings)

        layout.addLayout(sidebar, stretch=1)

        # 2. Central Stacked Views (Pilha de Telas)
        self.stack = QStackedWidget()
        
        self.dash_view = DashboardView()
        self.dash_view.start_study_signal.connect(self.open_study_session)

        self.subj_view = SubjectView()
        self.reader_view = StudyReaderView()

        # Conecta o sinal do leitor para voltar ao Dashboard (Índice 0)
        self.reader_view.back_requested.connect(lambda: self.switch_view(0))

        self.import_view = PDFImportView()
        self.import_view.import_requested.connect(self.handle_import)
        self.settings_view = SettingsView()

        # Adiciona na ordem dos índices do menu lateral
        self.stack.addWidget(self.dash_view)      # Index 0
        self.stack.addWidget(self.subj_view)      # Index 1
        self.stack.addWidget(self.reader_view)    # Index 2
        self.stack.addWidget(self.import_view)    # Index 3
        self.stack.addWidget(self.settings_view)  # Index 4
        layout.addWidget(self.stack, stretch=4)
        
        self.settings_view.app_reset.connect(self.handle_app_reset)

    def handle_app_reset(self):
        """Executado imediatamente quando o usuário reseta o banco."""
        # Unload do leitor de PDF
        if hasattr(self, 'reader_view'):
            self.reader_view.unload_pdf()
        
        # Redireciona para o Dashboard (Índice 0)
        self.switch_view(0)

    def switch_view(self, index: int):
        if index == 0:
            self.dash_view.refresh()
        elif index == 1:
            self.subj_view.refresh()
        self.stack.setCurrentIndex(index)

    def handle_import(self, file_paths: list, subject_id: int):
        """Recebe a lista de caminhos de PDFs e inicia o processamento em lote."""
        self.import_queue = file_paths.copy()
        self.current_import_subject_id = subject_id
        self.total_imports = len(file_paths)
        
        # Inicia a fila
        self.process_next_pdf_in_queue()

    def process_next_pdf_in_queue(self):
        """Processa um PDF por vez na fila. Quando a fila esvazia, retorna ao Dashboard."""
        if not self.import_queue:
            QMessageBox.information(
                self, 
                "Importação Concluída", 
                f"Todos os {self.total_imports} PDF(s) foram processados e importados com sucesso!"
            )
            self.switch_view(0)  # Volta para o Dashboard
            return

        # Retira o próximo arquivo PDF (string) da lista
        file_path = self.import_queue.pop(0)
        current_index = self.total_imports - len(self.import_queue)

        # Extrai as informações e o sumário do PDF atual
        info = PDFParser.get_info(file_path)
        toc_pages, confidence = TOCDetector.detect_toc_pages(file_path)
        
        topics = []
        if toc_pages:
            topics = TopicParser.parse_toc(file_path, toc_pages, info["pages"])

        # Instancia a tela de revisão para o PDF atual
        review_view = TOCReviewView(file_path, self.current_import_subject_id, topics)
        
        # Se a TOCReviewView implementar indicação de progresso, atualiza o cabeçalho
        if hasattr(review_view, 'set_progress_info'):
            review_view.set_progress_info(current_index, self.total_imports)

        # Quando o usuário confirmar a revisão deste PDF, processa o próximo da fila
        review_view.completed.connect(self.process_next_pdf_in_queue)
        
        self.stack.addWidget(review_view)
        self.stack.setCurrentWidget(review_view)

    def open_study_session(self, block_id: int):
        # Carrega o bloco no leitor antes de exibir a tela
        self.reader_view.load_block(block_id)
        self.switch_view(2)  # Muda para o índice do leitor