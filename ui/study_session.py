from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QLabel, QSpinBox, QTextEdit, QMessageBox, QFrame)
from PySide6.QtCore import QTimer, Signal, Qt
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
        layout.setSpacing(15)

        db = SessionLocal()
        try:
            block = db.query(StudyBlock).filter(StudyBlock.id == self.block_id).first()
            
            if not block:
                QMessageBox.critical(self, "Erro", "Bloco de estudo não encontrado.")
                return

            self.topic_title = block.topic.title
            self.subject_name = block.topic.pdf.subject.name
            self.pdf_title = block.topic.pdf.title
            
            # Recupera a página atual salva ou a página inicial do bloco
            self.start_p = block.page_start
            self.end_p = block.page_end
            self.current_p = block.current_page if (block.current_page and block.current_page >= self.start_p) else self.start_p
        finally:
            db.close()

        # 1. Header Card (Informações do Bloco)
        header_card = QFrame()
        header_card.setStyleSheet("""
            QFrame {
                background-color: #1E222A;
                border: 1px solid #2C3E50;
                border-radius: 8px;
                padding: 12px;
            }
            QLabel { color: #ECF0F1; font-size: 13px; }
        """)
        header_layout = QVBoxLayout(header_card)
        
        lbl_title = QLabel(f"<b style='font-size: 16px; color: #3498DB;'>{self.subject_name}</b>")
        lbl_sub = QLabel(f"<b>Tópico:</b> {self.topic_title} <span style='color: #7F8C8D;'>({self.pdf_title})</span>")
        lbl_interval = QLabel(f"<b>Intervalo do Bloco:</b> Páginas {self.start_p} até {self.end_p}")

        header_layout.addWidget(lbl_title)
        header_layout.addWidget(lbl_sub)
        header_layout.addWidget(lbl_interval)
        layout.addWidget(header_card)

        # 2. Cronômetro Central
        timer_container = QFrame()
        timer_container.setStyleSheet("""
            QFrame {
                background-color: #1E222A;
                border: 1px solid #34495E;
                border-radius: 8px;
            }
        """)
        timer_layout = QVBoxLayout(timer_container)
        timer_layout.setAlignment(Qt.AlignCenter)

        self.lbl_timer = QLabel("00:00:00")
        self.lbl_timer.setStyleSheet("font-size: 42px; font-weight: bold; color: #E74C3C; border: none;")
        timer_layout.addWidget(self.lbl_timer)

        layout.addWidget(timer_container)

        # 3. Atualizador de Página Atual
        page_card = QFrame()
        page_card.setStyleSheet("""
            QFrame {
                background-color: #1E222A;
                border: 1px solid #2C3E50;
                border-radius: 8px;
                padding: 8px;
            }
            QLabel { color: #ECF0F1; font-weight: bold; }
            QSpinBox {
                background-color: #2C3E50;
                color: #FFFFFF;
                border: 1px solid #34495E;
                border-radius: 4px;
                padding: 4px;
                font-size: 14px;
            }
        """)
        page_layout = QHBoxLayout(page_card)
        
        lbl_page = QLabel("Página Parada / Atual:")
        self.spn_current = QSpinBox()
        self.spn_current.setRange(self.start_p, self.end_p)
        self.spn_current.setValue(self.current_p)
        
        page_layout.addWidget(lbl_page)
        page_layout.addWidget(self.spn_current)
        layout.addWidget(page_card)

        # 4. Campo de Anotações/Observações
        lbl_notes = QLabel("Observações da Sessão:")
        lbl_notes.setStyleSheet("color: #BDC3C7; font-weight: bold;")
        layout.addWidget(lbl_notes)

        self.txt_notes = QTextEdit()
        self.txt_notes.setPlaceholderText("Digite anotações ou insights rápidos desta sessão...")
        self.txt_notes.setStyleSheet("""
            QTextEdit {
                background-color: #1E222A;
                color: #ECF0F1;
                border: 1px solid #2C3E50;
                border-radius: 6px;
                padding: 8px;
            }
        """)
        layout.addWidget(self.txt_notes)

        # 5. Botões de Ação
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        btn_cancel = QPushButton("❌ Sair sem Salvar")
        btn_cancel.setCursor(Qt.PointingHandCursor)
        btn_cancel.setStyleSheet("""
            QPushButton { background-color: #7F8C8D; color: white; padding: 10px; border-radius: 5px; font-weight: bold; }
            QPushButton:hover { background-color: #95A5A6; }
        """)
        btn_cancel.clicked.connect(self.cancel_session)

        self.btn_pause = QPushButton("⏸️ Pausar Cronômetro")
        self.btn_pause.setCursor(Qt.PointingHandCursor)
        self.btn_pause.setStyleSheet("""
            QPushButton { background-color: #34495E; color: white; padding: 10px; border-radius: 5px; font-weight: bold; }
            QPushButton:hover { background-color: #4E657A; }
        """)
        self.btn_pause.clicked.connect(self.toggle_timer)
        
        btn_save = QPushButton("💾 Salvar e Pausar")
        btn_save.setCursor(Qt.PointingHandCursor)
        btn_save.setStyleSheet("""
            QPushButton { background-color: #E67E22; color: white; padding: 10px; border-radius: 5px; font-weight: bold; }
            QPushButton:hover { background-color: #D35400; }
        """)
        btn_save.clicked.connect(lambda: self.save_progress(complete=False))

        btn_complete = QPushButton("✔️ Concluir Bloco")
        btn_complete.setCursor(Qt.PointingHandCursor)
        btn_complete.setStyleSheet("""
            QPushButton { background-color: #2ECC71; color: white; padding: 10px; border-radius: 5px; font-weight: bold; }
            QPushButton:hover { background-color: #27AE60; }
        """)
        btn_complete.clicked.connect(lambda: self.save_progress(complete=True))

        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(self.btn_pause)
        btn_layout.addWidget(btn_save)
        btn_layout.addWidget(btn_complete)

        layout.addLayout(btn_layout)

        # Inicia o cronômetro
        self.timer.start(1000)

    def update_timer(self):
        self.seconds_counter += 1
        m, s = divmod(self.seconds_counter, 60)
        h, m = divmod(m, 60)
        self.lbl_timer.setText(f"{h:02d}:{m:02d}:{s:02d}")

    def toggle_timer(self):
        if self.timer.isActive():
            self.timer.stop()
            self.btn_pause.setText("▶️ Retomar Cronômetro")
            self.lbl_timer.setStyleSheet("font-size: 42px; font-weight: bold; color: #F39C12; border: none;")
        else:
            self.timer.start(1000)
            self.btn_pause.setText("⏸️ Pausar Cronômetro")
            self.lbl_timer.setStyleSheet("font-size: 42px; font-weight: bold; color: #E74C3C; border: none;")

    def cancel_session(self):
        was_active = self.timer.isActive()
        self.timer.stop()
        
        confirm = QMessageBox.question(
            self, "Sair sem Salvar", 
            "Deseja sair sem salvar? Todo o tempo e progresso desta sessão serão descartados.",
            QMessageBox.Yes | QMessageBox.No
        )
        if confirm == QMessageBox.Yes:
            self.canceled.emit()
        elif was_active:
            self.timer.start(1000)

    def save_progress(self, complete=False):
        self.timer.stop()
        db = SessionLocal()
        try:
            curr_p = self.spn_current.value()
            
            # Atualiza tempo e status via StudyManager
            StudyManager.update_progress(
                db, 
                self.block_id, 
                current_page=curr_p, 
                complete=complete, 
                seconds_added=self.seconds_counter
            )
            
            # Trata anotações em texto simples no objeto StudyBlock (se o atributo existir como Coluna de texto)
            note_content = self.txt_notes.toPlainText().strip()
            if note_content:
                block = db.query(StudyBlock).filter(StudyBlock.id == self.block_id).first()
                if block and hasattr(block, 'notes') and isinstance(block.notes, str):
                    block.notes = f"{block.notes}\n{note_content}" if block.notes else note_content
                    db.commit()

            QMessageBox.information(self, "Sucesso", "Progresso registrado com sucesso!")
            self.finished.emit()
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Falha ao salvar progresso: {str(e)}")
            self.timer.start(1000)
        finally:
            db.close()