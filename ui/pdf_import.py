from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QLabel, QFileDialog, QComboBox, QMessageBox, QTableWidget, 
                             QTableWidgetItem, QInputDialog, QHeaderView)
from PySide6.QtCore import Qt, Signal
from database.connection import SessionLocal
from models.models import Subject
from services.pdf_parser import PDFParser

class PDFImportView(QWidget):
    import_requested = Signal(str, int)  # Emite file_path, subject_id

    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.selected_files = []
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)

        lbl_title = QLabel("📥 Importar PDFs de Preparatórios")
        lbl_title.setStyleSheet("color: #FFFFFF; font-size: 20px; font-weight: bold;")
        layout.addWidget(lbl_title)

        # Seleção e Criação Rápida de Matéria
        subj_layout = QHBoxLayout()
        
        lbl_subj = QLabel("Matéria Alvo:")
        lbl_subj.setStyleSheet("color: #BDC3C7; font-weight: bold; font-size: 14px;")
        subj_layout.addWidget(lbl_subj)

        self.cmb_subject = QComboBox()
        self.cmb_subject.setStyleSheet("""
            QComboBox {
                background-color: #1E222A;
                color: #ECF0F1;
                border: 1px solid #34495E;
                border-radius: 5px;
                padding: 6px 10px;
                font-size: 13px;
            }
            QComboBox::drop-down { border: none; }
            QComboBox QAbstractItemView {
                background-color: #1E222A;
                color: #ECF0F1;
                selection-background-color: #34495E;
            }
        """)
        subj_layout.addWidget(self.cmb_subject, stretch=3)

        btn_new_subject = QPushButton("➕ Nova Matéria")
        btn_new_subject.setStyleSheet("""
            QPushButton {
                background-color: #3498DB;
                color: white;
                font-weight: bold;
                padding: 6px 12px;
                border-radius: 5px;
            }
            QPushButton:hover { background-color: #2980B9; }
        """)
        btn_new_subject.setCursor(Qt.PointingHandCursor)
        btn_new_subject.clicked.connect(self.create_new_subject)
        subj_layout.addWidget(btn_new_subject, stretch=1)

        layout.addLayout(subj_layout)

        # Área de Drag & Drop / Botão de Seleção
        self.drop_area = QLabel("Arraste e solte os arquivos PDF aqui\nou clique no botão abaixo")
        self.drop_area.setAlignment(Qt.AlignCenter)
        self.drop_area.setStyleSheet("""
            QLabel {
                border: 2px dashed #34495E;
                border-radius: 10px;
                padding: 25px;
                background-color: #1E222A;
                color: #BDC3C7;
                font-size: 14px;
            }
        """)
        layout.addWidget(self.drop_area)

        btn_browse = QPushButton("📁 Selecionar PDFs do Computador...")
        btn_browse.setStyleSheet("""
            QPushButton {
                background-color: #2C3E50;
                color: #ECF0F1;
                font-weight: bold;
                padding: 8px;
                border: 1px solid #34495E;
                border-radius: 5px;
            }
            QPushButton:hover { background-color: #34495E; }
        """)
        btn_browse.setCursor(Qt.PointingHandCursor)
        btn_browse.clicked.connect(self.browse_files)
        layout.addWidget(btn_browse)

        # Tabela com resumos dos arquivos
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Nome do Arquivo", "Páginas", "Tamanho"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #1E222A;
                color: #ECF0F1;
                border: 1px solid #34495E;
                border-radius: 8px;
                gridline-color: #2C3E50;
            }
            QTableWidget::item { padding: 5px; }
            QTableWidget::item:selected { background-color: #34495E; color: #FFFFFF; }
            QHeaderView::section {
                background-color: #2C3E50;
                color: #BDC3C7;
                font-weight: bold;
                padding: 6px;
                border: none;
            }
        """)
        layout.addWidget(self.table)

        # Ações na Fila (Remover / Prosseguir)
        action_layout = QHBoxLayout()

        btn_remove = QPushButton("❌ Remover PDF Selecionado")
        btn_remove.setStyleSheet("""
            QPushButton {
                background-color: #E74C3C;
                color: white;
                padding: 8px 15px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #C0392B; }
        """)
        btn_remove.setCursor(Qt.PointingHandCursor)
        btn_remove.clicked.connect(self.remove_selected_file)
        action_layout.addWidget(btn_remove)

        action_layout.addStretch()

        self.btn_proceed = QPushButton("Avançar para Detecção de Sumário ➔")
        self.btn_proceed.setStyleSheet("""
            QPushButton {
                background-color: #2ECC71;
                color: white;
                font-weight: bold;
                font-size: 13px;
                padding: 10px 20px;
                border-radius: 5px;
            }
            QPushButton:hover { background-color: #27AE60; }
        """)
        self.btn_proceed.setCursor(Qt.PointingHandCursor)
        self.btn_proceed.clicked.connect(self.proceed)
        action_layout.addWidget(self.btn_proceed)

        layout.addLayout(action_layout)

        self.refresh_subjects()

    def refresh_subjects(self):
        """Recarrega as matérias cadastradas no banco de dados."""
        current_id = self.cmb_subject.currentData()
        self.cmb_subject.clear()
        db = SessionLocal()
        subjects = db.query(Subject).all()
        selected_index = 0
        
        for idx, s in enumerate(subjects):
            self.cmb_subject.addItem(s.name, s.id)
            if current_id and s.id == current_id:
                selected_index = idx

        if subjects:
            self.cmb_subject.setCurrentIndex(selected_index)
        db.close()

    def create_new_subject(self):
        """Permite cadastrar uma nova matéria diretamente da tela de importação."""
        text, ok = QInputDialog.getText(self, "Nova Matéria", "Nome da Matéria:")
        if ok and text.strip():
            db = SessionLocal()
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
            finally:
                db.close()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        files = [u.toLocalFile() for u in event.mimeData().urls() if u.toLocalFile().lower().endswith('.pdf')]
        self.add_files(files)

    def browse_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Selecionar PDFs", "", "Arquivos PDF (*.pdf)")
        if files:
            self.add_files(files)

    def add_files(self, files):
        for f in files:
            if f not in self.selected_files:
                self.selected_files.append(f)
                info = PDFParser.get_info(f)
                row = self.table.rowCount()
                self.table.insertRow(row)
                self.table.setItem(row, 0, QTableWidgetItem(info['title']))
                self.table.setItem(row, 1, QTableWidgetItem(str(info['pages'])))
                size_mb = f"{info['size_bytes'] / (1024*1024):.2f} MB"
                self.table.setItem(row, 2, QTableWidgetItem(size_mb))

    def remove_selected_file(self):
        current_row = self.table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "Aviso", "Selecione uma linha na tabela para remover.")
            return

        del self.selected_files[current_row]
        self.table.removeRow(current_row)

    def proceed(self):
        if not self.selected_files:
            QMessageBox.warning(self, "Aviso", "Selecione pelo menos um PDF na lista.")
            return
        if self.cmb_subject.currentIndex() < 0:
            QMessageBox.warning(self, "Aviso", "Cadastre ou selecione uma matéria primeiro.")
            return

        subject_id = self.cmb_subject.currentData()
        self.import_requested.emit(self.selected_files[0], subject_id)
        
    def showEvent(self, event):
        """Disparado automaticamente sempre que a view é exibida na tela."""
        super().showEvent(event)
        self.refresh_subjects()