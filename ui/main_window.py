from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, 
    QPushButton, QStackedWidget, QMessageBox, QDialog, QProgressDialog, QLabel, QSpacerItem, QSizePolicy
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QShortcut, QKeySequence

from ui.dashboard import DashboardView
from ui.subjects import SubjectView
from ui.pdf_import import PDFImportView
from ui.toc_review import TOCReviewView
from ui.settings import SettingsView
from ui.reader import StudyReaderView
from ui.global_search_dialog import GlobalSearchDialog
from ui.error_notebook import ErrorNotebookView

from services.toc_detector import TOCDetector
from services.topic_parser import TopicParser
from services.pdf_parser import PDFParser
from config.app import config
from database.connection import SessionLocal
from services.gdrive_sync import GDriveSyncService
from database.connection import engine 


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.gdrive_service = GDriveSyncService()
        
        self.setWindowTitle(f"{config.APP_NAME} - {config.APP_VERSION}")
        self.setMinimumSize(1024, 600)
        self.showMaximized()
        self.resize(1100, 720)
        self.is_returning_to_import = False

        # --- CONTROLE DA FILA E ACÚMULO EM MEMÓRIA ---
        self.import_queue = []            # Lista com todos os file_paths a importar
        self.batch_staged_data = {}       # Guarda o estado/rascunho de cada índice: {index: dict_dados}
        self.current_import_index = 0      # Índice atual na fila (0-indexed)
        self.current_import_subject_id = None

        main_widget = QWidget()
        main_widget.setStyleSheet(""" 
            QWidget#MainWidget{
                background-color: #1E1E2E;
            }    
        """)

        self.setCentralWidget(main_widget)
        layout = QHBoxLayout(main_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # -------------------------------------------------------------
        # 1. Menu Lateral Esquerdo (Sidebar Modernizada)
        # -------------------------------------------------------------
        self.sidebar_widget = QWidget()
        self.sidebar_widget.setFixedWidth(220)
        
        self.sidebar_widget.setStyleSheet("""
            QWidget#SidebarWidget {
                background-color: #1E1E2E;
                border-right: 1px solid #2D2D3F;
            }
            QLabel#AppTitle {
                color: #FFFFFF;
                font-size: 18px;
                font-weight: bold;
                padding: 15px 10px 5px 10px;
            }
            QPushButton.nav-btn {
                background-color: transparent;
                color: #A6ADC8;
                border: none;
                border-radius: 8px;
                text-align: left;
                padding: 12px 16px;
                font-size: 14px;
                font-weight: 500;
            }
            QPushButton.nav-btn:hover {
                background-color: #313244;
                color: #CDD6F4;
            }
            QPushButton.nav-btn:checked {
                background-color: #45475A;
                color: #89B4FA;
                font-weight: bold;
            }
            QPushButton#btn_search {
                background-color: #89B4FA;
                color: #11111B;
                border: none;
                border-radius: 8px;
                padding: 10px 14px;
                font-size: 13px;
                font-weight: bold;
                text-align: center;
            }
            QPushButton#btn_search:hover {
                background-color: #B4BEFE;
            }
        """)
        self.sidebar_widget.setObjectName("SidebarWidget")

        sidebar_layout = QVBoxLayout(self.sidebar_widget)
        sidebar_layout.setContentsMargins(12, 12, 12, 12)
        sidebar_layout.setSpacing(8)

        lbl_title = QLabel("📚 " f"{config.APP_NAME}")
        lbl_title.setObjectName("AppTitle")
        sidebar_layout.addWidget(lbl_title)
        sidebar_layout.addSpacing(10)

        self.nav_buttons = []

        btn_dash = QPushButton("📊  Dashboard")
        btn_subj = QPushButton("📚  Matérias e Ciclo")
        btn_reader = QPushButton("📖  Leitor e Estudo")
        btn_errors = QPushButton("🏷️  Caderno de Erros")
        btn_import = QPushButton("📥  Importar PDF")
        btn_settings = QPushButton("⚙️  Configurações")

        all_buttons = [btn_dash, btn_subj, btn_reader, btn_errors, btn_import, btn_settings]

        for idx, btn in enumerate(all_buttons):
            btn.setProperty("class", "nav-btn")
            btn.setCheckable(True)
            btn.clicked.connect(lambda _, i=idx: self.switch_view(i))
            sidebar_layout.addWidget(btn)
            self.nav_buttons.append(btn)

        sidebar_layout.addSpacerItem(
            QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)
        )

        btn_global_search = QPushButton("🔍 Busca Global (Ctrl+F)")
        btn_global_search.setObjectName("btn_search")
        btn_global_search.clicked.connect(self.open_global_search)
        sidebar_layout.addWidget(btn_global_search)

        layout.addWidget(self.sidebar_widget, stretch=0)

        self.shortcut_search = QShortcut(QKeySequence("Ctrl+F"), self)
        self.shortcut_search.activated.connect(self.open_global_search)

        # -------------------------------------------------------------
        # 2. Pilha de Telas (QStackedWidget)
        # -------------------------------------------------------------
        self.stack = QStackedWidget()

        # Instanciação das Telas
        self.dash_view = DashboardView()
        self.subj_view = SubjectView()
        self.reader_view = StudyReaderView()
        self.errors_view = ErrorNotebookView()
        self.import_view = PDFImportView()
        self.settings_view = SettingsView()

        # Conexão de Sinais
        self.dash_view.start_study_signal.connect(self.open_study_session)
        self.subj_view.start_study_signal.connect(self.open_study_session)
        
        self.reader_view.back_requested.connect(self.on_reader_back)
        self.reader_view.block_completed.connect(self.dash_view.refresh)

        self.toc_review_view = None

        if hasattr(self.reader_view, 'toggle_left_sidebar_requested'):
            self.reader_view.toggle_left_sidebar_requested.connect(self.toggle_left_sidebar)

        self.import_view.import_requested.connect(self.handle_import)
        self.settings_view.app_reset.connect(self.handle_app_reset)

        # Adiciona na ordem dos Índices do Menu
        self.stack.addWidget(self.dash_view)      # Index 0
        self.stack.addWidget(self.subj_view)      # Index 1
        self.stack.addWidget(self.reader_view)    # Index 2
        self.stack.addWidget(self.errors_view)    # Index 3
        self.stack.addWidget(self.import_view)    # Index 4
        self.stack.addWidget(self.settings_view)  # Index 5

        layout.addWidget(self.stack, stretch=1)
        
        self.switch_view(0)

    # -------------------------------------------------------------
    # NAVEGAÇÃO E GERENCIAMENTO DA IMPORTAÇÃO EM LOTE
    # -------------------------------------------------------------
    def handle_import(self, file_paths: list, subject_id: int):
        """Inicia a sequência de revisão guardando a fila."""
        self.import_queue = file_paths.copy()
        self.current_import_subject_id = subject_id
        self.batch_staged_data.clear()
        self.current_import_index = 0
        
        self.render_current_toc_review()

    def render_current_toc_review(self):
        """Cria e exibe a view de revisão para o PDF do índice atual."""
        file_path = self.import_queue[self.current_import_index]
        total_files = len(self.import_queue)

        # Se já tivermos editado e avançado/voltado antes, reusamos os tópicos guardados em memória
        if self.current_import_index in self.batch_staged_data:
            detected_topics = self.batch_staged_data[self.current_import_index]["topics"]
        else:
            info = PDFParser.get_info(file_path)
            toc_pages, confidence = TOCDetector.detect_toc_pages(file_path)
            detected_topics = []
            if toc_pages:
                detected_topics = TopicParser.parse_toc(file_path, toc_pages, info["pages"])

        # Instancia a view
        self.toc_review_view = TOCReviewView(file_path, self.current_import_subject_id, detected_topics)
        self.toc_review_view.set_progress_info(self.current_import_index + 1, total_files)

        # Conecta os sinais de transição sem persistência imediata
        self.toc_review_view.next_requested.connect(self.on_toc_next_requested)
        self.toc_review_view.prev_requested.connect(self.on_toc_prev_requested)
        self.toc_review_view.back_requested.connect(self.show_pdf_import_view)

        self.stack.addWidget(self.toc_review_view)
        self.stack.setCurrentWidget(self.toc_review_view)

    def on_toc_next_requested(self, staged_data: dict):
        """Guarda as alterações em memória e avança para o próximo PDF ou finaliza o lote."""
        # Armazena o estado atual do PDF em memória
        self.batch_staged_data[self.current_import_index] = staged_data

        if self.current_import_index < len(self.import_queue) - 1:
            # Avança para o próximo PDF
            self.current_import_index += 1
            self.render_current_toc_review()
        else:
            # Chegou ao último PDF: Persiste TODO o lote de uma vez no banco
            self.finalize_batch_import()

    def on_toc_prev_requested(self):
        """Volta para o PDF anterior mantendo as alterações recentes em memória."""
        if self.current_import_index > 0:
            self.current_import_index -= 1
            self.render_current_toc_review()

    def finalize_batch_import(self):
        """Pede confirmação do usuário e executa a gravação transacional única de todos os PDFs."""
        items_to_save = list(self.batch_staged_data.values())
        total_pdfs = len(items_to_save)
        
        # Calcula o total de tópicos acumulados em todos os PDFs para dar mais clareza na mensagem
        total_topics = sum(len(item.get("topics", [])) for item in items_to_save)

        # -----------------------------------------------------------------
        # Mensagem de Confirmação Final
        # -----------------------------------------------------------------
        reply = QMessageBox.question(
            self,
            "Confirmar Importação em Lote",
            f"Deseja realmente confirmar e importar a estrutura de {total_pdfs} arquivo(s) PDF "
            f"(totalizando {total_topics} tópico(s))?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )

        # Se o usuário cancelar, interrompe o processo e permanece na tela atual
        if reply != QMessageBox.Yes:
            return

        # -----------------------------------------------------------------
        # Execução da Gravação no Banco de Dados
        # -----------------------------------------------------------------
        db = SessionLocal()
        try:
            TOCReviewView.save_batch_data(db, items_to_save)

            QMessageBox.information(
                self, 
                "Importação Concluída", 
                f"Todos os {total_pdfs} PDF(s) foram processados e gravados no banco de dados com sucesso!"
            )
            
            # Limpa as filas e retorna para o Dashboard/Início
            self.import_view.clear_all_files()
            self.batch_staged_data.clear()
            self.import_queue.clear()
            self.switch_view(0)

        except Exception as e:
            QMessageBox.critical(
                self, 
                "Erro na Importação", 
                f"Ocorreu um erro ao gravar os dados no banco de dados. Nenhuma alteração foi salva.\n\nDetalhes: {str(e)}"
            )
        finally:
            db.close()

    def show_pdf_import_view(self):
        """Retorna para a tela de seleção/importação preservando a lista de seleção."""
        self.import_queue.clear()
        self.batch_staged_data.clear()
        self.is_returning_to_import = True
        self.switch_view(4)

    def closeEvent(self, event):
        if self.gdrive_service.is_authenticated():
            # Fecha todas as conexões ativas do SQLAlchemy com o SQLite antes de ler o arquivo
            engine.dispose()
            
            # Cria uma tela/diálogo rápido de carregamento
            progress = QProgressDialog("Sincronizando com o Google Drive...", None, 0, 0, self)
            progress.setWindowModality(Qt.WindowModal)
            progress.show()

            # Envia em background ou de forma síncrona se for rápido (< 2s)
            try:
                self.gdrive_service.upload_database()
            except Exception as e:
                print(f"Erro ao salvar na nuvem antes de fechar: {e}")
                
            progress.close()

        event.accept()

    # -------------------------------------------------------------
    # OUTROS MÉTODOS DA JANELA PRINCIPAL
    # -------------------------------------------------------------
    def on_reader_back(self):
        self.dash_view.refresh()
        self.switch_view(0)

    def open_global_search(self):
        dialog = GlobalSearchDialog(self)
        if dialog.exec() == QDialog.Accepted and dialog.selected_result:
            res = dialog.selected_result
            res_type = res.get("type")

            if res_type == "ERROR":
                self.switch_view(3)
                if hasattr(self.errors_view, "cb_filter_reason"):
                    self.errors_view.cb_filter_reason.blockSignals(True)
                    self.errors_view.cb_filter_reason.setCurrentIndex(0)
                    self.errors_view.cb_filter_reason.blockSignals(False)

                subject_id = res.get("subject_id")
                if subject_id and hasattr(self.errors_view, "cb_filter_subject"):
                    idx = self.errors_view.cb_filter_subject.findData(subject_id)
                    if idx != -1:
                        self.errors_view.cb_filter_subject.blockSignals(True)
                        self.errors_view.cb_filter_subject.setCurrentIndex(idx)
                        self.errors_view.cb_filter_subject.blockSignals(False)

                self.errors_view.load_errors()
                if res.get("error_id") and hasattr(self.errors_view, "select_error_by_id"):
                    self.errors_view.select_error_by_id(res.get("error_id"))

            elif res_type == "SUBJECT":
                self.switch_view(1)
                if res.get("subject_id") and hasattr(self.subj_view, "select_subject_by_id"):
                    self.subj_view.select_subject_by_id(res.get("subject_id"))

            elif res_type == "TOPIC":
                self.switch_view(1)
                subject_id = res.get("subject_id")
                topic_id = res.get("topic_id")

                if subject_id and hasattr(self.subj_view, "select_subject_by_id"):
                    self.subj_view.select_subject_by_id(subject_id)

                if topic_id:
                    self._select_topic_in_tree(topic_id)

            elif res_type in ("NOTE", "HIGHLIGHT"):
                self.switch_view(2)
                if hasattr(self.reader_view, "jump_to_annotation"):
                    self.reader_view.jump_to_annotation(res)

    def _select_topic_in_tree(self, topic_id):
        tree = self.subj_view.tree_topics

        def search_node(parent_item=None):
            count = parent_item.childCount() if parent_item else tree.topLevelItemCount()
            for i in range(count):
                item = parent_item.child(i) if parent_item else tree.topLevelItem(i)
                if item.data(0, Qt.UserRole) == topic_id and item.data(0, Qt.UserRole + 1) == "TOPIC":
                    curr = item
                    while curr is not None:
                        curr.setExpanded(True)
                        curr = curr.parent()
                    
                    tree.setCurrentItem(item)
                    tree.scrollToItem(item)
                    tree.setFocus()
                    return True
                
                if search_node(item):
                    return True
            return False

        search_node(None)

    def toggle_left_sidebar(self):
        is_visible = self.sidebar_widget.isVisible()
        self.sidebar_widget.setVisible(not is_visible)

    def switch_view(self, index: int):
        # Controla a visibilidade da barra lateral da janela principal
        if index == 2:
            self.sidebar_widget.setVisible(False)
        else:
            self.sidebar_widget.setVisible(True)

        for i, btn in enumerate(self.nav_buttons):
            btn.setChecked(i == index)

        if index == 0:
            self.dash_view.refresh()
        elif index == 1:
            self.subj_view.refresh()
        elif index == 3:
            self.errors_view.load_combos()
            self.errors_view.load_errors()
        elif index == 4:
            if not self.is_returning_to_import:
                self.import_view.clear_all_files()
            self.is_returning_to_import = False

        self.stack.setCurrentIndex(index)

    def handle_app_reset(self):
        if hasattr(self, 'reader_view'):
            self.reader_view.unload_pdf()
        self.switch_view(0)

    def open_study_session(self, block_id: int):
        self.reader_view.load_block(block_id)
        self.sidebar_widget.setVisible(False)
        self.switch_view(2)