from PySide6.QtWidgets import (QWidget, QVBoxLayout, QPushButton, QFileDialog, 
                             QMessageBox, QLabel, QInputDialog, QGroupBox)
from PySide6.QtCore import Qt, Signal
from services.backup_manager import BackupManager
from database.connection import SessionLocal
from models.models import Subject, PdfDocument, Topic, StudyBlock, StudySession, StudyCycle, Highlight, Note


class SettingsView(QWidget):
    app_reset = Signal()

    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)

        # Título
        lbl_title = QLabel("⚙️ Configurações & Backup")
        lbl_title.setStyleSheet("color: #FFFFFF; font-size: 20px; font-weight: bold;")
        layout.addWidget(lbl_title)

        # Grupo: Backup e Restauração
        group_backup = QGroupBox("Gestão de Dados")
        group_backup.setStyleSheet("""
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
        backup_layout = QVBoxLayout(group_backup)
        backup_layout.setSpacing(10)

        btn_export = QPushButton("📦 Exportar Backup (.zip)")
        btn_export.setStyleSheet("""
            QPushButton {
                background-color: #2C3E50;
                color: #ECF0F1;
                font-weight: bold;
                padding: 10px;
                border: 1px solid #34495E;
                border-radius: 5px;
            }
            QPushButton:hover { background-color: #34495E; }
        """)
        btn_export.setCursor(Qt.PointingHandCursor)
        btn_export.clicked.connect(self.export_backup)
        backup_layout.addWidget(btn_export)

        btn_import = QPushButton("📥 Importar Backup (.zip)")
        btn_import.setStyleSheet("""
            QPushButton {
                background-color: #2C3E50;
                color: #ECF0F1;
                font-weight: bold;
                padding: 10px;
                border: 1px solid #34495E;
                border-radius: 5px;
            }
            QPushButton:hover { background-color: #34495E; }
        """)
        btn_import.setCursor(Qt.PointingHandCursor)
        btn_import.clicked.connect(self.import_backup)
        backup_layout.addWidget(btn_import)

        layout.addWidget(group_backup)

        # Grupo: Zona de Perigo (Reset)
        group_danger = QGroupBox("⚠️ Zona de Perigo")
        group_danger.setStyleSheet("""
            QGroupBox {
                color: #E74C3C;
                font-weight: bold;
                font-size: 14px;
                border: 1px solid #E74C3C;
                border-radius: 8px;
                margin-top: 15px;
                padding: 15px;
                background-color: #1E222A;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 5px;
                color: #E74C3C;
            }
        """)
        danger_layout = QVBoxLayout(group_danger)

        lbl_danger_info = QLabel("Reinicia o banco de dados do EstudoFlow apangando todas as matérias, PDFs, blocos e anotações cadastradas.")
        lbl_danger_info.setStyleSheet("color: #BDC3C7; font-size: 12px; margin-bottom: 5px;")
        lbl_danger_info.setWordWrap(True)
        danger_layout.addWidget(lbl_danger_info)

        btn_reset = QPushButton("💣 Resetar Aplicação Inteira")
        btn_reset.setStyleSheet("""
            QPushButton {
                background-color: #C0392B;
                color: #FFFFFF;
                font-weight: bold;
                padding: 10px;
                border-radius: 5px;
            }
            QPushButton:hover { background-color: #E74C3C; }
        """)
        btn_reset.setCursor(Qt.PointingHandCursor)
        btn_reset.clicked.connect(self.reset_application)
        danger_layout.addWidget(btn_reset)

        layout.addWidget(group_danger)

        layout.addStretch()

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
                QMessageBox.information(self, "Sucesso", "Backup restaurado com sucesso! Reinicie o aplicativo.")
            except Exception as e:
                QMessageBox.critical(self, "Erro", f"Falha ao restaurar: {str(e)}")

    def reset_application(self):
        # PRIMEIRA CONFIRMAÇÃO
        confirm_1 = QMessageBox.warning(
            self,
            "⚠️ Atenção - Reset de Dados",
            "Você tem certeza de que deseja apagar TODOS os dados do aplicativo?\n\n"
            "Essa ação apagará permanentemente todas as suas matérias, histórico de estudo e grifos.",
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
            try:
                db = SessionLocal()
                # Limpeza do banco
                db.query(Highlight).delete()
                db.query(StudySession).delete()
                db.query(StudyBlock).delete()
                db.query(Topic).delete()
                db.query(PdfDocument).delete()
                db.query(StudyCycle).delete()
                db.query(Subject).delete()
                db.query(Note).delete()
                db.commit()
                db.close()

                # EMITE O SINAL DE RESET
                self.app_reset.emit()  # <--- Notifica a MainWindow

                QMessageBox.information(
                    self, 
                    "Aplicação Resetada", 
                    "Todos os dados foram excluídos com sucesso.\nO aplicativo agora está limpo."
                )
            except Exception as e:
                QMessageBox.critical(self, "Erro no Reset", f"Ocorreu uma falha ao limpar o banco: {str(e)}")
        elif ok:
            QMessageBox.warning(self, "Reset Cancelado", "Palavra digitada incorretamente. A operação foi cancelada.")