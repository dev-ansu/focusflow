from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget, 
                             QTreeWidgetItem, QPushButton, QLabel, QMessageBox, 
                             QSpinBox, QComboBox, QFrame, QHeaderView)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon
from database.connection import SessionLocal
from models.models import PdfDocument, Topic
from services.study_manager import StudyManager

class TOCReviewView(QWidget):
    completed = Signal()

    def __init__(self, file_path: str, subject_id: int, detected_topics: list):
        super().__init__()
        self.file_path = file_path
        self.subject_id = subject_id
        self.detected_topics = detected_topics
        self.init_ui()

    def init_ui(self):
        # Container principal com fundo escuro
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
        
        lbl_subtitle = QLabel("Ajuste os títulos e os limites de páginas detectados antes de gerar os blocos de estudo.")
        lbl_subtitle.setStyleSheet("font-size: 12px; color: #BDC3C7; border: none;")
        lbl_subtitle.setWordWrap(True)

        header_layout.addWidget(lbl_title)
        header_layout.addWidget(lbl_subtitle)
        main_layout.addWidget(header_card)

        # --- TABELA / TREE WIDGET DE TÓPICOS ---
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Tópico / Capítulo", "Pág. Inicial", "Pág. Final"])
        
        # Ajuste de proporção das colunas
        self.tree.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.tree.header().setSectionResizeMode(1, QHeaderView.Fixed)
        self.tree.header().setSectionResizeMode(2, QHeaderView.Fixed)
        self.tree.setColumnWidth(1, 100)
        self.tree.setColumnWidth(2, 100)
        self.tree.setAnimated(True)
        self.tree.setIndentation(15)

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

        # --- CONTROLES DE EDIÇÃO DA ÁRVORE (Adicionar / Remover) ---
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
        """)
        config_layout = QHBoxLayout(config_card)
        config_layout.setSpacing(15)

        config_layout.addWidget(QLabel("⚙️ Divisão de Blocos:"))
        
        self.cmb_mode = QComboBox()
        self.cmb_mode.addItems(["Por Tópico (1 Tópico = 1 Bloco)", "Por Limite de Páginas"])
        config_layout.addWidget(self.cmb_mode)

        config_layout.addWidget(QLabel("Págs. por Bloco:"))
        self.spn_pages = QSpinBox()
        self.spn_pages.setRange(5, 100)
        self.spn_pages.setValue(15)
        config_layout.addWidget(self.spn_pages)

        config_layout.addStretch()
        main_layout.addWidget(config_card)

        # --- BOTAO PRINCIPAL DE SALVAR ---
        btn_confirm = QPushButton("🚀 Confirmar e Gerar Blocos")
        btn_confirm.setCursor(Qt.PointingHandCursor)
        btn_confirm.setStyleSheet("""
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
        btn_confirm.clicked.connect(self.save)
        
        main_layout.addWidget(btn_confirm)

    def populate_tree(self):
        self.tree.clear()
        for t in self.detected_topics:
            item = QTreeWidgetItem([t["title"], str(t["page_start"]), str(t["page_end"])])
            item.setFlags(item.flags() | Qt.ItemIsEditable)
            self.tree.addTopLevelItem(item)

    def add_topic(self):
        item = QTreeWidgetItem(["Novo Tópico", "1", "10"])
        item.setFlags(item.flags() | Qt.ItemIsEditable)
        self.tree.addTopLevelItem(item)
        self.tree.setCurrentItem(item)

    def remove_topic(self):
        root = self.tree.invisibleRootItem()
        for item in self.tree.selectedItems():
            root.removeChild(item)

    def save(self):
        db = SessionLocal()
        try:
            from services.pdf_parser import PDFParser
            info = PDFParser.get_info(self.file_path)

            pdf_doc = PdfDocument(
                subject_id=self.subject_id,
                title=info["title"],
                file_path=self.file_path,
                file_size_bytes=info["size_bytes"],
                total_pages=info["pages"]
            )
            db.add(pdf_doc)
            db.flush()

            mode_str = "topic" if self.cmb_mode.currentIndex() == 0 else "pages"

            root = self.tree.invisibleRootItem()
            for i in range(root.childCount()):
                item = root.child(i)
                title = item.text(0)
                p_start = int(item.text(1))
                p_end = int(item.text(2))

                topic = Topic(
                    pdf_id=pdf_doc.id,
                    title=title,
                    page_start=p_start,
                    page_end=p_end
                )
                db.add(topic)
                db.flush()

                # Gera blocos automaticamente
                StudyManager.create_blocks_for_topic(db, topic.id, mode=mode_str, pages_per_block=self.spn_pages.value())

            db.commit()
            QMessageBox.information(self, "Sucesso", "PDF e tópicos importados com sucesso!")
            self.completed.emit()
        except Exception as e:
            db.rollback()
            QMessageBox.critical(self, "Erro", f"Erro ao salvar: {str(e)}")
        finally:
            db.close()