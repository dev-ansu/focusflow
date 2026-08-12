import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QFileDialog, 
    QMessageBox, QLabel, QInputDialog, QGroupBox, QSpinBox, 
    QComboBox, QFrame, QScrollArea
)
from PySide6.QtCore import Qt, Signal, QSettings
from services.backup_manager import BackupManager
from database.connection import SessionLocal
from models.models import (
    Subject, PdfDocument, Topic, StudyBlock, StudySession, 
    StudyCycle, Highlight, Note, QuestionError
)


class SettingsView(QWidget):
    app_reset = Signal()

    def __init__(self):
        super().__init__()
        self.settings = QSettings("EstudoFlow", "Preferences")
        self.init_ui()
        self.refresh_stats()

    def showEvent(self, event):
        """Garante que os estatísticas e os cards sejam atualizados ao visualizar a tela."""
        super().showEvent(event)
        self.refresh_stats()

    def init_ui(self):
        self.setStyleSheet("""
            QWidget {
                background-color: #1E1E2E;
                color: #CDD6F4;
                font-family: 'Segoe UI', system-ui, sans-serif;
            }
            QGroupBox {
                color: #89B4FA;
                font-weight: bold;
                font-size: 14px;
                border: 1px solid #313244;
                border-radius: 8px;
                margin-top: 10px;
                padding: 15px;
                background-color: #252637;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 6px;
                color: #89B4FA;
            }
            QPushButton.action-btn {
                background-color: #313244;
                color: #CDD6F4;
                font-weight: bold;
                padding: 10px;
                border: 1px solid #45475A;
                border-radius: 6px;
            }
            QPushButton.action-btn:hover {
                background-color: #45475A;
                color: #89B4FA;
            }
            QPushButton.danger-btn {
                background-color: #F38BA8;
                color: #11111B;
                font-weight: bold;
                padding: 10px;
                border: none;
                border-radius: 6px;
            }
            QPushButton.danger-btn:hover {
                background-color: #EBA0AC;
            }
            QSpinBox, QComboBox {
                background-color: #181825;
                border: 1px solid #313244;
                border-radius: 6px;
                padding: 6px;
                color: #CDD6F4;
            }
            QLabel.stat-card {
                background-color: #181825;
                border: 1px solid #313244;
                border-radius: 6px;
                padding: 10px;
                font-size: 13px;
            }
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)

        # Scroll Area para o caso de telas menores
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        scroll_content = QWidget()
        layout = QVBoxLayout(scroll_content)
        layout.setSpacing(16)

        # ---------------- 1. TÍTULO DA PÁGINA ----------------
        lbl_title = QLabel("⚙️ Configurações & Preferências")
        lbl_title.setStyleSheet("color: #89B4FA; font-size: 20px; font-weight: bold;")
        layout.addWidget(lbl_title)

        # ---------------- 2. GRUPO: STATUS DO ARMAZENAMENTO ----------------
        group_stats = QGroupBox("📊 Resumo do Sistema & Banco de Dados")
        stats_layout = QHBoxLayout(group_stats)
        
        self.lbl_stat_subjects = QLabel("📚 Matérias: 0")
        self.lbl_stat_subjects.setProperty("class", "stat-card")
        
        self.lbl_stat_pdfs = QLabel("📄 PDFs: 0")
        self.lbl_stat_pdfs.setProperty("class", "stat-card")

        self.lbl_stat_errors = QLabel("❌ Caderno de Erros: 0")
        self.lbl_stat_errors.setProperty("class", "stat-card")

        self.lbl_stat_notes = QLabel("📝 Anotações: 0")
        self.lbl_stat_notes.setProperty("class", "stat-card")

        stats_layout.addWidget(self.lbl_stat_subjects)
        stats_layout.addWidget(self.lbl_stat_pdfs)
        stats_layout.addWidget(self.lbl_stat_errors)
        stats_layout.addWidget(self.lbl_stat_notes)

        layout.addWidget(group_stats)

        # ---------------- 4. GRUPO: GESTÃO DE DADOS (BACKUP) ----------------
        group_backup = QGroupBox("📦 Gestão de Dados & Backup")
        backup_layout = QVBoxLayout(group_backup)
        backup_layout.setSpacing(10)

        lbl_backup_info = QLabel("Exporte uma cópia completa dos seus PDFs, anotações e progresso para segurança.")
        lbl_backup_info.setStyleSheet("color: #A6ADC8; font-size: 12px;")
        backup_layout.addWidget(lbl_backup_info)

        row_btns = QHBoxLayout()
        btn_export = QPushButton("📤 Exportar Backup (.zip)")
        btn_export.setProperty("class", "action-btn")
        btn_export.setCursor(Qt.PointingHandCursor)
        btn_export.clicked.connect(self.export_backup)

        btn_import = QPushButton("📥 Importar Backup (.zip)")
        btn_import.setProperty("class", "action-btn")
        btn_import.setCursor(Qt.PointingHandCursor)
        btn_import.clicked.connect(self.import_backup)

        row_btns.addWidget(btn_export)
        row_btns.addWidget(btn_import)
        backup_layout.addLayout(row_btns)

        layout.addWidget(group_backup)

        # ---------------- 5. GRUPO: ZONA DE PERIGO ----------------
        group_danger = QGroupBox("⚠️ Zona de Perigo")
        group_danger.setStyleSheet("""
            QGroupBox {
                color: #F38BA8;
                font-weight: bold;
                border: 1px solid #F38BA8;
                border-radius: 8px;
                margin-top: 10px;
                padding: 15px;
                background-color: #252637;
            }
            QGroupBox::title { color: #F38BA8; }
        """)
        danger_layout = QVBoxLayout(group_danger)

        lbl_danger_info = QLabel("Apaga permanentemente todo o banco de dados: Matérias, PDFs, Caderno de Erros, Histórico e Grifos.")
        lbl_danger_info.setStyleSheet("color: #BAC2DE; font-size: 12px;")
        lbl_danger_info.setWordWrap(True)
        danger_layout.addWidget(lbl_danger_info)

        btn_reset = QPushButton("💣 Resetar Aplicação Inteira")
        btn_reset.setProperty("class", "danger-btn")
        btn_reset.setCursor(Qt.PointingHandCursor)
        btn_reset.clicked.connect(self.reset_application)
        danger_layout.addWidget(btn_reset)

        layout.addWidget(group_danger)
        layout.addStretch()

        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll)

    # ---------------- LÓGICA DE DADOS & PREFERÊNCIAS ----------------

    def refresh_stats(self):
        """Atualiza a contagem dos dados salvos no banco."""
        with SessionLocal() as db:
            try:
                subjects_cnt = db.query(Subject).count()
                pdfs_cnt = db.query(PdfDocument).count()
                errors_cnt = db.query(QuestionError).count()
                notes_cnt = db.query(Note).count()

                self.lbl_stat_subjects.setText(f"📚 Matérias: {subjects_cnt}")
                self.lbl_stat_pdfs.setText(f"📄 PDFs: {pdfs_cnt}")
                self.lbl_stat_errors.setText(f"❌ Caderno de Erros: {errors_cnt}")
                self.lbl_stat_notes.setText(f"📝 Anotações: {notes_cnt}")
            except Exception as e:
                print(f"Erro ao carregar estatísticas: {e}")

    def export_backup(self):
        path, _ = QFileDialog.getSaveFileName(self, "Salvar Backup", "estudoflow_backup.zip", "ZIP Files (*.zip)")
        if path:
            try:
                BackupManager.export_backup(path)
                QMessageBox.information(self, "Sucesso", "Backup exportado com sucesso!")
            except Exception as e:
                QMessageBox.critical(self, "Erro", f"Falha ao exportar: {str(e)}")

    def import_backup(self):
        path, _ = QFileDialog.getOpenFileName(self, "Abrir Backup", "", "ZIP Files (*.zip)")
        if path:
            try:
                BackupManager.import_backup(path)
                self.refresh_stats()
                QMessageBox.information(self, "Sucesso", "Backup restaurado com sucesso!")
            except Exception as e:
                QMessageBox.critical(self, "Erro", f"Falha ao restaurar: {str(e)}")

    def reset_application(self):
        # PRIMEIRA CONFIRMAÇÃO
        confirm_1 = QMessageBox.warning(
            self,
            "⚠️ Atenção - Reset de Dados",
            "Você tem certeza de que deseja apagar TODOS os dados do aplicativo?\n\n"
            "Essa ação apagará permanentemente suas matérias, Caderno de Erros, histórico e grifos.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if confirm_1 != QMessageBox.Yes:
            return

        # SEGUNDA CONFIRMAÇÃO (Digitar Palavra Chave)
        text, ok = QInputDialog.getText(
            self,
            "🔒 Dupla Confirmação Exigida",
            "Esta ação é IRREVERSÍVEL!\nPara confirmar o reset, digite a palavra RESETAR abaixo:"
        )

        if ok and text.strip().upper() == "RESETAR":
            with SessionLocal() as db:
                try:
                    # Limpeza completa de todas as tabelas (incluindo QuestionError)
                    db.query(QuestionError).delete()
                    db.query(Highlight).delete()
                    db.query(Note).delete()
                    db.query(StudySession).delete()
                    db.query(StudyBlock).delete()
                    db.query(Topic).delete()
                    db.query(PdfDocument).delete()
                    db.query(StudyCycle).delete()
                    db.query(Subject).delete()
                    
                    db.commit()

                    self.refresh_stats()
                    self.app_reset.emit()  # Notifica MainWindow para redefinir views

                    QMessageBox.information(
                        self, 
                        "Aplicação Resetada", 
                        "Todos os dados foram excluídos com sucesso.\nO EstudoFlow está limpo."
                    )
                except Exception as e:
                    db.rollback()
                    QMessageBox.critical(self, "Erro no Reset", f"Ocorreu uma falha ao limpar o banco: {str(e)}")
        elif ok:
            QMessageBox.warning(self, "Reset Cancelado", "Palavra digitada incorretamente. A operação foi cancelada.")