from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QProgressBar, QGroupBox, QMessageBox, QScrollArea)
from PySide6.QtCore import Qt, Signal
from database.connection import SessionLocal
from services.study_manager import StudyManager
from models.models import Subject, StudyBlock, BlockStatus, Topic, PdfDocument

class DashboardView(QWidget):
    start_study_signal = Signal(int) # Emite o ID do bloco para iniciar

    def __init__(self):
        super().__init__()
        self.current_block_id = None
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(20)

        # Título Principal do EstudoFlow
        lbl_app_title = QLabel("ESTUDOFLOW")
        lbl_app_title.setStyleSheet("""
            QLabel {
                color: #FFFFFF;
                font-size: 26px;
                font-weight: bold;
                letter-spacing: 2px;
                margin-bottom: 5px;
            }
        """)
        layout.addWidget(lbl_app_title)

        # Card Continuar (Recomendação Geral)
        self.continue_card = QGroupBox("▶ CONTINUAR CICLO PRINCIPAL")
        self.continue_card.setStyleSheet("""
            QGroupBox {
                color: #3498DB;
                font-weight: bold;
                font-size: 14px;
                border: 2px solid #3498DB;
                border-radius: 8px;
                margin-top: 10px;
                padding: 15px;
                background-color: #2C3E50;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 5px;
                color: #3498DB;
            }
        """)
        card_layout = QVBoxLayout(self.continue_card)

        # Informações do Bloco (Matéria, Tópico e Páginas)
        self.lbl_info = QLabel("Nenhum estudo em andamento ou pendente.")
        self.lbl_info.setStyleSheet("""
            QLabel {
                font-size: 15px;
                color: #ECF0F1;
                line-height: 1.4;
            }
        """)
        self.lbl_info.setWordWrap(True)
        card_layout.addWidget(self.lbl_info)

        self.btn_start = QPushButton("COMEÇAR RECOMENDADO")
        self.btn_start.setStyleSheet("""
            QPushButton {
                background-color: #2ECC71;
                color: #FFFFFF;
                font-weight: bold;
                font-size: 14px;
                padding: 10px;
                border-radius: 5px;
                margin-top: 10px;
            }
            QPushButton:hover {
                background-color: #27AE60;
            }
        """)
        self.btn_start.setCursor(Qt.PointingHandCursor)
        self.btn_start.clicked.connect(self.on_start_clicked)
        card_layout.addWidget(self.btn_start)

        layout.addWidget(self.continue_card)

        # Seção de Progresso por Matéria
        prog_group = QGroupBox("Seleção Direta por Matéria")
        prog_group.setStyleSheet("""
            QGroupBox {
                color: #BDC3C7;
                font-weight: bold;
                font-size: 14px;
                border: 1px solid #34495E;
                border-radius: 8px;
                margin-top: 10px;
                padding: 15px;
                background-color: #1E222A;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 5px;
                color: #BDC3C7;
            }
        """)
        group_layout = QVBoxLayout(prog_group)

        # QScrollArea para acomodar muitas matérias sem achatar
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                border: none;
                background: #1E222A;
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: #34495E;
                border-radius: 4px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: #4E657A;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                border: none;
                background: none;
            }
        """)

        # Container interno do Scroll
        self.scroll_content = QWidget()
        self.scroll_content.setStyleSheet("background-color: transparent;")
        self.prog_layout = QVBoxLayout(self.scroll_content)
        self.prog_layout.setContentsMargins(0, 0, 5, 0)
        self.prog_layout.setSpacing(10)
        
        self.scroll_area.setWidget(self.scroll_content)
        group_layout.addWidget(self.scroll_area)

        layout.addWidget(prog_group)

        self.refresh()

    def refresh(self):
        db = SessionLocal()
        try:
            # 1. Atualiza o bloco recomendado ordenando pelo campo 'order' do Tópico
            # (Em vez de buscar apenas o padrão, garantimos a sequência pela hierarquia)
            next_block = (
                db.query(StudyBlock)
                .join(Topic)
                .join(PdfDocument)
                .filter(StudyBlock.status.in_([BlockStatus.EM_ANDAMENTO, BlockStatus.PENDENTE]))
                .order_by(
                    # Dá prioridade ao bloco que já começou
                    StudyBlock.status == BlockStatus.PENDENTE,  # EM_ANDAMENTO vem primeiro (False < True)
                    Topic.order.asc(),                          # Respeita a ordem cadastrada
                    StudyBlock.id.asc()                         # Desempate pelo ID
                )
                .first()
            )

            if next_block:
                self.current_block_id = next_block.id
                subj_name = next_block.topic.pdf.subject.name
                pdf_title = next_block.topic.pdf.title
                topic_title = next_block.topic.title
                
                p_start = next_block.current_page if (next_block.current_page and next_block.current_page > 0) else next_block.page_start
                p_end = next_block.page_end

                self.lbl_info.setText(
                    f"<b>Matéria:</b> {subj_name}<br>"
                    f"<b>Tópico:</b> {topic_title} ({pdf_title})<br>"
                    f"<b>Páginas:</b> {p_start} até {p_end}"
                )
                self.btn_start.setEnabled(True)
            else:
                self.current_block_id = None
                self.lbl_info.setText("Parabéns! Todos os blocos cadastrados foram concluídos.")
                self.btn_start.setEnabled(False)

            # 2. Limpa e renderiza a lista por matéria (continua idêntico)
            for i in reversed(range(self.prog_layout.count())): 
                item = self.prog_layout.itemAt(i)
                if item.widget():
                    item.widget().deleteLater()

            subjects = db.query(Subject).all()
            for s in subjects:
                total_blocks = db.query(StudyBlock).join(Topic).join(PdfDocument).filter(PdfDocument.subject_id == s.id).count()
                done_blocks = db.query(StudyBlock).join(Topic).join(PdfDocument).filter(
                    PdfDocument.subject_id == s.id,
                    StudyBlock.status == BlockStatus.CONCLUIDO
                ).count()

                pct = int((done_blocks / total_blocks) * 100) if total_blocks > 0 else 0

                row = QHBoxLayout()
                
                lbl = QLabel(s.name)
                lbl.setMinimumWidth(150)
                lbl.setStyleSheet("font-weight: bold; color: #ECF0F1;")
                row.addWidget(lbl)
                
                bar = QProgressBar()
                bar.setValue(pct)
                bar.setStyleSheet("""
                    QProgressBar {
                        border: 1px solid #34495E;
                        border-radius: 5px;
                        text-align: center;
                        color: #FFFFFF;
                        background-color: #2C3E50;
                        height: 20px;
                    }
                    QProgressBar::chunk {
                        background-color: #2ECC71;
                        border-radius: 4px;
                    }
                """)
                row.addWidget(bar)
                
                btn_study_subj = QPushButton("Estudar ➔")
                btn_study_subj.setCursor(Qt.PointingHandCursor)
                btn_study_subj.setStyleSheet("""
                    QPushButton {
                        background-color: #3498DB; 
                        color: white; 
                        font-weight: bold; 
                        padding: 5px 12px; 
                        border-radius: 4px;
                    }
                    QPushButton:hover {
                        background-color: #2980B9;
                    }
                    QPushButton:disabled {
                        background-color: #7F8C8D;
                        color: #BDC3C7;
                    }
                """)
                
                if total_blocks == 0:
                    btn_study_subj.setDisabled(True)
                    btn_study_subj.setText("Sem Blocos")
                elif done_blocks == total_blocks:
                    btn_study_subj.setDisabled(True)
                    btn_study_subj.setText("Concluído")
                else:
                    btn_study_subj.clicked.connect(lambda checked=False, subj_id=s.id: self.start_subject_study(subj_id))

                row.addWidget(btn_study_subj)
                
                container = QWidget()
                container.setLayout(row)
                self.prog_layout.addWidget(container)

            self.prog_layout.addStretch()

        finally:
            db.close()

    def start_subject_study(self, subject_id):
        """Busca o próximo bloco pendente/em andamento DESTA matéria seguindo a ordem dos tópicos."""
        db = SessionLocal()
        try:
            # Primeiro tenta pegar um bloco que já esteja EM ANDAMENTO nessa matéria
            block = (
                db.query(StudyBlock)
                .join(Topic)
                .join(PdfDocument)
                .filter(PdfDocument.subject_id == subject_id, StudyBlock.status == BlockStatus.EM_ANDAMENTO)
                .order_by(Topic.order.asc(), StudyBlock.id.asc())
                .first()
            )
            
            # Se não houver nenhum em andamento, pega o primeiro PENDENTE na ordem dos tópicos
            if not block:
                block = (
                    db.query(StudyBlock)
                    .join(Topic)
                    .join(PdfDocument)
                    .filter(PdfDocument.subject_id == subject_id, StudyBlock.status == BlockStatus.PENDENTE)
                    .order_by(Topic.order.asc(), StudyBlock.id.asc())
                    .first()
                )

            if block:
                self.start_study_signal.emit(block.id)
            else:
                QMessageBox.information(self, "Aviso", "Não há blocos pendentes para esta matéria.")
        finally:
            db.close()

    def on_start_clicked(self):
        if self.current_block_id:
            self.start_study_signal.emit(self.current_block_id)