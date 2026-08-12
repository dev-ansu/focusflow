import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QLabel, QFileDialog, QComboBox, QMessageBox, QTableWidget, 
    QTableWidgetItem, QInputDialog, QHeaderView, QFrame
)
from PySide6.QtCore import Qt, Signal
from database.connection import SessionLocal
from models.models import Subject
from services.pdf_parser import PDFParser


class PDFImportView(QWidget):
    import_requested = Signal(list, int)  # Emite (lista_de_file_paths, subject_id)

    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.selected_files = []
        self.init_ui()

    def init_ui(self):
        self.setStyleSheet("""
            QWidget {
                background-color: #1E1E2E;
                color: #CDD6F4;
                font-family: 'Segoe UI', system-ui, sans-serif;
            }
            QLabel.title {
                color: #89B4FA;
                font-size: 20px;
                font-weight: bold;
            }
            QLabel.subtitle {
                color: #A6ADC8;
                font-size: 13px;
            }
            QComboBox {
                background-color: #181825;
                color: #CDD6F4;
                border: 1px solid #313244;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 13px;
            }
            QComboBox:focus {
                border-color: #89B4FA;
            }
            QComboBox QAbstractItemView {
                background-color: #181825;
                color: #CDD6F4;
                selection-background-color: #313244;
            }
            QPushButton.primary-btn {
                background-color: #89B4FA;
                color: #11111B;
                font-weight: bold;
                padding: 8px 16px;
                border: none;
                border-radius: 6px;
            }
            QPushButton.primary-btn:hover {
                background-color: #B4BEFE;
            }
            QPushButton.secondary-btn {
                background-color: #313244;
                color: #CDD6F4;
                font-weight: bold;
                padding: 8px 16px;
                border: 1px solid #45475A;
                border-radius: 6px;
            }
            QPushButton.secondary-btn:hover {
                background-color: #45475A;
                color: #89B4FA;
            }
            QPushButton.success-btn {
                background-color: #A6E3A1;
                color: #11111B;
                font-weight: bold;
                font-size: 13px;
                padding: 10px 20px;
                border: none;
                border-radius: 6px;
            }
            QPushButton.success-btn:hover {
                background-color: #94E2D5;
            }
            QPushButton.danger-btn {
                background-color: #F38BA8;
                color: #11111B;
                font-weight: bold;
                padding: 8px 14px;
                border: none;
                border-radius: 6px;
            }
            QPushButton.danger-btn:hover {
                background-color: #EBA0AC;
            }
            QTableWidget {
                background-color: #181825;
                color: #CDD6F4;
                border: 1px solid #313244;
                border-radius: 8px;
                gridline-color: #252637;
            }
            QTableWidget::item {
                padding: 8px;
            }
            QTableWidget::item:selected {
                background-color: #313244;
                color: #89B4FA;
            }
            QHeaderView::section {
                background-color: #252637;
                color: #A6ADC8;
                font-weight: bold;
                padding: 8px;
                border: none;
                border-bottom: 1px solid #313244;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        # 1. TÍTULO E SUBTÍTULO
        header_layout = QVBoxLayout()
        header_layout.setSpacing(2)
        lbl_title = QLabel("📥 Importar PDFs em Lote")
        lbl_title.setProperty("class", "title")
        lbl_subtitle = QLabel("Adicione múltiplos PDFs e associe-os a uma matéria para processamento automático.")
        lbl_subtitle.setProperty("class", "subtitle")
        header_layout.addWidget(lbl_title)
        header_layout.addWidget(lbl_subtitle)
        layout.addLayout(header_layout)

        # 2. SELEÇÃO E CRIAÇÃO RÁPIDA DE MATÉRIA
        subj_card = QFrame()
        subj_card.setStyleSheet("background-color: #252637; border-radius: 8px; padding: 6px;")
        subj_card_layout = QHBoxLayout(subj_card)
        subj_card_layout.setContentsMargins(10, 6, 10, 6)

        lbl_subj = QLabel("Matéria Alvo:")
        lbl_subj.setStyleSheet("color: #CDD6F4; font-weight: bold; font-size: 13px;")
        subj_card_layout.addWidget(lbl_subj)

        self.cmb_subject = QComboBox()
        subj_card_layout.addWidget(self.cmb_subject, stretch=3)

        btn_new_subject = QPushButton("➕ Nova Matéria")
        btn_new_subject.setProperty("class", "secondary-btn")
        btn_new_subject.setCursor(Qt.PointingHandCursor)
        btn_new_subject.clicked.connect(self.create_new_subject)
        subj_card_layout.addWidget(btn_new_subject, stretch=1)

        layout.addWidget(subj_card)

        # 3. ÁREA DE DRAG & DROP
        self.drop_area = QLabel("📄 Arraste e solte seus arquivos PDF aqui\nou clique no botão para navegar")
        self.drop_area.setAlignment(Qt.AlignCenter)
        self.set_drop_area_style(active=False)
        layout.addWidget(self.drop_area)

        # Botão para Navegar pelos Arquivos
        btn_browse = QPushButton("📁 Selecionar PDFs do Computador...")
        btn_browse.setProperty("class", "secondary-btn")
        btn_browse.setCursor(Qt.PointingHandCursor)
        btn_browse.clicked.connect(self.browse_files)
        layout.addWidget(btn_browse)

        # 4. CABEÇALHO DA TABELA + CONTADOR DE ARQUIVOS
        table_header_layout = QHBoxLayout()
        self.lbl_queue_count = QLabel("Fila de Importação (0 arquivos)")
        self.lbl_queue_count.setStyleSheet("color: #A6ADC8; font-weight: bold; font-size: 13px;")
        table_header_layout.addWidget(self.lbl_queue_count)
        table_header_layout.addStretch()
        layout.addLayout(table_header_layout)

        # TABELA
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Nome do Arquivo", "Páginas", "Tamanho"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        layout.addWidget(self.table)

        # 5. AÇÕES DA FILA
        action_layout = QHBoxLayout()

        btn_remove = QPushButton("❌ Remover Selecionado")
        btn_remove.setProperty("class", "danger-btn")
        btn_remove.setCursor(Qt.PointingHandCursor)
        btn_remove.clicked.connect(self.remove_selected_file)
        action_layout.addWidget(btn_remove)

        btn_clear = QPushButton("🗑️ Limpar Lista")
        btn_clear.setProperty("class", "secondary-btn")
        btn_clear.setCursor(Qt.PointingHandCursor)
        btn_clear.clicked.connect(self.clear_all_files)
        action_layout.addWidget(btn_clear)

        action_layout.addStretch()

        self.btn_proceed = QPushButton("Avançar para Revisão dos PDFs ➔")
        self.btn_proceed.setProperty("class", "success-btn")
        self.btn_proceed.setCursor(Qt.PointingHandCursor)
        self.btn_proceed.clicked.connect(self.proceed)
        action_layout.addWidget(self.btn_proceed)

        layout.addLayout(action_layout)

        self.refresh_subjects()

    def set_drop_area_style(self, active=False):
        """Alterna o estilo visual da caixa de drag and drop quando o usuário arrasta algo por cima."""
        if active:
            self.drop_area.setStyleSheet("""
                QLabel {
                    border: 2px dashed #89B4FA;
                    border-radius: 10px;
                    padding: 24px;
                    background-color: #252637;
                    color: #89B4FA;
                    font-size: 14px;
                    font-weight: bold;
                }
            """)
        else:
            self.drop_area.setStyleSheet("""
                QLabel {
                    border: 2px dashed #45475A;
                    border-radius: 10px;
                    padding: 24px;
                    background-color: #181825;
                    color: #A6ADC8;
                    font-size: 13px;
                }
            """)

    def refresh_subjects(self):
        current_id = self.cmb_subject.currentData()
        self.cmb_subject.clear()
        
        with SessionLocal() as db:
            subjects = db.query(Subject).all()
            selected_index = 0
            
            for idx, s in enumerate(subjects):
                self.cmb_subject.addItem(s.name, s.id)
                if current_id and s.id == current_id:
                    selected_index = idx

            if subjects:
                self.cmb_subject.setCurrentIndex(selected_index)

    def create_new_subject(self):
        text, ok = QInputDialog.getText(self, "Nova Matéria", "Nome da Matéria:")
        if ok and text.strip():
            with SessionLocal() as db:
                try:
                    new_subj = Subject(name=text.strip())
                    db.add(new_subj)
                    db.commit()
                    db.refresh(new_subj)
                    
                    self.refresh_subjects()
                    index = self.cmb_subject.findData(new_subj.id)
                    if index >= 0:
                        self.cmb_subject.setCurrentIndex(index)
                except Exception:
                    QMessageBox.warning(self, "Erro", "Matéria já existente ou inválida.")

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if any(u.toLocalFile().lower().endswith('.pdf') for u in urls):
                self.set_drop_area_style(active=True)
                event.acceptProposedAction()

    def dragLeaveEvent(self, event):
        self.set_drop_area_style(active=False)

    def dropEvent(self, event):
        self.set_drop_area_style(active=False)
        files = [u.toLocalFile() for u in event.mimeData().urls() if u.toLocalFile().lower().endswith('.pdf')]
        
        total_dropped = len(event.mimeData().urls())
        if len(files) < total_dropped:
            QMessageBox.information(
                self, "Filtro de Arquivos", 
                "Alguns arquivos foram ignorados por não estarem no formato PDF."
            )
            
        if files:
            self.add_files(files)

    def browse_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Selecionar PDFs", "", "Arquivos PDF (*.pdf)"
        )
        if files:
            self.add_files(files)

    def add_files(self, files):
        for f in files:
            if not f.lower().endswith('.pdf'):
                continue

            if f not in self.selected_files:
                try:
                    info = PDFParser.get_info(f)
                    
                    self.selected_files.append(f)
                    row = self.table.rowCount()
                    self.table.insertRow(row)

                    item_title = QTableWidgetItem(info['title'])
                    item_pages = QTableWidgetItem(str(info['pages']))
                    item_pages.setTextAlignment(Qt.AlignCenter)

                    size_mb = f"{info['size_bytes'] / (1024*1024):.2f} MB"
                    item_size = QTableWidgetItem(size_mb)
                    item_size.setTextAlignment(Qt.AlignCenter)

                    self.table.setItem(row, 0, item_title)
                    self.table.setItem(row, 1, item_pages)
                    self.table.setItem(row, 2, item_size)
                
                except Exception as e:
                    file_name = os.path.basename(f)
                    QMessageBox.warning(
                        self, "Erro ao carregar PDF", 
                        f"Não foi possível ler o arquivo '{file_name}'. Ele pode estar protegido ou corrompido.\n\nDetalhes: {str(e)}"
                    )

        self.update_queue_label()

    def remove_selected_file(self):
        current_row = self.table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "Aviso", "Selecione uma linha na tabela para remover.")
            return

        del self.selected_files[current_row]
        self.table.removeRow(current_row)
        self.update_queue_label()

    def clear_all_files(self):
        self.selected_files.clear()
        self.table.setRowCount(0)
        self.update_queue_label()

    def update_queue_label(self):
        count = len(self.selected_files)
        self.lbl_queue_count.setText(f"Fila de Importação ({count} arquivo{'s' if count != 1 else ''})")

    def proceed(self):
        if not self.selected_files:
            QMessageBox.warning(self, "Aviso", "Selecione pelo menos um PDF na lista.")
            return
        if self.cmb_subject.currentIndex() < 0:
            QMessageBox.warning(self, "Aviso", "Cadastre ou selecione uma matéria primeiro.")
            return

        subject_id = self.cmb_subject.currentData()
        self.import_requested.emit(self.selected_files.copy(), subject_id)
        # self.clear_all_files()

    def showEvent(self, event):
        super().showEvent(event)
        self.refresh_subjects()