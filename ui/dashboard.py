from datetime import datetime, timezone

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy.sql.expression import func

from config.app import config
from database.connection import SessionLocal
from models.models import BlockStatus, PdfDocument, StudyBlock, Subject, Topic
from services.study_manager import StudyManager


class DashboardView(QWidget):
    start_study_signal = Signal(int)

    def __init__(self):
        super().__init__()
        self.current_block_id = None
        self.init_ui()

    def _create_kpi_card(
        self, title: str, initial_val: str = "0", val_color: str = "#89B4FA"
    ):
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: #181825;
                border: 1px solid #313244;
                border-radius: 10px;
                padding: 8px 12px;
            }
        """)
        layout = QVBoxLayout(card)
        layout.setSpacing(2)
        layout.setContentsMargins(12, 10, 12, 10)

        lbl_title = QLabel(title)
        lbl_title.setStyleSheet(
            "color: #A6ADC8; font-size: 11px; font-weight: bold; border: none;"
        )

        lbl_value = QLabel(initial_val)
        lbl_value.setStyleSheet(
            f"color: {val_color}; font-size: 20px; font-weight: bold; border: none;"
        )

        layout.addWidget(lbl_title)
        layout.addWidget(lbl_value)
        return card, lbl_value

    def init_ui(self):
        self.setStyleSheet("""
            QWidget {
                background-color: #1E1E2E;
                color: #CDD6F4;
                font-family: 'Segoe UI', system-ui, sans-serif;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # 1. Título Principal
        lbl_app_title = QLabel(f"⚡ {config.APP_NAME}")
        lbl_app_title.setStyleSheet("""
            QLabel {
                color: #CBA6F7;
                font-size: 24px;
                font-weight: bold;
                letter-spacing: 2px;
            }
        """)
        layout.addWidget(lbl_app_title)

        # 2. Linha de KPIs
        kpi_layout = QHBoxLayout()
        kpi_layout.setSpacing(12)

        self.card_pages, self.lbl_kpi_pages = self._create_kpi_card(
            "📄 PÁGINAS LIDAS", val_color="#89B4FA"
        )
        self.card_blocks, self.lbl_kpi_blocks = self._create_kpi_card(
            "🧩 BLOCOS CONCLUÍDOS", val_color="#A6E3A1"
        )
        self.card_overall, self.lbl_kpi_overall = self._create_kpi_card(
            "🎯 PROGRESSO GERAL", val_color="#F9E2AF"
        )
        self.card_time, self.lbl_kpi_time = self._create_kpi_card(
            "⏳ TEMPO INVESTIDO", val_color="#FAB387"
        )

        kpi_layout.addWidget(self.card_pages)
        kpi_layout.addWidget(self.card_blocks)
        kpi_layout.addWidget(self.card_overall)
        kpi_layout.addWidget(self.card_time)

        layout.addLayout(kpi_layout)

        # 3. Card Continuar
        self.continue_card = QGroupBox("▶ CONTINUAR CICLO DE ESTUDOS")
        self.continue_card.setStyleSheet("""
            QGroupBox {
                color: #89B4FA;
                font-weight: bold;
                font-size: 14px;
                border: 1px solid #313244;
                border-radius: 10px;
                margin-top: 5px;
                padding: 16px;
                background-color: #181825;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 6px;
                color: #89B4FA;
            }
        """)
        card_layout = QVBoxLayout(self.continue_card)
        card_layout.setSpacing(10)

        self.lbl_info = QLabel("Nenhum estudo em andamento ou pendente.")
        self.lbl_info.setStyleSheet(
            "font-size: 14px; color: #CDD6F4; line-height: 1.4;"
        )
        self.lbl_info.setWordWrap(True)
        card_layout.addWidget(self.lbl_info)

        self.btn_start = QPushButton("▶ COMEÇAR RECOMENDADO")
        self.btn_start.setStyleSheet("""
            QPushButton {
                background-color: #A6E3A1;
                color: #11111B;
                font-weight: bold;
                font-size: 13px;
                padding: 10px;
                border-radius: 6px;
                border: none;
            }
            QPushButton:hover { background-color: #94E2D5; }
            QPushButton:disabled { background-color: #313244; color: #585B70; }
        """)
        self.btn_start.setCursor(Qt.PointingHandCursor)
        self.btn_start.clicked.connect(self.on_start_clicked)
        card_layout.addWidget(self.btn_start)

        self.btn_resume_last = QPushButton("🔄 Retomar De Onde Parou")
        self.btn_resume_last.setCursor(Qt.PointingHandCursor)
        self.btn_resume_last.setStyleSheet("""
            QPushButton {
                background-color: #FAB387;
                color: #11111B;
                font-weight: bold;
                font-size: 12px;
                padding: 8px;
                border-radius: 6px;
                border: none;
            }
            QPushButton:hover { background-color: #F9E2AF; }
            QPushButton:disabled { background-color: #313244; color: #585B70; }
        """)
        self.btn_resume_last.clicked.connect(self.start_in_progress_block)
        card_layout.addWidget(self.btn_resume_last)

        quick_actions_layout = QHBoxLayout()
        quick_actions_layout.setSpacing(8)

        btn_style = """
            QPushButton {
                background-color: #313244; color: #CDD6F4; 
                padding: 8px; border-radius: 6px; font-weight: 500; font-size: 12px;
                border: 1px solid #45475A;
            }
            QPushButton:hover { background-color: #45475A; color: #FFFFFF; }
        """

        btn_short_block = QPushButton("⚡ Bloco Curto")
        btn_short_block.setCursor(Qt.PointingHandCursor)
        btn_short_block.setStyleSheet(btn_style)
        btn_short_block.clicked.connect(self.start_short_block)

        btn_long_block = QPushButton("🐘 Bloco Longo")
        btn_long_block.setCursor(Qt.PointingHandCursor)
        btn_long_block.setStyleSheet(btn_style)
        btn_long_block.clicked.connect(self.start_long_block)

        btn_random_block = QPushButton("🎲 Aleatório")
        btn_random_block.setCursor(Qt.PointingHandCursor)
        btn_random_block.setStyleSheet(btn_style)
        btn_random_block.clicked.connect(self.start_random_block)

        quick_actions_layout.addWidget(btn_short_block)
        quick_actions_layout.addWidget(btn_long_block)
        quick_actions_layout.addWidget(btn_random_block)

        card_layout.addLayout(quick_actions_layout)
        layout.addWidget(self.continue_card)

        # 4. Seção de Progresso por Matéria
        prog_group = QGroupBox("📚 Seleção Direta por Matéria")
        prog_group.setStyleSheet("""
            QGroupBox {
                color: #BAC2DE;
                font-weight: bold;
                font-size: 14px;
                border: 1px solid #313244;
                border-radius: 10px;
                margin-top: 5px;
                padding: 16px;
                background-color: #181825;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 6px;
                color: #BAC2DE;
            }
        """)
        group_layout = QVBoxLayout(prog_group)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("""
            QScrollArea { border: none; background-color: transparent; }
            QScrollBar:vertical {
                border: none;
                background: #181825;
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: #313244;
                border-radius: 4px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover { background: #45475A; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { border: none; background: none; }
        """)

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
                QMessageBox.information(
                    self, "Aviso", "Não há estudos em andamento para retomar."
                )
        finally:
            db.close()

    def _start_block_by_query(self, query):
        db = SessionLocal()
        try:
            block = query.first()
            if block:
                # Transiciona e atualiza horários usando UTC
                block.status = BlockStatus.EM_ANDAMENTO
                if not block.started_at:
                    block.started_at = datetime.now(timezone.utc)
                db.commit()

                self.start_study_signal.emit(block.id)
            else:
                QMessageBox.information(
                    self, "Aviso", "Não há blocos pendentes disponíveis."
                )
        except Exception as e:
            db.rollback()
            if config.DEBUG:
                print(
                    f"[{config.APP_NAME}] Erro ao iniciar bloco por consulta: {e}"
                )
            QMessageBox.critical(self, "Erro", f"Erro ao iniciar bloco: {e}")
        finally:
            db.close()

    def start_short_block(self):
        db = SessionLocal()
        try:
            q = (
                db.query(StudyBlock)
                .filter(StudyBlock.status == BlockStatus.PENDENTE)
                .order_by((StudyBlock.page_end - StudyBlock.page_start).asc())
            )
            self._start_block_by_query(q)
        finally:
            db.close()

    def start_long_block(self):
        db = SessionLocal()
        try:
            q = (
                db.query(StudyBlock)
                .filter(StudyBlock.status == BlockStatus.PENDENTE)
                .order_by((StudyBlock.page_end - StudyBlock.page_start).desc())
            )
            self._start_block_by_query(q)
        finally:
            db.close()

    def start_random_block(self):
        db = SessionLocal()
        try:
            q = (
                db.query(StudyBlock)
                .filter(StudyBlock.status == BlockStatus.PENDENTE)
                .order_by(func.random())
            )
            self._start_block_by_query(q)
        finally:
            db.close()

    def refresh(self):
        db = SessionLocal()
        try:
            # 1. Bloco em Andamento
            in_progress_block = (
                db.query(StudyBlock)
                .filter(StudyBlock.status == BlockStatus.EM_ANDAMENTO)
                .order_by(StudyBlock.id.desc())
                .first()
            )

            if in_progress_block:
                page = (
                    in_progress_block.current_page
                    or in_progress_block.page_start
                )
                self.btn_resume_last.setEnabled(True)
                self.btn_resume_last.setText(
                    f"🔄 Retomar {in_progress_block.topic.title} (Pág. {page})"
                )
            else:
                self.btn_resume_last.setEnabled(False)
                self.btn_resume_last.setText("🔄 Nenhum Estudo Interrompido")

            # 2. Métricas Gerais
            all_blocks = db.query(StudyBlock).all()
            total_b = len(all_blocks)
            done_b_list = [
                b for b in all_blocks if b.status == BlockStatus.CONCLUIDO
            ]
            done_b = len(done_b_list)

            pages_read = sum(
                (b.page_end - b.page_start + 1) for b in done_b_list
            )
            overall_pct = int((done_b / total_b) * 100) if total_b > 0 else 0

            total_seconds = sum(b.time_spent_seconds or 0 for b in all_blocks)
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            seconds = total_seconds % 60

            if hours > 0:
                time_str = f"{hours}h {minutes}m"
            elif minutes > 0:
                time_str = f"{minutes}m {seconds}s"
            else:
                time_str = f"{seconds}s"

            self.lbl_kpi_pages.setText(f"{pages_read} pág(s)")
            self.lbl_kpi_blocks.setText(f"{done_b} / {total_b}")
            self.lbl_kpi_overall.setText(f"{overall_pct}%")
            self.lbl_kpi_time.setText(time_str)

            # 3. Bloco Recomendado (Delegado para o StudyManager)
            last_completed = (
                db.query(PdfDocument.subject_id, StudyBlock.id, StudyBlock.completed_at)
                .join(Topic, Topic.pdf_id == PdfDocument.id)
                .join(StudyBlock, StudyBlock.topic_id == Topic.id)
                .filter(StudyBlock.status == BlockStatus.CONCLUIDO)
                .order_by(StudyBlock.completed_at.desc(), StudyBlock.id.desc())
                .first()
            )

            print("\n" + "="*30)
            print("🔍 DEBUG DO CICLO")
            print("Último Bloco Concluído (Subject ID, Block ID, Completed At):", last_completed)

            if last_completed:
                last_subj_id = last_completed[0]
                print(f"-> ID da Última Matéria Concluída: {last_subj_id}")
            else:
                last_subj_id = None
                print("-> Nenhum bloco concluído foi encontrado no banco!")

            # ATRIBUIÇÃO CORRETA DA VARIÁVEL EXPECTIDA NA TELA: next_block
            next_block = StudyManager.get_next_block_to_study(db, last_subject_id=last_subj_id)
            
            if next_block:
                print(f"-> Próximo Bloco Selecionado (ID): {next_block.id}")
                print(f"-> Matéria do Próximo Bloco (Subject ID): {next_block.topic.pdf.subject_id}")
            else:
                print("-> Nenhum próximo bloco pendente foi retornado!")
            print("="*30 + "\n")

            # Exibição do Bloco Recomendado na UI
            all_subjects_count = db.query(Subject).count()

            if (
                next_block
                and next_block.topic
                and next_block.topic.pdf
                and next_block.topic.pdf.subject
            ):
                self.current_block_id = next_block.id
                subj_name = next_block.topic.pdf.subject.name
                pdf_title = next_block.topic.pdf.title
                topic_title = next_block.topic.title

                p_start = (
                    next_block.current_page
                    if (
                        next_block.current_page
                        and next_block.current_page > 0
                    )
                    else next_block.page_start
                )
                p_end = next_block.page_end

                self.lbl_info.setText(
                    f"<b>Matéria:</b> {subj_name}<br>"
                    f"<b>Tópico:</b> {topic_title} ({pdf_title})<br>"
                    f"<b>Páginas:</b> {p_start} até {p_end}"
                )
                self.btn_start.setEnabled(True)
            else:
                self.current_block_id = None
                if all_subjects_count == 0:
                    self.lbl_info.setText(
                        "Nenhuma matéria ou tópico cadastrado. Cadastre matérias para iniciar o ciclo."
                    )
                else:
                    self.lbl_info.setText(
                        "Parabéns! Todos os blocos cadastrados foram concluídos."
                    )

                self.btn_start.setEnabled(False)

            # 4. Limpeza da Lista por Matéria
            while self.prog_layout.count():
                item = self.prog_layout.takeAt(0)
                widget = item.widget()
                if widget:
                    widget.deleteLater()

            # 5. Renderização das Matérias
            subjects = (
                db.query(Subject)
                .order_by(Subject.order.asc(), Subject.id.asc())
                .all()
            )
            for s in subjects:
                sub_total = (
                    db.query(StudyBlock)
                    .join(Topic)
                    .join(PdfDocument)
                    .filter(PdfDocument.subject_id == s.id)
                    .count()
                )
                sub_done = (
                    db.query(StudyBlock)
                    .join(Topic)
                    .join(PdfDocument)
                    .filter(
                        PdfDocument.subject_id == s.id,
                        StudyBlock.status == BlockStatus.CONCLUIDO,
                    )
                    .count()
                )

                pct = int((sub_done / sub_total) * 100) if sub_total > 0 else 0

                container = QWidget()
                row = QHBoxLayout(container)
                row.setContentsMargins(0, 0, 0, 0)
                row.setSpacing(12)

                lbl = QLabel(s.name)
                lbl.setMinimumWidth(160)
                lbl.setStyleSheet(
                    "font-weight: bold; color: #CDD6F4; font-size: 13px;"
                )
                row.addWidget(lbl)

                bar = QProgressBar()
                bar.setValue(pct)
                bar.setStyleSheet("""
                    QProgressBar {
                        border: 1px solid #313244;
                        border-radius: 6px;
                        text-align: center;
                        color: #CDD6F4;
                        background-color: #11111B;
                        height: 22px;
                        font-weight: bold;
                        font-size: 11px;
                    }
                    QProgressBar::chunk {
                        background-color: #A6E3A1;
                        border-radius: 5px;
                    }
                """)
                row.addWidget(bar)

                btn_study_subj = QPushButton("Estudar ➔")
                btn_study_subj.setCursor(Qt.PointingHandCursor)
                btn_study_subj.setStyleSheet("""
                    QPushButton {
                        background-color: #89B4FA; 
                        color: #11111B; 
                        font-weight: bold; 
                        padding: 6px 14px; 
                        border-radius: 6px;
                        border: none;
                    }
                    QPushButton:hover { background-color: #B4BEFE; }
                    QPushButton:disabled { background-color: #313244; color: #585B70; }
                """)

                if sub_total == 0:
                    btn_study_subj.setDisabled(True)
                    btn_study_subj.setText("Sem Blocos")
                elif sub_done == sub_total:
                    btn_study_subj.setDisabled(True)
                    btn_study_subj.setText("Concluído")
                else:
                    btn_study_subj.clicked.connect(
                        lambda checked=False, s_id=s.id: self.start_subject_study(
                            s_id
                        )
                    )

                row.addWidget(btn_study_subj)
                self.prog_layout.addWidget(container)

            self.prog_layout.addStretch()

        finally:
            db.close()

    def start_subject_study(self, subject_id: int):
        db = SessionLocal()
        try:
            block = (
                db.query(StudyBlock)
                .join(Topic)
                .join(PdfDocument)
                .filter(
                    PdfDocument.subject_id == subject_id,
                    StudyBlock.status == BlockStatus.EM_ANDAMENTO,
                )
                .order_by(Topic.order.asc(), StudyBlock.id.asc())
                .first()
            )

            if not block:
                block = (
                    db.query(StudyBlock)
                    .join(Topic)
                    .join(PdfDocument)
                    .filter(
                        PdfDocument.subject_id == subject_id,
                        StudyBlock.status == BlockStatus.PENDENTE,
                    )
                    .order_by(Topic.order.asc(), StudyBlock.id.asc())
                    .first()
                )

            if block:
                # Transiciona status antes de iniciar
                if block.status == BlockStatus.PENDENTE:
                    block.status = BlockStatus.EM_ANDAMENTO
                    if not block.started_at:
                        block.started_at = datetime.now(timezone.utc)
                    db.commit()

                self.start_study_signal.emit(block.id)
            else:
                QMessageBox.information(
                    self,
                    "Aviso",
                    "Não há blocos pendentes para esta matéria.",
                )
        except Exception as e:
            db.rollback()
            if config.DEBUG:
                print(f"[{config.APP_NAME}] Erro ao iniciar estudo por matéria: {e}")
        finally:
            db.close()

    def on_start_clicked(self):
        if self.current_block_id:
            db = SessionLocal()
            try:
                block = (
                    db.query(StudyBlock)
                    .filter(StudyBlock.id == self.current_block_id)
                    .first()
                )
                if block:
                    if block.status == BlockStatus.PENDENTE:
                        block.status = BlockStatus.EM_ANDAMENTO
                        if not block.started_at:
                            block.started_at = datetime.now(timezone.utc)
                        db.commit()

                    self.start_study_signal.emit(block.id)
            except Exception as e:
                db.rollback()
                if config.DEBUG:
                    print(
                        f"[{config.APP_NAME}] Erro ao iniciar bloco recomendado: {e}"
                    )
            finally:
                db.close()