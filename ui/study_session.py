from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QLabel, QSpinBox, QTextEdit, QMessageBox)
from PySide6.QtCore import QTimer, Signal
from database.connection import SessionLocal
from models.models import StudyBlock
from services.study_manager import StudyManager

class StudySessionView(QWidget):
    finished = Signal()
    canceled = Signal()  # Sinal ao sair sem salvar

    def __init__(self, block_id: int):
        super().__init__()
        self.block_id = block_id
        self.seconds_counter = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_timer)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        db = SessionLocal()
        block = db.query(StudyBlock).filter(StudyBlock.id == self.block_id).first()
        
        if not block:
            db.close()
            return

        self.topic_title = block.topic.title
        self.pdf_path = block.topic.pdf.file_path
        self.start_p = block.current_page
        self.end_p = block.page_end
        db.close()

        # Header Info
        layout.addWidget(QLabel("<h2>Sessão de Estudo</h2>"))
        layout.addWidget(QLabel(f"<b>Tópico:</b> {self.topic_title}"))
        layout.addWidget(QLabel(f"<b>Intervalo Planejado:</b> Pág. {self.start_p} até {self.end_p}"))

        # Cronômetro
        self.lbl_timer = QLabel("00:00:00")
        self.lbl_timer.setStyleSheet("font-size: 32px; font-weight: bold; color: #e74c3c;")
        layout.addWidget(self.lbl_timer)

        # Atualizador de Página Atual
        page_layout = QHBoxLayout()
        page_layout.addWidget(QLabel("Página Parada / Atual:"))
        self.spn_current = QSpinBox()
        self.spn_current.setRange(self.start_p, self.end_p)
        self.spn_current.setValue(self.start_p)
        page_layout.addWidget(self.spn_current)
        layout.addLayout(page_layout)

        # Anotações
        layout.addWidget(QLabel("Observações da Sessão:"))
        self.txt_notes = QTextEdit()
        layout.addWidget(self.txt_notes)

        # Botões de Ação
        btn_layout = QHBoxLayout()

        btn_cancel = QPushButton("❌ Sair sem Salvar")
        btn_cancel.setStyleSheet("background-color: #95a5a6; color: white; padding: 10px;")
        btn_cancel.clicked.connect(self.cancel_session)

        self.btn_pause = QPushButton("Pausar Cronômetro")
        self.btn_pause.clicked.connect(self.toggle_timer)
        
        btn_save = QPushButton("💾 Salvar Progresso e Pausar")
        btn_save.setStyleSheet("background-color: #f39c12; color: white; padding: 10px;")
        btn_save.clicked.connect(lambda: self.save_progress(complete=False))

        btn_complete = QPushButton("✔️ Concluir Bloco")
        btn_complete.setStyleSheet("background-color: #2ecc71; color: white; font-weight: bold; padding: 10px;")
        btn_complete.clicked.connect(lambda: self.save_progress(complete=True))

        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(self.btn_pause)
        btn_layout.addWidget(btn_save)
        btn_layout.addWidget(btn_complete)

        layout.addLayout(btn_layout)

        self.timer.start(1000)

    def update_timer(self):
        self.seconds_counter += 1
        m, s = divmod(self.seconds_counter, 60)
        h, m = divmod(m, 60)
        self.lbl_timer.setText(f"{h:02d}:{m:02d}:{s:02d}")

    def toggle_timer(self):
        if self.timer.isActive():
            self.timer.stop()
            self.btn_pause.setText("Retomar Cronômetro")
        else:
            self.timer.start(1000)
            self.btn_pause.setText("Pausar Cronômetro")

    def cancel_session(self):
        confirm = QMessageBox.question(
            self, "Sair sem Salvar", 
            "Deseja sair sem salvar? Todo o tempo e página anotados nesta sessão serão descartados.",
            QMessageBox.Yes | QMessageBox.No
        )
        if confirm == QMessageBox.Yes:
            self.timer.stop()
            self.canceled.emit()

    def save_progress(self, complete=False):
        self.timer.stop()
        db = SessionLocal()
        try:
            curr_p = self.spn_current.value()
            StudyManager.update_progress(
                db, 
                self.block_id, 
                current_page=curr_p, 
                complete=complete, 
                seconds_added=self.seconds_counter
            )
            # Salvar observações simples
            block = db.query(StudyBlock).filter(StudyBlock.id == self.block_id).first()
            if block and self.txt_notes.toPlainText().strip():
                new_note = self.txt_notes.toPlainText().strip()
                block.notes = f"{block.notes}\n{new_note}" if block.notes else new_note
                db.commit()

            QMessageBox.information(self, "Sucesso", "Progresso registrado com sucesso!")
            self.finished.emit()
        finally:
            db.close()