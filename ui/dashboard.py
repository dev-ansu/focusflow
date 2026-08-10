from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QProgressBar, QGroupBox, QMessageBox, QScrollArea, QFrame)
from PySide6.QtCore import Qt, Signal
from database.connection import SessionLocal
from services.study_manager import StudyManager
from models.models import Subject, StudyBlock, BlockStatus, Topic, PdfDocument
from sqlalchemy.sql.expression import func

class DashboardView(QWidget):
    start_study_signal = Signal(int)

    def __init__(self):
        super().__init__()
        self.current_block_id = None
        self.init_ui()

    def _create_kpi_card(self, title: str, initial_val: str = "0"):
        """Cria um card simples de métrica com visual moderno."""
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: #1E222A;
                border: 1px solid #2C3E50;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        layout = QVBoxLayout(card)
        layout.setSpacing(2)
        layout.setContentsMargins(10, 8, 10, 8)

        lbl_title = QLabel(title)
        lbl_title.setStyleSheet("color: #7F8C8D; font-size: 11px; font-weight: bold; border: none;")
        
        lbl_value = QLabel(initial_val)
        lbl_value.setStyleSheet("color: #3498DB; font-size: 18px; font-weight: bold; border: none;")

        layout.addWidget(lbl_title)
        layout.addWidget(lbl_value)
        return card, lbl_value

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # 1. Título Principal
        lbl_app_title = QLabel("ESTUDOFLOW")
        lbl_app_title.setStyleSheet("""
            QLabel {
                color: #FFFFFF;
                font-size: 26px;
                font-weight: bold;
                letter-spacing: 2px;
                margin-bottom: 0px;
            }
        """)
        layout.addWidget(lbl_app_title)

        # 2. FEATURE NOVA: Linha de KPIs / Estatísticas Rápidas
        kpi_layout = QHBoxLayout()
        kpi_layout.setSpacing(10)

        self.card_pages, self.lbl_kpi_pages = self._create_kpi_card("📄 PÁGINAS LIDAS")
        self.card_blocks, self.lbl_kpi_blocks = self._create_kpi_card("🧩 BLOCOS CONCLUÍDOS")
        self.card_overall, self.lbl_kpi_overall = self._create_kpi_card("🎯 PROGRESSO GERAL")
  
        self.card_time, self.lbl_kpi_time = self._create_kpi_card("⏳ TEMPO ESTIMADO")

        kpi_layout.addWidget(self.card_pages)
        kpi_layout.addWidget(self.card_blocks)
        kpi_layout.addWidget(self.card_overall)
        kpi_layout.addWidget(self.card_time)

        layout.addLayout(kpi_layout)

        
        

        # 3. Card Continuar (Recomendação Geral)
        self.continue_card = QGroupBox("▶ CONTINUAR CICLO PRINCIPAL")
        self.continue_card.setStyleSheet("""
            QGroupBox {
                color: #3498DB;
                font-weight: bold;
                font-size: 14px;
                border: 2px solid #3498DB;
                border-radius: 8px;
                margin-top: 5px;
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

        # 4. Seção de Progresso por Matéria
        prog_group = QGroupBox("Seleção Direta por Matéria")
        prog_group.setStyleSheet("""
            QGroupBox {
                color: #BDC3C7;
                font-weight: bold;
                font-size: 14px;
                border: 1px solid #34495E;
                border-radius: 8px;
                margin-top: 5px;
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

        # --- Na construção da UI (init_ui) ---
        quick_actions_layout = QHBoxLayout()
        quick_actions_layout.setSpacing(8)

        # 1. Bloco Curto
        btn_short_block = QPushButton("⚡ Bloco Curto")
        btn_short_block.setCursor(Qt.PointingHandCursor)
        btn_short_block.setStyleSheet("""
            QPushButton {
                background-color: #34495E; color: #ECF0F1; 
                padding: 6px; border-radius: 4px; font-weight: bold; font-size: 11px;
            }
            QPushButton:hover { background-color: #4E657A; }
        """)
        btn_short_block.clicked.connect(self.start_short_block)

        # 2. Bloco Longo (Novo!)
        btn_long_block = QPushButton("🐘 Bloco Longo")
        btn_long_block.setCursor(Qt.PointingHandCursor)
        btn_long_block.setStyleSheet("""
            QPushButton {
                background-color: #34495E; color: #ECF0F1; 
                padding: 6px; border-radius: 4px; font-weight: bold; font-size: 11px;
            }
            QPushButton:hover { background-color: #4E657A; }
        """)
        btn_long_block.clicked.connect(self.start_long_block)

        # 3. Bloco Aleatório
        btn_random_block = QPushButton("🎲 Aleatório")
        btn_random_block.setCursor(Qt.PointingHandCursor)
        btn_random_block.setStyleSheet("""
            QPushButton {
                background-color: #34495E; color: #ECF0F1; 
                padding: 6px; border-radius: 4px; font-weight: bold; font-size: 11px;
            }
            QPushButton:hover { background-color: #4E657A; }
        """)
        btn_random_block.clicked.connect(self.start_random_block)

        # Adiciona os 3 botões lado a lado
        quick_actions_layout.addWidget(btn_short_block)
        quick_actions_layout.addWidget(btn_long_block)
        quick_actions_layout.addWidget(btn_random_block)

        card_layout.addLayout(quick_actions_layout)

                # Botão para retomar estudo que ficou pela metade
        self.btn_resume_last = QPushButton("🔄 Retomar De Onde Parou")
        self.btn_resume_last.setCursor(Qt.PointingHandCursor)
        self.btn_resume_last.setStyleSheet("""
            QPushButton {
                background-color: #E67E22;
                color: #FFFFFF;
                font-weight: bold;
                font-size: 12px;
                padding: 8px;
                border-radius: 5px;
                margin-top: 5px;
            }
            QPushButton:hover {
                background-color: #D35400;
            }
            QPushButton:disabled {
                background-color: #7F8C8D;
                color: #BDC3C7;
            }
        """)
        self.btn_resume_last.clicked.connect(self.start_in_progress_block)

        # Adiciona no card_layout (acima das ações rápidas)
        card_layout.addWidget(self.btn_resume_last)

        self.scroll_content = QWidget()
        self.scroll_content.setStyleSheet("background-color: transparent;")
        self.prog_layout = QVBoxLayout(self.scroll_content)
        self.prog_layout.setContentsMargins(0, 0, 5, 0)
        self.prog_layout.setSpacing(10)
        
        self.scroll_area.setWidget(self.scroll_content)
        group_layout.addWidget(self.scroll_area)

        layout.addWidget(prog_group)

        self.refresh()
    
    def start_in_progress_block(self):
        """Abre direto o último bloco que ficou no meio do caminho."""
        db = SessionLocal()
        try:
            block = (
                db.query(StudyBlock)
                .filter(StudyBlock.status == BlockStatus.EM_ANDAMENTO)
                .order_by(StudyBlock.id.desc())
                .first()
            )
            if block:
                self.start_study_signal.emit(block.id)
            else:
                QMessageBox.information(self, "Aviso", "Não há estudos em andamento para retomar.")
        finally:
            db.close()

    def start_long_block(self):
        """Busca o bloco pendente com maior número de páginas para sessões intensas."""
        db = SessionLocal()
        try:
            block = (
                db.query(StudyBlock)
                .filter(StudyBlock.status == BlockStatus.PENDENTE)
                # Ordena do maior número de páginas para o menor (.desc())
                .order_by((StudyBlock.page_end - StudyBlock.page_start).desc())
                .first()
            )
            if block:
                self.start_study_signal.emit(block.id)
            else:
                QMessageBox.information(self, "Aviso", "Não há blocos pendentes disponíveis.")
        finally:
            db.close()

    def start_short_block(self):
        """Busca o menor bloco pendente disponível."""
        db = SessionLocal()
        try:
            block = (
                db.query(StudyBlock)
                .filter(StudyBlock.status == BlockStatus.PENDENTE)
                .order_by((StudyBlock.page_end - StudyBlock.page_start).asc())
                .first()
            )
            if block:
                self.start_study_signal.emit(block.id)
            else:
                QMessageBox.information(self, "Aviso", "Não há blocos pendentes disponíveis.")
        finally:
            db.close()

    def start_random_block(self):
        """Busca um bloco pendente aleatório para variar o estudo."""
        db = SessionLocal()
        try:
            block = (
                db.query(StudyBlock)
                .filter(StudyBlock.status == BlockStatus.PENDENTE)
                .order_by(func.random())  # func.rand() se for SQLite/PostgreSQL
                .first()
            )
            if block:
                self.start_study_signal.emit(block.id)
            else:
                QMessageBox.information(self, "Aviso", "Não há blocos pendentes disponíveis.")
        finally:
            db.close()

    def refresh(self):
        db = SessionLocal()
        try:

            

            in_progress_block = (
                db.query(StudyBlock)
                .filter(StudyBlock.status == BlockStatus.EM_ANDAMENTO)
                .order_by(StudyBlock.id.desc()) # Pega o mais recente
                .first()
            )

            if in_progress_block:
                page = in_progress_block.current_page or in_progress_block.page_start
                self.btn_resume_last.setEnabled(True)
                self.btn_resume_last.setText(f"🔄 Retomar {in_progress_block.topic.title} (Pág. {page})")
            else:
                self.btn_resume_last.setEnabled(False)
                self.btn_resume_last.setText("🔄 Nenhum Estudo Interrompido")
            # --- CÁLCULO DAS MÉTRICAS GERAIS (NOVA FEATURE) ---
            all_blocks = db.query(StudyBlock).all()
            total_b = len(all_blocks)
            
            
            done_b_list = [b for b in all_blocks if b.status == BlockStatus.CONCLUIDO]
            done_b = len(done_b_list)

            # No método refresh(), ao calcular o progresso geral:
            pending_b = total_b - done_b
            estimated_hours = round((pending_b * 25) / 60, 1)

            # Se você criou os cards de estatística no topo:
            self.lbl_kpi_time.setText(f"~{estimated_hours}h restantes")

            # Soma de páginas lidas nos blocos concluídos
            pages_read = sum((b.page_end - b.page_start + 1) for b in done_b_list)
            overall_pct = int((done_b / total_b) * 100) if total_b > 0 else 0

            self.lbl_kpi_pages.setText(f"{pages_read} pág(s)")
            self.lbl_kpi_blocks.setText(f"{done_b} / {total_b}")
            self.lbl_kpi_overall.setText(f"{overall_pct}%")

            # 1. Atualiza o bloco recomendado
            next_block = (
                db.query(StudyBlock)
                .join(Topic)
                .join(PdfDocument)
                .filter(StudyBlock.status.in_([BlockStatus.EM_ANDAMENTO, BlockStatus.PENDENTE]))
                .order_by(
                    StudyBlock.status == BlockStatus.PENDENTE,
                    Topic.order.asc(),
                    StudyBlock.id.asc()
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

            # 2. Renderiza a lista por matéria
            for i in reversed(range(self.prog_layout.count())): 
                item = self.prog_layout.itemAt(i)
                if item.widget():
                    item.widget().deleteLater()

            subjects = db.query(Subject).all()
            for s in subjects:
                sub_total = db.query(StudyBlock).join(Topic).join(PdfDocument).filter(PdfDocument.subject_id == s.id).count()
                sub_done = db.query(StudyBlock).join(Topic).join(PdfDocument).filter(
                    PdfDocument.subject_id == s.id,
                    StudyBlock.status == BlockStatus.CONCLUIDO
                ).count()

                pct = int((sub_done / sub_total) * 100) if sub_total > 0 else 0

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
                
                if sub_total == 0:
                    btn_study_subj.setDisabled(True)
                    btn_study_subj.setText("Sem Blocos")
                elif sub_done == sub_total:
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
        db = SessionLocal()
        try:
            block = (
                db.query(StudyBlock)
                .join(Topic)
                .join(PdfDocument)
                .filter(PdfDocument.subject_id == subject_id, StudyBlock.status == BlockStatus.EM_ANDAMENTO)
                .order_by(Topic.order.asc(), StudyBlock.id.asc())
                .first()
            )
            
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