from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget, 
                             QTreeWidgetItem, QPushButton, QLabel, QMessageBox, 
                             QSpinBox, QComboBox, QFrame, QHeaderView,
                             QStyledItemDelegate, QLineEdit)
from PySide6.QtGui import QIntValidator
from PySide6.QtCore import Qt, Signal
from database.connection import SessionLocal
from models.models import PdfDocument, Topic
from services.study_manager import StudyManager
from services.pdf_parser import PDFParser


class MaxPageDelegate(QStyledItemDelegate):
    """Delegate que limita a digitação até o número máximo de páginas do PDF."""
    def __init__(self, parent=None, max_pages=99999):
        super().__init__(parent)
        self.max_pages = max_pages

    def createEditor(self, parent, option, index):
        editor = QLineEdit(parent)
        # Permite apenas números inteiros entre 1 e o total de páginas do PDF
        validator = QIntValidator(1, self.max_pages, editor)
        editor.setValidator(validator)
        return editor


class TOCReviewView(QWidget):
    completed = Signal()

    def __init__(self, file_path: str, subject_id: int, detected_topics: list):
        super().__init__()
        self.file_path = file_path
        self.subject_id = subject_id
        self.detected_topics = detected_topics
        
        # Obtém os metadados do PDF antecipadamente para saber o total real de páginas
        try:
            self.pdf_info = PDFParser.get_info(self.file_path)
            self.total_pages = self.pdf_info.get("pages", 99999)
        except Exception:
            self.total_pages = 99999
            self.pdf_info = {}

        self.init_ui()

    def init_ui(self):
        self.setStyleSheet("background-color: #121418; color: #ECF0F1;")
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

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
        header_layout = QVBoxLayout(header_card)
        header_layout.setSpacing(4)

        lbl_title = QLabel("📚 Revisão da Estrutura do Sumário")
        lbl_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #FFFFFF; border: none;")
        
        # Exibe o total de páginas do documento para orientar o usuário
        self.lbl_subtitle = QLabel(
            f"Ajuste os tópicos (PDF com {self.total_pages} pág(s)). Nenhuma página pode exceder esse limite."
        )
        self.lbl_subtitle.setStyleSheet("font-size: 12px; color: #BDC3C7; border: none;")
        self.lbl_subtitle.setWordWrap(True)

        header_layout.addWidget(lbl_title)
        header_layout.addWidget(self.lbl_subtitle)
        main_layout.addWidget(header_card)

        # --- TABELA / TREE WIDGET DE TÓPICOS ---
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Tópico / Capítulo", "Pág. Inicial", "Pág. Final"])
        
        self.tree.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.tree.header().setSectionResizeMode(1, QHeaderView.Fixed)
        self.tree.header().setSectionResizeMode(2, QHeaderView.Fixed)
        self.tree.setColumnWidth(1, 100)
        self.tree.setColumnWidth(2, 100)
        self.tree.setAnimated(True)
        self.tree.setIndentation(15)

        # APLICAÇÃO DO DELEGATE COM LIMITE MÁXIMO DE PÁGINAS DO PDF
        numeric_delegate = MaxPageDelegate(self.tree, max_pages=self.total_pages)
        self.tree.setItemDelegateForColumn(1, numeric_delegate)
        self.tree.setItemDelegateForColumn(2, numeric_delegate)

        self.tree.setStyleSheet("""
            QTreeWidget {
                background-color: #1E222A;
                border: 1px solid #2C3E50;
                border-radius: 8px;
                padding: 5px;
                outline: none;
                font-size: 13px;
            }
            QTreeWidget::item {
                padding: 6px;
                border-bottom: 1px solid #282C34;
                border-radius: 4px;
            }
            QTreeWidget::item:hover {
                background-color: #2C3E50;
            }
            QTreeWidget::item:selected {
                background-color: #34495E;
                color: #3498DB;
                font-weight: bold;
            }
            QHeaderView::section {
                background-color: #181B20;
                color: #3498DB;
                font-weight: bold;
                padding: 8px;
                border: none;
                border-bottom: 2px solid #2C3E50;
            }
        """)
        main_layout.addWidget(self.tree)

        self.populate_tree()

        # --- CONTROLES DE EDIÇÃO DA ÁRVORE ---
        tree_actions_layout = QHBoxLayout()
        
        btn_add = QPushButton("➕ Adicionar Tópico")
        btn_add.setCursor(Qt.PointingHandCursor)
        btn_add.setStyleSheet("""
            QPushButton {
                background-color: #2C3E50;
                color: #ECF0F1;
                font-weight: bold;
                padding: 8px 12px;
                border-radius: 5px;
                border: 1px solid #34495E;
            }
            QPushButton:hover { background-color: #34495E; }
        """)
        btn_add.clicked.connect(self.add_topic)

        btn_del = QPushButton("🗑️ Remover Selecionado")
        btn_del.setCursor(Qt.PointingHandCursor)
        btn_del.setStyleSheet("""
            QPushButton {
                background-color: #2C3E50;
                color: #E74C3C;
                font-weight: bold;
                padding: 8px 12px;
                border-radius: 5px;
                border: 1px solid #34495E;
            }
            QPushButton:hover { background-color: #922B21; color: white; }
        """)
        btn_del.clicked.connect(self.remove_topic)

        tree_actions_layout.addWidget(btn_add)
        tree_actions_layout.addWidget(btn_del)
        tree_actions_layout.addStretch()
        
        main_layout.addLayout(tree_actions_layout)

        # --- PAINEL DE CONFIGURAÇÃO DE BLOCOS DE ESTUDO ---
        config_card = QFrame()
        config_card.setStyleSheet("""
            QFrame {
                background-color: #1E222A;
                border: 1px solid #2C3E50;
                border-radius: 8px;
                padding: 10px 15px;
            }
            QLabel { color: #ECF0F1; font-weight: bold; border: none; }
            QComboBox, QSpinBox {
                background-color: #121418;
                color: #ECF0F1;
                border: 1px solid #34495E;
                border-radius: 5px;
                padding: 6px;
                min-width: 120px;
            }
            QComboBox::drop-down { border: none; }
            QComboBox QAbstractItemView {
                background-color: #1E222A;
                color: #ECF0F1;
                selection-background-color: #34495E;
            }
            QSpinBox:disabled {
                background-color: #1A1D24;
                color: #555555;
                border: 1px solid #2A2D34;
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

        # Conecta a alteração do modo para habilitar/desabilitar o SpinBox
        self.cmb_mode.currentIndexChanged.connect(self._on_mode_changed)
        self._on_mode_changed(self.cmb_mode.currentIndex())  # Aplica o estado inicial

        config_layout.addStretch()
        main_layout.addWidget(config_card)

        # --- BOTÃO PRINCIPAL DE SALVAR ---
        self.btn_confirm = QPushButton("🚀 Confirmar e Gerar Blocos")
        self.btn_confirm.setCursor(Qt.PointingHandCursor)
        self.btn_confirm.setStyleSheet("""
            QPushButton {
                background-color: #27AE60;
                color: white;
                font-size: 14px;
                font-weight: bold;
                padding: 12px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #2ECC71;
            }
        """)
        self.btn_confirm.clicked.connect(self.save)
        
        main_layout.addWidget(self.btn_confirm)

    def _on_mode_changed(self, index: int):
        """Habilita ou desabilita o SpinBox de páginas conforme o modo de divisão selecionado."""
        is_page_limit_mode = (index == 1)
        self.spn_pages.setEnabled(is_page_limit_mode)
        self.lbl_pages_per_block.setEnabled(is_page_limit_mode)

    def set_progress_info(self, current: int, total: int):
        """Atualiza a legenda do cabeçalho indicando o progresso do lote."""
        if total > 1:
            self.lbl_subtitle.setText(
                f"<span style='color: #3498DB; font-weight: bold;'>[PDF {current} de {total}]</span> "
                f"Ajuste os tópicos (PDF com {self.total_pages} pág(s)). Nenhuma página pode exceder esse limite."
            )
            # Atualiza o texto do botão no caso de lote para indicar que haverá próximo
            if current < total:
                self.btn_confirm.setText(f"🚀 Confirmar e Ir para o Próximo PDF ({current}/{total}) ➔")
            else:
                self.btn_confirm.setText("🚀 Concluir Importação em Lote")

    def populate_tree(self):
        self.tree.clear()
        for t in self.detected_topics:
            p_start = min(max(1, t["page_start"]), self.total_pages)
            p_end = min(max(p_start, t["page_end"]), self.total_pages)

            item = QTreeWidgetItem([t["title"], str(p_start), str(p_end)])
            item.setFlags(item.flags() | Qt.ItemIsEditable)
            self.tree.addTopLevelItem(item)

    def add_topic(self):
        """Adiciona um novo tópico e entra em modo de edição diretamente no título."""
        p_start = str(min(1, self.total_pages))
        p_end = str(min(10, self.total_pages))
        
        item = QTreeWidgetItem(["Novo Tópico", p_start, p_end])
        item.setFlags(item.flags() | Qt.ItemIsEditable)
        self.tree.addTopLevelItem(item)
        self.tree.setCurrentItem(item)
        
        # Abre o editor de texto direto na coluna do título do novo item
        self.tree.editItem(item, 0)

    def remove_topic(self):
        root = self.tree.invisibleRootItem()
        for item in self.tree.selectedItems():
            root.removeChild(item)

    def save(self):
        db = SessionLocal()
        try:
            info = self.pdf_info or PDFParser.get_info(self.file_path)

            pdf_doc = PdfDocument(
                subject_id=self.subject_id,
                title=info.get("title", "Documento Sem Título"),
                file_path=self.file_path,
                file_size_bytes=info.get("size_bytes", 0),
                total_pages=info.get("pages", self.total_pages)
            )
            db.add(pdf_doc)
            db.flush()

            mode_str = "topic" if self.cmb_mode.currentIndex() == 0 else "pages"

            root = self.tree.invisibleRootItem()
            
            if root.childCount() == 0:
                QMessageBox.warning(self, "Aviso", "Você precisa ter pelo menos um tópico cadastrado.")
                db.rollback()
                return

            for i in range(root.childCount()):
                item = root.child(i)
                title = item.text(0).strip() or f"Tópico {i+1}"
                
                str_start = item.text(1).strip()
                str_end = item.text(2).strip()

                # 1. Validação de formato
                if not str_start.isdigit() or not str_end.isdigit():
                    QMessageBox.warning(
                        self, "Erro de Validação", 
                        f"As páginas do tópico '{title}' devem ser números inteiros."
                    )
                    db.rollback()
                    return

                p_start = int(str_start)
                p_end = int(str_end)

                # 2. Validação se excede o limite real do PDF
                if p_start > self.total_pages or p_end > self.total_pages:
                    QMessageBox.critical(
                        self, "Limite de Páginas Excedido", 
                        f"O tópico '{title}' possui páginas (de {p_start} a {p_end}) que ultrapassam "
                        f"o total de páginas do PDF ({self.total_pages} páginas)."
                    )
                    db.rollback()
                    return

                # 3. Validação de consistência do intervalo
                if p_start < 1 or p_end < 1:
                    QMessageBox.warning(
                        self, "Erro de Validação", 
                        f"No tópico '{title}', as páginas devem ser maiores ou iguais a 1."
                    )
                    db.rollback()
                    return

                if p_start > p_end:
                    QMessageBox.warning(
                        self, "Erro de Validação", 
                        f"No tópico '{title}', a página inicial ({p_start}) não pode ser "
                        f"maior do que a página final ({p_end})."
                    )
                    db.rollback()
                    return

                topic = Topic(
                    pdf_id=pdf_doc.id,
                    title=title,
                    page_start=p_start,
                    page_end=p_end
                )
                db.add(topic)
                db.flush()

                # Gera blocos automaticamente
                StudyManager.create_blocks_for_topic(
                    db, topic.id, mode=mode_str, pages_per_block=self.spn_pages.value()
                )

            db.commit()
            self.completed.emit()
        except Exception as e:
            db.rollback()
            QMessageBox.critical(self, "Erro ao Salvar", f"Não foi possível salvar a estrutura do PDF:\n{str(e)}")
        finally:
            db.close()