from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget, 
                             QTreeWidgetItem, QPushButton, QLabel, QMessageBox, 
                             QSpinBox, QComboBox, QFrame, QHeaderView,
                             QStyledItemDelegate, QLineEdit)
from PySide6.QtGui import QIntValidator, QShortcut, QKeySequence
from PySide6.QtCore import Qt, Signal
from database.connection import SessionLocal
from models.models import PdfDocument, Topic
from services.study_manager import StudyManager
from services.pdf_parser import PDFParser


class MaxPageDelegate(QStyledItemDelegate):
    def __init__(self, parent=None, max_pages=99999):
        super().__init__(parent)
        self.max_pages = max_pages

    def createEditor(self, parent, option, index):
        editor = QLineEdit(parent)
        validator = QIntValidator(1, self.max_pages, editor)
        editor.setValidator(validator)
        return editor


class TOCReviewView(QWidget):
    completed = Signal()         # Disparado quando todo o lote for salvo com sucesso
    back_requested = Signal()    # Abortar/Voltar para a seleção de arquivos
    prev_requested = Signal()    # Navegar para o PDF anterior
    next_requested = Signal(dict) # Avançar para o próximo PDF transmitindo os dados em memória

    def __init__(self, file_path: str, subject_id: int, detected_topics: list):
        super().__init__()
        self.file_path = file_path
        self.subject_id = subject_id
        self.detected_topics = detected_topics
        
        self.undo_stack = []

        try:
            self.pdf_info = PDFParser.get_info(self.file_path)
            self.total_pages = self.pdf_info.get("pages", 99999)
        except Exception:
            self.total_pages = 99999
            self.pdf_info = {}

        self.init_ui()
        self.setup_shortcuts()

    def setup_shortcuts(self):
        self.shortcut_undo = QShortcut(QKeySequence("Ctrl+Z"), self)
        self.shortcut_undo.activated.connect(self.undo_remove)

    def init_ui(self):
        self.setStyleSheet("background-color: #121418; color: #ECF0F1;")
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(12)

        # --- CABEÇALHO ---
        header_card = QFrame()
        header_card.setStyleSheet("""
            QFrame {
                background-color: #1E222A;
                border: 1px solid #2C3E50;
                border-radius: 8px;
                padding: 12px;
            }
        """)
        header_main_layout = QHBoxLayout(header_card)
        
        header_text_layout = QVBoxLayout()
        header_text_layout.setSpacing(4)

        lbl_title = QLabel("📚 Revisão da Estrutura do Sumário")
        lbl_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #FFFFFF; border: none;")
        
        self.lbl_subtitle = QLabel(
            f"Ajuste os tópicos (PDF com {self.total_pages} pág(s)). Nenhuma página pode exceder esse limite."
        )
        self.lbl_subtitle.setStyleSheet("font-size: 12px; color: #BDC3C7; border: none;")
        self.lbl_subtitle.setWordWrap(True)

        header_text_layout.addWidget(lbl_title)
        header_text_layout.addWidget(self.lbl_subtitle)
        header_main_layout.addLayout(header_text_layout, stretch=1)

        btn_back = QPushButton("📁 Cancelar Importação")
        btn_back.setCursor(Qt.PointingHandCursor)
        btn_back.setStyleSheet("""
            QPushButton {
                background-color: #2C3E50; color: #CDD6F4; font-weight: bold;
                padding: 8px 14px; border: 1px solid #34495E; border-radius: 6px; font-size: 12px;
            }
            QPushButton:hover { background-color: #34495E; color: #89B4FA; }
        """)
        btn_back.clicked.connect(self.back_requested.emit)
        header_main_layout.addWidget(btn_back, alignment=Qt.AlignRight | Qt.AlignVCenter)

        main_layout.addWidget(header_card)

        # --- BARRA DE BUSCA E SELEÇÃO RÁPIDA ---
        toolbar_card = QFrame()
        toolbar_card.setStyleSheet("background-color: #1E222A; border-radius: 6px; padding: 8px;")
        toolbar_layout = QHBoxLayout(toolbar_card)
        toolbar_layout.setSpacing(8)

        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("🔍 Filtrar e selecionar tópicos...")
        self.txt_search.setStyleSheet("""
            QLineEdit {
                background-color: #121418; color: #ECF0F1;
                border: 1px solid #34495E; border-radius: 5px; padding: 6px 10px;
            }
            QLineEdit:focus { border-color: #3498DB; }
        """)
        self.txt_search.textChanged.connect(self.on_search_text_changed)
        toolbar_layout.addWidget(self.txt_search, stretch=2)

        btn_check_matching = QPushButton("☑️ Marcar Buscados")
        btn_check_matching.setCursor(Qt.PointingHandCursor)
        btn_check_matching.setStyleSheet("""
            QPushButton { background-color: #2980B9; color: white; padding: 6px 12px; border-radius: 4px; border: none; }
            QPushButton:hover { background-color: #3498DB; }
        """)
        btn_check_matching.clicked.connect(lambda: self.toggle_check_searched(True))
        toolbar_layout.addWidget(btn_check_matching)

        btn_uncheck_all = QPushButton("☐ Desmarcar Todos")
        btn_uncheck_all.setCursor(Qt.PointingHandCursor)
        btn_uncheck_all.setStyleSheet("""
            QPushButton { background-color: #34495E; color: white; padding: 6px 12px; border-radius: 4px; border: none; }
            QPushButton:hover { background-color: #455A64; }
        """)
        btn_uncheck_all.clicked.connect(lambda: self.toggle_check_all(False))
        toolbar_layout.addWidget(btn_uncheck_all)

        main_layout.addWidget(toolbar_card)

        # --- ÁRVORE DE TÓPICOS ---
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Tópico / Capítulo", "Pág. Inicial", "Pág. Final"])
        self.tree.setSelectionMode(QTreeWidget.ExtendedSelection)
        
        self.tree.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.tree.header().setSectionResizeMode(1, QHeaderView.Fixed)
        self.tree.header().setSectionResizeMode(2, QHeaderView.Fixed)
        self.tree.setColumnWidth(1, 100)
        self.tree.setColumnWidth(2, 100)
        self.tree.setAnimated(True)
        self.tree.setIndentation(15)

        numeric_delegate = MaxPageDelegate(self.tree, max_pages=self.total_pages)
        self.tree.setItemDelegateForColumn(1, numeric_delegate)
        self.tree.setItemDelegateForColumn(2, numeric_delegate)

        self.tree.setStyleSheet("""
            QTreeWidget {
                background-color: #1E222A; border: 1px solid #2C3E50;
                border-radius: 8px; padding: 5px; outline: none; font-size: 13px;
            }
            QTreeWidget::item { padding: 6px; border-bottom: 1px solid #282C34; border-radius: 4px; }
            QTreeWidget::item:hover { background-color: #2C3E50; }
            QTreeWidget::item:selected { background-color: #34495E; color: #3498DB; font-weight: bold; }
            QHeaderView::section {
                background-color: #181B20; color: #3498DB; font-weight: bold;
                padding: 8px; border: none; border-bottom: 2px solid #2C3E50;
            }
        """)
        main_layout.addWidget(self.tree)

        self.populate_tree()

        # --- AÇÕES EM MASSA & EDICÃO ---
        tree_actions_layout = QHBoxLayout()
        
        btn_add = QPushButton("➕ Adicionar Tópico")
        btn_add.setCursor(Qt.PointingHandCursor)
        btn_add.setStyleSheet("""
            QPushButton {
                background-color: #2C3E50; color: #ECF0F1; font-weight: bold;
                padding: 8px 12px; border-radius: 5px; border: 1px solid #34495E;
            }
            QPushButton:hover { background-color: #34495E; }
        """)
        btn_add.clicked.connect(self.add_topic)

        btn_remove_checked = QPushButton("🗑️ Remover Marcados (☑)")
        btn_remove_checked.setCursor(Qt.PointingHandCursor)
        btn_remove_checked.setStyleSheet("""
            QPushButton {
                background-color: #C0392B; color: white; font-weight: bold;
                padding: 8px 12px; border-radius: 5px; border: none;
            }
            QPushButton:hover { background-color: #E74C3C; }
        """)
        btn_remove_checked.clicked.connect(self.remove_checked_topics)

        btn_undo = QPushButton("↩️ Desfazer (Ctrl+Z)")
        btn_undo.setCursor(Qt.PointingHandCursor)
        btn_undo.setStyleSheet("""
            QPushButton {
                background-color: #2C3E50; color: #E5C07B; font-weight: bold;
                padding: 8px 12px; border-radius: 5px; border: 1px solid #34495E;
            }
            QPushButton:hover { background-color: #34495E; }
        """)
        btn_undo.clicked.connect(self.undo_remove)

        btn_reset = QPushButton("🔄 Resetar Tópicos")
        btn_reset.setCursor(Qt.PointingHandCursor)
        btn_reset.setStyleSheet("""
            QPushButton {
                background-color: #2C3E50; color: #E06C75; font-weight: bold;
                padding: 8px 12px; border-radius: 5px; border: 1px solid #34495E;
            }
            QPushButton:hover { background-color: #34495E; }
        """)
        btn_reset.clicked.connect(self.reset_topics)

        tree_actions_layout.addWidget(btn_add)
        tree_actions_layout.addWidget(btn_remove_checked)
        tree_actions_layout.addWidget(btn_undo)
        tree_actions_layout.addWidget(btn_reset)
        tree_actions_layout.addStretch()
        
        main_layout.addLayout(tree_actions_layout)

        # --- CONFIGURAÇÃO DE BLOCOS DE ESTUDO ---
        config_card = QFrame()
        config_card.setStyleSheet("""
            QFrame {
                background-color: #1E222A; border: 1px solid #2C3E50;
                border-radius: 8px; padding: 10px 15px;
            }
            QLabel { color: #ECF0F1; font-weight: bold; border: none; }
            QComboBox, QSpinBox {
                background-color: #121418; color: #ECF0F1;
                border: 1px solid #34495E; border-radius: 5px; padding: 6px; min-width: 120px;
            }
        """)
        config_layout = QHBoxLayout(config_card)
        config_layout.setSpacing(15)

        config_layout.addWidget(QLabel("⚙️ Divisão de Blocos:"))
        self.cmb_mode = QComboBox()
        self.cmb_mode.addItems(["Por Tópico (1 Tópico = 1 Bloco)", "Por Limite de Páginas"])
        config_layout.addWidget(self.cmb_mode)

        self.lbl_pages_per_block = QLabel("Págs. por Bloco:")
        config_layout.addWidget(self.lbl_pages_per_block)
        
        self.spn_pages = QSpinBox()
        self.spn_pages.setRange(1, self.total_pages)
        self.spn_pages.setValue(min(15, self.total_pages))
        config_layout.addWidget(self.spn_pages)

        self.cmb_mode.currentIndexChanged.connect(self._on_mode_changed)
        self._on_mode_changed(self.cmb_mode.currentIndex())

        config_layout.addStretch()
        main_layout.addWidget(config_card)

        # --- BARRA DE BOTÕES DE NAVEGAÇÃO E CONFIRMAÇÃO ---
        nav_buttons_layout = QHBoxLayout()

        self.btn_prev_pdf = QPushButton("⬅️ PDF Anterior")
        self.btn_prev_pdf.setCursor(Qt.PointingHandCursor)
        self.btn_prev_pdf.setEnabled(False)
        self.btn_prev_pdf.setStyleSheet("""
            QPushButton {
                background-color: #34495E; color: white;
                font-size: 14px; font-weight: bold; padding: 12px 20px; border-radius: 6px;
            }
            QPushButton:hover { background-color: #455A64; }
            QPushButton:disabled { background-color: #1E222A; color: #555; }
        """)
        # 👈 Ação de voltar sem tocar no banco
        self.btn_prev_pdf.clicked.connect(self.prev_requested.emit)

        self.btn_confirm = QPushButton("🚀 Confirmar e Avançar")
        self.btn_confirm.setCursor(Qt.PointingHandCursor)
        self.btn_confirm.setStyleSheet("""
            QPushButton {
                background-color: #27AE60; color: white;
                font-size: 14px; font-weight: bold; padding: 12px; border-radius: 6px;
            }
            QPushButton:hover { background-color: #2ECC71; }
        """)
        # 👈 Valida e repassa os dados em memória
        self.btn_confirm.clicked.connect(self.handle_next_click)

        nav_buttons_layout.addWidget(self.btn_prev_pdf)
        nav_buttons_layout.addWidget(self.btn_confirm, stretch=1)

        self.tree.itemChanged.connect(self._on_item_changed)
        main_layout.addLayout(nav_buttons_layout)

    def set_progress_info(self, current: int, total: int):
        """Ajusta o estado visual dos botões e títulos conforme o item atual da fila."""
        self.btn_prev_pdf.setEnabled(current > 1)

        if total > 1:
            self.lbl_subtitle.setText(
                f"<span style='color: #3498DB; font-weight: bold;'>[PDF {current} de {total}]</span> "
                f"Ajuste os tópicos (PDF com {self.total_pages} pág(s)). Nenhuma página pode exceder esse limite."
            )
            if current < total:
                self.btn_confirm.setText(f"🚀 Confirmar e Ir para o Próximo PDF ({current}/{total}) ➔")
            else:
                self.btn_confirm.setText("🚀 Concluir e Finalizar Tudo")

    def populate_tree(self):
        self.tree.clear()
        for t in self.detected_topics:
            p_start = min(max(1, t["page_start"]), self.total_pages)
            p_end = min(max(p_start, t["page_end"]), self.total_pages)

            item = QTreeWidgetItem([t["title"], str(p_start), str(p_end)])
            item.setFlags(item.flags() | Qt.ItemIsEditable | Qt.ItemIsUserCheckable)
            item.setCheckState(0, Qt.Unchecked)
            self.tree.addTopLevelItem(item)

    def remove_checked_topics(self):
        root = self.tree.invisibleRootItem()
        items_to_remove = []
        
        for i in range(root.childCount()):
            item = root.child(i)
            if item.checkState(0) == Qt.Checked:
                items_to_remove.append(item)

        if not items_to_remove:
            QMessageBox.information(self, "Aviso", "Nenhum tópico marcado para remoção.")
            return

        snapshot = []
        for item in items_to_remove:
            snapshot.append({
                "title": item.text(0),
                "p_start": item.text(1),
                "p_end": item.text(2),
                "index": root.indexOfChild(item)
            })
        self.undo_stack.append(snapshot)

        self.txt_search.blockSignals(True)
        self.txt_search.clear()
        self.txt_search.blockSignals(False)

        for item in items_to_remove:
            root.removeChild(item)

        for i in range(root.childCount()):
            root.child(i).setHidden(False)

    def undo_remove(self):
        if not self.undo_stack:
            return

        last_removed = self.undo_stack.pop()
        root = self.tree.invisibleRootItem()

        self.tree.blockSignals(True)
        try:
            for data in last_removed:
                item = QTreeWidgetItem([data["title"], data["p_start"], data["p_end"]])
                item.setFlags(item.flags() | Qt.ItemIsEditable | Qt.ItemIsUserCheckable)
                item.setCheckState(0, Qt.Unchecked)
                
                idx = min(data["index"], root.childCount())
                root.insertChild(idx, item)
        finally:
            self.tree.blockSignals(False)

    def reset_topics(self):
        if self.tree.invisibleRootItem().childCount() > 0:
            reply = QMessageBox.question(
                self, "Confirmar Restauração",
                "Deseja descartar as alterações feitas e restaurar a lista original de tópicos deste PDF?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return

        self.undo_stack.clear()
        self.populate_tree()

    def _on_item_changed(self, item, column):
        if column not in (1, 2):
            return

        root = self.tree.invisibleRootItem()
        item_index = root.indexOfChild(item)
        if item_index == -1:
            return

        self.tree.blockSignals(True)

        try:
            try:
                p_start = int(item.text(1))
            except ValueError:
                p_start = 1

            try:
                p_end = int(item.text(2))
            except ValueError:
                p_end = p_start

            p_start = max(1, min(p_start, self.total_pages))
            p_end = max(p_start, min(p_end, self.total_pages))
            
            item.setText(1, str(p_start))
            item.setText(2, str(p_end))

            current_next_start = p_end + 1

            for i in range(item_index + 1, root.childCount()):
                child_item = root.child(i)
                
                if current_next_start > self.total_pages:
                    child_item.setText(1, str(self.total_pages))
                    child_item.setText(2, str(self.total_pages))
                    continue

                try:
                    old_start = int(child_item.text(1))
                    old_end = int(child_item.text(2))
                    block_size = max(0, old_end - old_start)
                except ValueError:
                    block_size = 5

                new_child_start = current_next_start
                new_child_end = min(new_child_start + block_size, self.total_pages)

                child_item.setText(1, str(new_child_start))
                child_item.setText(2, str(new_child_end))

                current_next_start = new_child_end + 1

        finally:
            self.tree.blockSignals(False)

    def on_search_text_changed(self, text: str):
        query = text.strip().lower()
        root = self.tree.invisibleRootItem()
        
        for i in range(root.childCount()):
            item = root.child(i)
            title = item.text(0).lower()
            
            if not query:
                item.setHidden(False)
            else:
                matches = query in title
                item.setHidden(not matches)
                if matches:
                    item.setCheckState(0, Qt.Checked)
                else:
                    item.setCheckState(0, Qt.Unchecked)

    def toggle_check_searched(self, checked: bool):
        state = Qt.Checked if checked else Qt.Unchecked
        root = self.tree.invisibleRootItem()
        for i in range(root.childCount()):
            item = root.child(i)
            if not item.isHidden():
                item.setCheckState(0, state)

    def toggle_check_all(self, checked: bool):
        state = Qt.Checked if checked else Qt.Unchecked
        root = self.tree.invisibleRootItem()
        for i in range(root.childCount()):
            root.child(i).setCheckState(0, state)

    def _on_mode_changed(self, index: int):
        is_page_limit_mode = (index == 1)
        self.spn_pages.setEnabled(is_page_limit_mode)
        self.lbl_pages_per_block.setEnabled(is_page_limit_mode)

    def add_topic(self):
        p_start = str(min(1, self.total_pages))
        p_end = str(min(10, self.total_pages))
        
        item = QTreeWidgetItem(["Novo Tópico", p_start, p_end])
        item.setFlags(item.flags() | Qt.ItemIsEditable | Qt.ItemIsUserCheckable)
        item.setCheckState(0, Qt.Unchecked)
        self.tree.addTopLevelItem(item)
        self.tree.setCurrentItem(item)
        self.tree.editItem(item, 0)

    def get_current_data(self) -> dict:
        """Extrai os dados da tela validando campos sem salvar no BD."""
        root = self.tree.invisibleRootItem()
        if root.childCount() == 0:
            QMessageBox.warning(self, "Aviso", "Você precisa ter pelo menos um tópico cadastrado.")
            return None

        parsed_topics = []
        for i in range(root.childCount()):
            item = root.child(i)
            title = item.text(0).strip() or f"Tópico {i+1}"
            str_start = item.text(1).strip()
            str_end = item.text(2).strip()

            if not str_start.isdigit() or not str_end.isdigit():
                QMessageBox.warning(
                    self, "Erro de Validação", 
                    f"As páginas do tópico '{title}' devem ser números inteiros."
                )
                return None

            p_start = int(str_start)
            p_end = int(str_end)

            if p_start > self.total_pages or p_end > self.total_pages or p_start < 1 or p_end < 1 or p_start > p_end:
                QMessageBox.warning(
                    self, "Erro de Validação", 
                    f"Intervalo de páginas inválido no tópico '{title}'."
                )
                return None

            parsed_topics.append({
                "title": title,
                "page_start": p_start,
                "page_end": p_end
            })

        return {
            "file_path": self.file_path,
            "subject_id": self.subject_id,
            "info": self.pdf_info or PDFParser.get_info(self.file_path),
            "topics": parsed_topics,
            "mode": "topic" if self.cmb_mode.currentIndex() == 0 else "pages",
            "pages_per_block": self.spn_pages.value()
        }

    def handle_next_click(self):
        """Valida e emite o sinal com a estrutura em memória."""
        data = self.get_current_data()
        if data:
            self.next_requested.emit(data)

    @staticmethod
    def save_batch_data(db, batch_data_list: list):
        """Salva a lista completa acumulada de PDFs e seus blocos no banco de dados de uma só vez."""
        try:
            for data in batch_data_list:
                info = data["info"]
                pdf_doc = PdfDocument(
                    subject_id=data["subject_id"],
                    title=info.get("title", "Documento Sem Título"),
                    file_path=data["file_path"],
                    file_size_bytes=info.get("size_bytes", 0),
                    total_pages=info.get("pages", 1)
                )
                db.add(pdf_doc)
                db.flush()

                for t_data in data["topics"]:
                    topic = Topic(
                        pdf_id=pdf_doc.id,
                        title=t_data["title"],
                        page_start=t_data["page_start"],
                        page_end=t_data["page_end"]
                    )
                    db.add(topic)
                    db.flush()

                    StudyManager.create_blocks_for_topic(
                        db, topic.id, mode=data["mode"], pages_per_block=data["pages_per_block"]
                    )

            db.commit()
            return True
        except Exception as e:
            db.rollback()
            raise e