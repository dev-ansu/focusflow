import os
import shutil
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QFileDialog, 
    QMessageBox, QLabel, QInputDialog, QGroupBox, QFrame, 
    QScrollArea, QTableWidget, QTableWidgetItem, QHeaderView
)
from PySide6.QtCore import Qt, Signal, QSettings
from services.backup_manager import BackupManager
from database.connection import SessionLocal
from models.models import (
    Subject, PdfDocument, Topic, StudyBlock, StudySession, 
    StudyCycle, Highlight, Note, QuestionError
)
from config.app import config

class SettingsView(QWidget):
    app_reset = Signal()

    def __init__(self):
        super().__init__()
        self.settings = QSettings(f"{config.APP_NAME}", "Preferences")
        self.init_ui()
        self.refresh_stats()
        self.refresh_backups_table()

    def showEvent(self, event):
        """Atualiza estatísticas e a tabela de backups ao visualizar a tela."""
        super().showEvent(event)
        self.refresh_stats()
        self.refresh_backups_table()

    def get_backup_folder(self) -> str:
        """Retorna o diretório de backup configurado ou o padrão da aplicação."""
        default_dir = str(config.BACKUP_DIR)
        return self.settings.value("custom_backup_dir", default_dir, type=str)

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
                padding: 8px 12px;
                border: 1px solid #45475A;
                border-radius: 6px;
            }
            QPushButton.action-btn:hover {
                background-color: #45475A;
                color: #89B4FA;
            }
            QPushButton.primary-btn {
                background-color: #89B4FA;
                color: #11111B;
                font-weight: bold;
                padding: 8px 14px;
                border: none;
                border-radius: 6px;
            }
            QPushButton.primary-btn:hover {
                background-color: #B4BEFE;
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
            QLabel.stat-card {
                background-color: #181825;
                border: 1px solid #313244;
                border-radius: 6px;
                padding: 10px;
                font-size: 13px;
            }
            QTableWidget {
                background-color: #181825;
                border: 1px solid #313244;
                border-radius: 6px;
                gridline-color: #313244;
            }
            QHeaderView::section {
                background-color: #313244;
                color: #CDD6F4;
                padding: 6px;
                font-weight: bold;
                border: none;
            }
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        scroll_content = QWidget()
        layout = QVBoxLayout(scroll_content)
        layout.setSpacing(16)

        # 1. TÍTULO
        lbl_title = QLabel("⚙️ Configurações & Preferências")
        lbl_title.setStyleSheet("color: #89B4FA; font-size: 20px; font-weight: bold;")
        layout.addWidget(lbl_title)

        # 2. STATUS DO ARMAZENAMENTO
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

        # 3. GESTÃO DE BACKUPS & TABELA
        group_backup = QGroupBox("📦 Gestão de Backups")
        backup_layout = QVBoxLayout(group_backup)
        backup_layout.setSpacing(12)

        # Diretório Atual de Backup
        dir_layout = QHBoxLayout()
        self.lbl_dir = QLabel(f"📂 Diretório Atual: {self.get_backup_folder()}")
        self.lbl_dir.setStyleSheet("color: #A6ADC8; font-size: 12px;")
        
        btn_change_dir = QPushButton("📁 Alterar Pasta")
        btn_change_dir.setProperty("class", "action-btn")
        btn_change_dir.setCursor(Qt.PointingHandCursor)
        btn_change_dir.clicked.connect(self.select_custom_backup_folder)

        dir_layout.addWidget(self.lbl_dir, stretch=1)
        dir_layout.addWidget(btn_change_dir)
        backup_layout.addLayout(dir_layout)

        # Botões Principais de Backup
        row_btns = QHBoxLayout()
        
        btn_create = QPushButton("⚡ Gerar Novo Backup Agora")
        btn_create.setProperty("class", "primary-btn")
        btn_create.setCursor(Qt.PointingHandCursor)
        btn_create.clicked.connect(self.create_backup)

        btn_import = QPushButton("📥 Importar Backup (.zip)")
        btn_import.setProperty("class", "action-btn")
        btn_import.setCursor(Qt.PointingHandCursor)
        btn_import.clicked.connect(self.import_backup)

        row_btns.addWidget(btn_create)
        row_btns.addWidget(btn_import)
        backup_layout.addLayout(row_btns)

        # Tabela de Backups Existentes
        self.table_backups = QTableWidget()
        self.table_backups.setColumnCount(4)
        self.table_backups.setHorizontalHeaderLabels(["Nome do Arquivo", "Data", "Tamanho", "Ação"])
        self.table_backups.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table_backups.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table_backups.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table_backups.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table_backups.setMinimumHeight(200)

        backup_layout.addWidget(self.table_backups)
        layout.addWidget(group_backup)

        # 4. ZONA DE PERIGO
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

    # ---------------- LÓGICA DE DADOS & BACKUP ----------------

    def refresh_stats(self):
        """Atualiza a contagem dos dados salvos no banco."""
        with SessionLocal() as db:
            try:
                self.lbl_stat_subjects.setText(f"📚 Matérias: {db.query(Subject).count()}")
                self.lbl_stat_pdfs.setText(f"📄 PDFs: {db.query(PdfDocument).count()}")
                self.lbl_stat_errors.setText(f"❌ Caderno de Erros: {db.query(QuestionError).count()}")
                self.lbl_stat_notes.setText(f"📝 Anotações: {db.query(Note).count()}")
            except Exception as e:
                print(f"Erro ao carregar estatísticas: {e}")

    def select_custom_backup_folder(self):
        """Permite que o usuário defina uma pasta personalizada de backups."""
        folder = QFileDialog.getExistingDirectory(self, "Selecionar Pasta de Backups", self.get_backup_folder())
        if folder:
            self.settings.setValue("custom_backup_dir", folder)
            self.lbl_dir.setText(f"📂 Diretório Atual: {folder}")
            self.refresh_backups_table()

    def refresh_backups_table(self):
        """Carrega e exibe os arquivos .zip contidos na pasta de backups."""
        backup_dir = self.get_backup_folder()
        os.makedirs(backup_dir, exist_ok=True)

        files = [f for f in os.listdir(backup_dir) if f.endswith('.zip')]
        files.sort(key=lambda f: os.path.getmtime(os.path.join(backup_dir, f)), reverse=True)

        # Alterado para 5 colunas para acomodar o botão de exclusão
        self.table_backups.setColumnCount(5)
        self.table_backups.setHorizontalHeaderLabels(["Nome do Arquivo", "Data", "Tamanho", "Download", "Ação"])
        self.table_backups.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table_backups.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table_backups.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table_backups.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table_backups.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        
        self.table_backups.setRowCount(len(files))

        for row, filename in enumerate(files):
            file_path = os.path.join(backup_dir, filename)
            stat = os.stat(file_path)

            size_mb = f"{stat.st_size / (1024 * 1024):.2f} MB"
            date_str = datetime.fromtimestamp(stat.st_mtime).strftime("%d/%m/%Y %H:%M")

            item_name = QTableWidgetItem(filename)
            item_date = QTableWidgetItem(date_str)
            item_size = QTableWidgetItem(size_mb)

            item_name.setFlags(item_name.flags() ^ Qt.ItemIsEditable)
            item_date.setFlags(item_date.flags() ^ Qt.ItemIsEditable)
            item_size.setFlags(item_size.flags() ^ Qt.ItemIsEditable)

            self.table_backups.setItem(row, 0, item_name)
            self.table_backups.setItem(row, 1, item_date)
            self.table_backups.setItem(row, 2, item_size)

            # Botão de Download
            btn_download = QPushButton("💾 Baixar")
            btn_download.setProperty("class", "action-btn")
            btn_download.setCursor(Qt.PointingHandCursor)
            btn_download.clicked.connect(lambda _, path=file_path: self.download_backup(path))
            self.table_backups.setCellWidget(row, 3, btn_download)

            # Botão de Excluir Backup
            btn_delete = QPushButton("🗑️ Apagar")
            btn_delete.setProperty("class", "danger-btn")
            btn_delete.setStyleSheet("padding: 4px 8px; font-size: 11px;")
            btn_delete.setCursor(Qt.PointingHandCursor)
            btn_delete.clicked.connect(lambda _, path=file_path, name=filename: self.delete_backup(path, name))
            self.table_backups.setCellWidget(row, 4, btn_delete)

    def delete_backup(self, file_path: str, filename: str):
        """Solicita confirmação e apaga permanentemente o arquivo de backup selecionado."""
        confirm = QMessageBox.question(
            self,
            "Confirmar Exclusão",
            f"Tem certeza de que deseja apagar o backup:\n'{filename}'?\n\nEsta ação não poderá ser desfeita.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if confirm == QMessageBox.Yes:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    self.refresh_backups_table()
                    QMessageBox.information(self, "Sucesso", "Arquivo de backup removido com sucesso!")
            except Exception as e:
                QMessageBox.critical(self, "Erro", f"Falha ao apagar o arquivo: {str(e)}")

    def create_backup(self):
        """Cria o arquivo ZIP e armazena na pasta de backups do sistema."""
        backup_dir = self.get_backup_folder()
        os.makedirs(backup_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{config.APP_NAME}_backup_{timestamp}.zip"
        target_path = os.path.join(backup_dir, filename)

        try:
            BackupManager.export_backup(target_path)
            self.refresh_backups_table()
            QMessageBox.information(self, "Sucesso", f"Backup gerado com sucesso em:\n{target_path}")
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Falha ao gerar backup: {str(e)}")

    def download_backup(self, source_path: str):
        """Permite que o usuário salve uma cópia do backup em outro diretório."""
        filename = os.path.basename(source_path)
        dest_path, _ = QFileDialog.getSaveFileName(self, "Salvar Backup Como...", filename, "ZIP Files (*.zip)")
        
        if dest_path:
            try:
                shutil.copy2(source_path, dest_path)
                QMessageBox.information(self, "Sucesso", "Backup salvo com sucesso na pasta selecionada!")
            except Exception as e:
                QMessageBox.critical(self, "Erro", f"Falha ao salvar o backup: {str(e)}")

    def import_backup(self):
        """Restaura um arquivo de backup (.zip)."""
        path, _ = QFileDialog.getOpenFileName(self, "Selecionar Backup para Importar", "", "ZIP Files (*.zip)")
        if path:
            try:
                BackupManager.import_backup(path)
                self.refresh_stats()
                self.refresh_backups_table()
                QMessageBox.information(self, "Sucesso", "Backup restaurado com sucesso!")
            except Exception as e:
                QMessageBox.critical(self, "Erro", f"Falha ao restaurar: {str(e)}")

    def reset_application(self):
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

        text, ok = QInputDialog.getText(
            self,
            "🔒 Dupla Confirmação Exigida",
            "Esta ação é IRREVERSÍVEL!\nPara confirmar o reset, digite a palavra RESETAR abaixo:"
        )

        if ok and text.strip().upper() == "RESETAR":
            with SessionLocal() as db:
                try:
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
                    self.refresh_backups_table()
                    self.app_reset.emit()

                    QMessageBox.information(
                        self, 
                        "Aplicação Resetada", 
                        f"Todos os dados foram excluídos com sucesso.\nO {config.APP_NAME} está limpo."
                    )
                except Exception as e:
                    db.rollback()
                    QMessageBox.critical(self, "Erro no Reset", f"Ocorreu uma falha ao limpar o banco: {str(e)}")
        elif ok:
            QMessageBox.warning(self, "Reset Cancelado", "Palavra digitada incorretamente. A operação foi cancelada.")