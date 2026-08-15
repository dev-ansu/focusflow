import os
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QFileDialog, 
    QMessageBox, QLabel, QInputDialog, QGroupBox, QFrame, 
    QScrollArea, QTableWidget, QTableWidgetItem, QHeaderView,
    QCheckBox, QTabWidget, QSpinBox
)
from PySide6.QtCore import Qt, Signal, QSettings, QThread

from services.backup_manager import BackupManager
from database.connection import SessionLocal, engine
from models.models import (
    Base, Subject, PdfDocument, Topic, StudyBlock, StudySession, 
    StudyCycle, Highlight, Note, QuestionError
)
from config.app import config
from services.gdrive_sync import GDriveSyncService
from services.updater import (
    get_current_version, UpdateCheckerWorker, 
    download_and_prepare_update, launch_updater_script_and_exit
)
from services.updater import is_frozen


def safe_replace_file(src_path: str | Path, dst_path: str | Path, max_retries: int = 5, delay: float = 0.2):
    """
    Substitui um arquivo tentando repetidamente caso o Windows mantenha o lock no SQLite.
    """
    src = Path(src_path)
    dst = Path(dst_path)

    for attempt in range(max_retries):
        try:
            shutil.copy(src, dst)
            return True
        except PermissionError:
            if attempt == max_retries - 1:
                raise PermissionError(
                    f"Não foi possível substituir o arquivo '{dst.name}'. "
                    "O banco de dados ainda está em uso pelo sistema. Tente novamente."
                )
            time.sleep(delay)

class DownloadWorker(QThread):
    """Worker dedicado para baixar o arquivo sem travar a UI."""
    progress_signal = Signal(int)
    finished_signal = Signal(object)  # Path da pasta extraída
    error_signal = Signal(str)

    def __init__(self, download_url: str):
        super().__init__()
        self.download_url = download_url

    def run(self):
        try:
            extracted_dir = download_and_prepare_update(self.download_url, self.progress_signal)
            self.finished_signal.emit(extracted_dir)
        except Exception as e:
            self.error_signal.emit(str(e))

class OAuthWorker(QThread):
    finished_signal = Signal(bool, str)

    def __init__(self, gdrive_service):
        super().__init__()
        self.gdrive_service = gdrive_service

    def run(self):
        try:
            success = self.gdrive_service.authenticate()
            self.finished_signal.emit(success, "")
        except Exception as e:
            self.finished_signal.emit(False, str(e))


class SettingsView(QWidget):
    app_reset = Signal()

    def __init__(self):
        super().__init__()
        self.settings = QSettings(f"{config.APP_NAME}", "Preferences")
        self.gdrive_service = GDriveSyncService()
        self.init_ui()
        self.refresh_stats()
        self.refresh_backups_table()

    def showEvent(self, event):
        super().showEvent(event)
        self.refresh_stats()
        self.refresh_backups_table()

    def get_backup_folder(self) -> str:
        default_dir = str(config.BACKUP_DIR)
        saved_dir = self.settings.value("custom_backup_dir", None, type=str)
        
        if saved_dir and ("estudoflow" in saved_dir or not os.path.exists(saved_dir)):
            self.settings.remove("custom_backup_dir")
            return default_dir

        return saved_dir if saved_dir else default_dir

    def init_ui(self):
        self.setStyleSheet("""
            QWidget {
                background-color: #1E1E2E;
                color: #CDD6F4;
                font-family: 'Segoe UI', system-ui, sans-serif;
            }
            QTabWidget::pane {
                border: 1px solid #313244;
                border-radius: 8px;
                background-color: #1E1E2E;
                top: -1px;
            }
            QTabBar::tab {
                background-color: #181825;
                color: #A6ADC8;
                padding: 8px 16px;
                border: 1px solid #313244;
                border-bottom: none;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                margin-right: 4px;
                font-weight: bold;
            }
            QTabBar::tab:selected {
                background-color: #252637;
                color: #89B4FA;
                border-bottom: 2px solid #89B4FA;
            }
            QTabBar::tab:hover:!selected {
                background-color: #313244;
                color: #CDD6F4;
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
                padding: 6px 12px;
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
                padding: 8px 12px;
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
            QSpinBox {
                background-color: #181825;
                color: #CDD6F4;
                border: 1px solid #45475A;
                border-radius: 4px;
                padding: 4px;
            }
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)

        # 1. TÍTULO
        lbl_title = QLabel("⚙️ Configurações & Preferências")
        lbl_title.setStyleSheet("color: #89B4FA; font-size: 20px; font-weight: bold; margin-bottom: 8px;")
        main_layout.addWidget(lbl_title)

        # 2. SISTEMA DE ABAS (QTabWidget)
        self.tabs = QTabWidget()
        
        # --- ABA 1: Geral, Nuvem & Backups ---
        tab_general = QWidget()
        tab_general_layout = QVBoxLayout(tab_general)
        
        scroll_general = QScrollArea()
        scroll_general.setWidgetResizable(True)
        scroll_general.setFrameShape(QFrame.NoFrame)

        scroll_content_general = QWidget()
        layout_general = QVBoxLayout(scroll_content_general)
        layout_general.setSpacing(16)


        # Sincronização em Nuvem
        group_cloud = QGroupBox("☁️ Sincronização em Nuvem (Google Drive)")
        cloud_layout = QVBoxLayout(group_cloud)
        cloud_layout.setSpacing(10)

        self.lbl_cloud_status = QLabel("Status: Desconectado")
        self.lbl_cloud_status.setStyleSheet("color: #A6ADC8; font-size: 12px;")
        cloud_layout.addWidget(self.lbl_cloud_status)

        row_cloud_btns = QHBoxLayout()

        self.btn_google_auth = QPushButton("🔑 Conectar Conta Google")
        self.btn_google_auth.setProperty("class", "action-btn")
        self.btn_google_auth.setCursor(Qt.PointingHandCursor)
        self.btn_google_auth.clicked.connect(self.toggle_google_auth)

        self.btn_cloud_upload = QPushButton("☁️ Enviando BD p/ Nuvem")
        self.btn_cloud_upload.setProperty("class", "primary-btn")
        self.btn_cloud_upload.setCursor(Qt.PointingHandCursor)
        self.btn_cloud_upload.clicked.connect(self.upload_to_cloud)

        self.btn_cloud_download = QPushButton("📲 Baixar BD da Nuvem")
        self.btn_cloud_download.setProperty("class", "action-btn")
        self.btn_cloud_download.setCursor(Qt.PointingHandCursor)
        self.btn_cloud_download.clicked.connect(self.download_from_cloud)

        row_cloud_btns.addWidget(self.btn_google_auth)
        row_cloud_btns.addWidget(self.btn_cloud_upload)
        row_cloud_btns.addWidget(self.btn_cloud_download)
        cloud_layout.addLayout(row_cloud_btns)

        layout_general.addWidget(group_cloud)

        # Status do Armazenamento
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
        layout_general.addWidget(group_stats)

        # Gestão de Backups
        group_backup = QGroupBox("📦 Gestão de Backups")
        backup_layout = QVBoxLayout(group_backup)
        backup_layout.setSpacing(12)

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

        row_btns = QHBoxLayout()
        btn_create = QPushButton("⚡ Gerar Novo Backup Agora")
        btn_create.setProperty("class", "primary-btn")
        btn_create.setCursor(Qt.PointingHandCursor)
        btn_create.clicked.connect(self.create_backup)

        btn_import = QPushButton("📥 Importar Backup Externo (.zip)")
        btn_import.setProperty("class", "action-btn")
        btn_import.setCursor(Qt.PointingHandCursor)
        btn_import.clicked.connect(self.import_backup)

        row_btns.addWidget(btn_create)
        row_btns.addWidget(btn_import)
        backup_layout.addLayout(row_btns)

        self.table_backups = QTableWidget()
        self.table_backups.setColumnCount(5)
        self.table_backups.setHorizontalHeaderLabels(["Origem", "Nome do Arquivo", "Data", "Tamanho", "Ações"])
        self.table_backups.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table_backups.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table_backups.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table_backups.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table_backups.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.table_backups.setMinimumHeight(220)

        backup_layout.addWidget(self.table_backups)
        layout_general.addWidget(group_backup)

        # Zona de Perigo
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

        lbl_danger_info = QLabel("Apaga permanentemente todo o banco de dados e arquivos locais: Matérias, PDFs, Caderno de Erros, Histórico e Grifos.")
        lbl_danger_info.setStyleSheet("color: #BAC2DE; font-size: 12px;")
        lbl_danger_info.setWordWrap(True)
        danger_layout.addWidget(lbl_danger_info)

        btn_reset = QPushButton("💣 Resetar Aplicação Inteira")
        btn_reset.setProperty("class", "danger-btn")
        btn_reset.setCursor(Qt.PointingHandCursor)
        btn_reset.clicked.connect(self.reset_application)
        danger_layout.addWidget(btn_reset)

        layout_general.addWidget(group_danger)
        layout_general.addStretch()

        scroll_general.setWidget(scroll_content_general)
        tab_general_layout.addWidget(scroll_general)

        # --- ABA 2: Leitor PDF & Atalhos ---
        tab_reader = QWidget()
        tab_reader_layout = QVBoxLayout(tab_reader)

        scroll_reader = QScrollArea()
        scroll_reader.setWidgetResizable(True)
        scroll_reader.setFrameShape(QFrame.NoFrame)

        scroll_content_reader = QWidget()
        layout_reader = QVBoxLayout(scroll_content_reader)
        layout_reader.setSpacing(16)

        # Mapeamento de Atalhos
        shortcuts_group = QGroupBox("⌨️ Mapeamento de Atalhos (Leitor PDF)")
        shortcuts_layout = QVBoxLayout(shortcuts_group)

        shortcuts_data = [
            ("Ctrl + F", "Abre a Busca Global (Command Palette)", "Global"),
            ("F11", "Alterna Modo Foco (Oculta/Exibe painéis)", "Leitor"),
            ("Escape", "Sair do Modo Foco", "Leitor"),
            ("Seta Direita / PgDown", "Próxima Página", "Leitor"),
            ("Seta Esquerda / PgUp", "Página Anterior", "Leitor"),
            ("Ctrl + +", "Ampliar Zoom (Zoom In)", "Leitor"),
            ("Ctrl + -", "Reduzir Zoom (Zoom Out)", "Leitor"),
            ("Ctrl + D", "Alterna Modo Escuro / Claro (Inversão de Matriz)", "Leitor"),
            ("1", "Seleciona cor de grifo: Amarelo (#FFFF00)", "Destaque"),
            ("2", "Seleciona cor de grifo: Verde (#2ECC71)", "Destaque"),
            ("3", "Seleciona cor de grifo: Azul (#3498DB)", "Destaque"),
            ("4", "Seleciona cor de grifo: Rosa (#E91E63)", "Destaque"),
        ]

        table_shortcuts = QTableWidget()
        table_shortcuts.setRowCount(len(shortcuts_data))
        table_shortcuts.setColumnCount(3)
        table_shortcuts.setHorizontalHeaderLabels(["Escopo", "Atalho", "Ação / Descrição"])
        table_shortcuts.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        table_shortcuts.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        table_shortcuts.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        table_shortcuts.setSelectionMode(QTableWidget.NoSelection)
        table_shortcuts.setEditTriggers(QTableWidget.NoEditTriggers)
        table_shortcuts.setMinimumHeight(320)

        for row, (key, desc, scope) in enumerate(shortcuts_data):
            table_shortcuts.setItem(row, 0, QTableWidgetItem(scope))
            table_shortcuts.setItem(row, 1, QTableWidgetItem(key))
            table_shortcuts.setItem(row, 2, QTableWidgetItem(desc))

        shortcuts_layout.addWidget(table_shortcuts)
        layout_reader.addWidget(shortcuts_group)
        layout_reader.addStretch()

        scroll_reader.setWidget(scroll_content_reader)
        tab_reader_layout.addWidget(scroll_reader)

        # Adiciona as abas ao widget principal
        self.tabs.addTab(tab_general, "⚙️ Geral e Backup")
        self.tabs.addTab(tab_reader, "📖 Leitor e Atalhos")

        # Grupo de Atualizações
        group_update = QGroupBox("🔄 Atualizações do Sistema")
        update_layout = QVBoxLayout(group_update)

 
        self.lbl_update_status = QLabel(f"Versão Atual instalada: v{get_current_version()}")
        self.lbl_update_status.setStyleSheet("color: #A6ADC8; font-size: 12px;")

        
        update_layout.addWidget(self.lbl_update_status)
        

        self.btn_check_update = QPushButton("🔎 Buscar Atualização")

        if not is_frozen():
            self.lbl_update_status.setText(f"Versão Atual: v{get_current_version()} (Modo Dev - Código Fonte)")
            self.btn_check_update.setToolTip("Atualizações automáticas funcionam apenas na versão final compilada (.exe / .tar.gz)")
            
        self.btn_check_update.setProperty("class", "primary-btn")
        self.btn_check_update.setCursor(Qt.PointingHandCursor)
        self.btn_check_update.clicked.connect(self.check_for_updates)

        update_layout.addWidget(self.btn_check_update)
        layout_general.addWidget(group_update)

        main_layout.addWidget(self.tabs)
        self.update_cloud_ui_state()

    
    def check_for_updates(self):

        # Trava amigável se o dev clicar durante o desenvolvimento
        if not is_frozen():
            QMessageBox.warning(
                self,
                "Modo de Desenvolvimento",
                "A atualização automática via aplicativo só está disponível nos executáveis compilados.\n\n"
                "Em ambiente de desenvolvimento, utilize 'git pull' para atualizar o código."
            )
            return

        """Inicia a checagem por atualizações sem travar a interface."""
        self.btn_check_update.setEnabled(False)
        self.btn_check_update.setText("⏳ Verificando no GitHub...")

        self.updater_thread = UpdateCheckerWorker()
        self.updater_thread.finished_signal.connect(self._on_update_check_finished)
        self.updater_thread.error_signal.connect(self._on_update_check_error)
        self.updater_thread.start()

    def _on_update_check_finished(self, has_update: bool, latest_version: str, download_url: str, asset_name: str):
        self.btn_check_update.setEnabled(True)
        self.btn_check_update.setText("🔎 Buscar Atualização")

        if not has_update:
            QMessageBox.information(
                self, 
                "Aplicação Atualizada", 
                f"Você já está utilizando a versão mais recente (v{latest_version})."
            )
            return

        # Se houver atualização
        reply = QMessageBox.question(
            self,
            "Nova Atualização Encontrada! 🎉",
            f"A versão v{latest_version} já está disponível no GitHub.\n\n"
            f"Deseja baixar e atualizar o aplicativo agora?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )

        if reply == QMessageBox.Yes:
            self.perform_update(download_url)

    def _on_update_check_error(self, err_msg: str):
        self.btn_check_update.setEnabled(True)
        self.btn_check_update.setText("🔎 Buscar Atualização")
        QMessageBox.warning(self, "Falha na Verificação", err_msg)

    def perform_update(self, download_url: str):
        self.btn_check_update.setEnabled(False)
        self.btn_check_update.setText("📥 Baixando atualização (0%)...")

        self.downloader = DownloadWorker(download_url)
        
        # Atualiza o progresso visual no botão
        self.downloader.progress_signal.connect(
            lambda pct: self.btn_check_update.setText(f"📥 Baixando atualização ({pct}%)...")
        )
        
        def on_success(extracted_dir):
            QMessageBox.information(
                self,
                "Pronto para Atualizar",
                "O arquivo de atualização foi baixado com sucesso!\n\n"
                "O FocusFlow será fechado agora para aplicar as alterações."
            )
            try:
                engine.dispose()
            except NameError:
                pass
            launch_updater_script_and_exit(extracted_dir)

        def on_error(err):
            self.btn_check_update.setEnabled(True)
            self.btn_check_update.setText("🔎 Buscar Atualização")
            QMessageBox.critical(self, "Erro no Download", err)

        self.downloader.finished_signal.connect(on_success)
        self.downloader.error_signal.connect(on_error)
        self.downloader.start()


    # ---------------- MÉTODOS DE INTEGRAÇÃO GOOGLE DRIVE ----------------

    def update_cloud_ui_state(self):
        """Atualiza os botões e labels conforme o status da autenticação Google."""
        self.btn_google_auth.setEnabled(True)

        if self.gdrive_service.is_authenticated():
            self.lbl_cloud_status.setText("Status: 🟢 Conectado ao Google Drive (AppData Folder Oculta)")
            self.lbl_cloud_status.setStyleSheet("color: #A6E3A1; font-size: 12px; font-weight: bold;")
            self.btn_google_auth.setText("🔴 Desconectar Conta")
            self.btn_cloud_upload.setEnabled(True)
            self.btn_cloud_download.setEnabled(True)
        else:
            self.lbl_cloud_status.setText("Status: ⚪ Desconectado (Seus dados estão salvos apenas neste PC)")
            self.lbl_cloud_status.setStyleSheet("color: #A6ADC8; font-size: 12px;")
            self.btn_google_auth.setText("🔑 Conectar Conta Google")
            self.btn_cloud_upload.setEnabled(False)
            self.btn_cloud_download.setEnabled(False)

    def toggle_google_auth(self):
        """Conecta ou desconecta a conta do Google sem travar a interface."""
        if self.gdrive_service.is_authenticated():
            self.gdrive_service.logout()
            self.gdrive_service = GDriveSyncService()
            self.update_cloud_ui_state()
            self.refresh_backups_table()
            QMessageBox.information(self, "Desconectado", "Sua conta do Google foi desconectada com sucesso.")
        else:
            self.btn_google_auth.setEnabled(False)
            self.btn_google_auth.setText("⏳ Aguardando Login no Navegador...")

            self.oauth_thread = OAuthWorker(self.gdrive_service)
            self.oauth_thread.finished_signal.connect(self._on_oauth_finished)
            self.oauth_thread.start()

    def _on_oauth_finished(self, success: bool, error_msg: str):
        """Callback executado assim que a Thread do OAuth termina ou expira."""
        if success:
            QMessageBox.information(self, "Sucesso", f"Autenticação concluída! O {config.APP_NAME} agora pode sincronizar seus dados.")
        elif "timeout" in error_msg.lower() or "timed out" in error_msg.lower() or "tempo limite" in error_msg.lower():
            QMessageBox.warning(
                self, 
                "Tempo Esgotado ⏳", 
                "O tempo para autorizar a conta no navegador expirou (limite de 5 min).\n\n"
                "Para tentar novamente, basta clicar em 'Conectar Conta Google'."
            )
        elif error_msg:
            QMessageBox.warning(self, "Login Não Concluído", f"{error_msg}")
        else:
            QMessageBox.warning(self, "Cancelado", "A autenticação foi interrompida.")

        self.update_cloud_ui_state()
        self.refresh_backups_table()

    def upload_to_cloud(self):
        """Faz o envio manual do banco de dados local para a nuvem."""
        db_path = str(config.DB_PATH)
        if not os.path.exists(db_path):
            QMessageBox.warning(self, "Aviso", "O arquivo de banco de dados local não foi encontrado.")
            return

        try:
            self.gdrive_service.upload_database(db_path)
            QMessageBox.information(self, "Nuvem Sincronizada", "Banco de dados enviado para o Google Drive com sucesso!")
            self.refresh_backups_table()
        except Exception as e:
            QMessageBox.critical(self, "Erro na Sincronização", f"Falha ao enviar dados para a nuvem:\n{str(e)}")

    def download_from_cloud(self):
        """Baixa o banco de dados da nuvem e substitui o local com retentativa defensiva."""
        confirm = QMessageBox.question(
            self,
            "Confirmar Download da Nuvem",
            "Deseja substituir seus dados LOCAIS pela versão salva no Google Drive?\n\nEsta operação não pode ser desfeita.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if confirm == QMessageBox.Yes:
            db_path = str(config.DB_PATH)
            temp_download_path = f"{db_path}.tmp"

            try:
                engine.dispose()
                self.gdrive_service.download_database(temp_download_path)
                safe_replace_file(temp_download_path, db_path)

                if os.path.exists(temp_download_path):
                    os.remove(temp_download_path)

                with SessionLocal() as db:
                    db.expire_all()

                self.refresh_stats()
                self.refresh_backups_table()
                self.app_reset.emit()
                
                QMessageBox.information(self, "Sucesso", "Banco de dados restaurado da nuvem com sucesso!")
            except Exception as e:
                if os.path.exists(temp_download_path):
                    try:
                        os.remove(temp_download_path)
                    except Exception:
                        pass
                QMessageBox.critical(self, "Erro ao Baixar", f"Falha ao baixar dados da nuvem:\n{str(e)}")

    # ---------------- LÓGICA DE DADOS & BACKUPS LOCAIS ----------------

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
        folder = QFileDialog.getExistingDirectory(self, "Selecionar Pasta de Backups", self.get_backup_folder())
        if folder:
            self.settings.setValue("custom_backup_dir", folder)
            self.lbl_dir.setText(f"📂 Diretório Atual: {folder}")
            self.refresh_backups_table()

    def refresh_backups_table(self):
        backup_dir = self.get_backup_folder()
        os.makedirs(backup_dir, exist_ok=True)

        rows = []

        if os.path.exists(backup_dir):
            for f in os.listdir(backup_dir):
                if f.endswith('.zip'):
                    path = os.path.join(backup_dir, f)
                    stat = os.stat(path)
                    dt_utc_naive = datetime.utcfromtimestamp(stat.st_mtime)
                    rows.append({
                        "origin": "💻 Local",
                        "filename": f,
                        "date": dt_utc_naive,
                        "size": f"{stat.st_size / (1024 * 1024):.2f} MB",
                        "path": path,
                        "is_cloud": False
                    })

        if self.gdrive_service.is_authenticated():
            cloud_meta = self.gdrive_service.get_cloud_db_metadata()
            if cloud_meta:
                dt_iso = datetime.fromisoformat(cloud_meta['modifiedTime'].replace('Z', '+00:00'))
                dt_utc_naive = dt_iso.astimezone(timezone.utc).replace(tzinfo=None)
                
                size_mb = f"{int(cloud_meta.get('size', 0)) / (1024 * 1024):.2f} MB"
                rows.append({
                    "origin": "☁️ Nuvem",
                    "filename": f"{config.DB_NAME} (Snapshot Nuvem)",
                    "date": dt_utc_naive,
                    "size": size_mb,
                    "path": None,
                    "is_cloud": True
                })

        rows.sort(key=lambda r: r["date"], reverse=True)

        self.table_backups.setRowCount(len(rows))

        for row, data in enumerate(rows):
            item_origin = QTableWidgetItem(data["origin"])
            item_name = QTableWidgetItem(data["filename"])
            item_date = QTableWidgetItem(data["date"].strftime("%d/%m/%Y %H:%M"))
            item_size = QTableWidgetItem(data["size"])

            if data["is_cloud"]:
                item_origin.setForeground(Qt.green)
            else:
                item_origin.setForeground(Qt.cyan)

            self.table_backups.setItem(row, 0, item_origin)
            self.table_backups.setItem(row, 1, item_name)
            self.table_backups.setItem(row, 2, item_date)
            self.table_backups.setItem(row, 3, item_size)

            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(4, 2, 4, 2)

            if data["is_cloud"]:
                btn_restore = QPushButton("📲 Baixar da Nuvem")
                btn_restore.clicked.connect(self.download_from_cloud)
                actions_layout.addWidget(btn_restore)
            else:
                btn_restore = QPushButton("🔄")
                btn_restore.clicked.connect(lambda _, p=data["path"]: self.restore_direct_backup(p))
                btn_delete = QPushButton("🗑️")
                btn_delete.clicked.connect(lambda _, p=data["path"], n=data["filename"]: self.delete_backup(p, n))
                actions_layout.addWidget(btn_restore)
                actions_layout.addWidget(btn_delete)

            self.table_backups.setCellWidget(row, 4, actions_widget)

    def restore_direct_backup(self, file_path: str):
        confirm = QMessageBox.question(
            self,
            "Confirmar Restauração",
            "Deseja substituir TODOS os seus dados atuais pelo conteúdo deste backup?\n\nEsta operação é irreversível.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if confirm == QMessageBox.Yes:
            try:
                engine.dispose()
                BackupManager.import_backup(file_path)
                
                self.refresh_stats()
                self.refresh_backups_table()
                self.app_reset.emit()
                
                QMessageBox.information(self, "Sucesso", "Backup restaurado com sucesso!")
            except Exception as e:
                QMessageBox.critical(self, "Erro na Restauração", f"Falha ao restaurar o backup:\n{str(e)}")

    def delete_backup(self, file_path: str, filename: str):
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

    def import_backup(self):
        path, _ = QFileDialog.getOpenFileName(self, "Selecionar Backup para Importar", "", "ZIP Files (*.zip)")
        if path:
            self.restore_direct_backup(path)

    # ---------------- RESET DA APLICAÇÃO ----------------

    def reset_application(self):
        """Executa a remoção física de todo o diretório de dados, encerra sessões e opcionalmente limpa a nuvem."""
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setWindowTitle("⚠️ Atenção - Reset de Dados")
        msg_box.setText("Você tem certeza de que deseja apagar TODOS os dados do aplicativo?\n\n"
                        "Essa ação apagará permanentemente o banco de dados local, a pasta de backups local, "
                        "PDFs, caderno de erros, histórico e grifos.")
        
        msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg_box.setDefaultButton(QMessageBox.No)

        chk_delete_cloud = None
        if self.gdrive_service.is_authenticated():
            chk_delete_cloud = QCheckBox("Deseja também apagar a cópia de segurança armazenada no Google Drive?", msg_box)
            chk_delete_cloud.setStyleSheet("color: #F38BA8; font-size: 12px; margin-top: 10px;")
            msg_box.setCheckBox(chk_delete_cloud)

        if msg_box.exec() != QMessageBox.Yes:
            return

        should_delete_cloud = chk_delete_cloud.isChecked() if chk_delete_cloud else False

        text, ok = QInputDialog.getText(
            self,
            "🔒 Dupla Confirmação Exigida",
            "Esta ação é IRREVERSÍVEL!\nPara confirmar o reset local, digite a palavra RESETAR abaixo:"
        )

        if not ok or text.strip().upper() != "RESETAR":
            QMessageBox.warning(self, "Reset Cancelado", "Palavra digitada incorretamente. A operação foi cancelada.")
            return

        engine.dispose()

        try:
            root_data_folder = config.DATA_DIR.parent

            if root_data_folder.exists():
                shutil.rmtree(root_data_folder)

            config.ensure_directories_exist()
            Base.metadata.create_all(bind=engine)

            cloud_msg = ""
            if should_delete_cloud:
                if self.gdrive_service.delete_cloud_database():
                    cloud_msg = "\n• O banco de dados no Google Drive também foi apagado."
                else:
                    cloud_msg = "\n• Houve uma falha ao tentar apagar o banco no Google Drive."

            if self.gdrive_service.is_authenticated():
                self.gdrive_service.logout()
                self.gdrive_service = GDriveSyncService()
                cloud_msg += "\n• A sua conta do Google Drive foi desconectada."

            self.settings.clear()

            self.lbl_dir.setText(f"📂 Diretório Atual: {self.get_backup_folder()}")
            self.update_cloud_ui_state()
            self.refresh_stats()
            self.refresh_backups_table()
            self.app_reset.emit()

            QMessageBox.information(
                self, 
                "Aplicação Resetada", 
                f"A pasta de dados local ({root_data_folder.name}) foi completamente limpa e redefinida.{cloud_msg}\n\nO {config.APP_NAME} está limpo."
            )
        except Exception as e:
            QMessageBox.critical(self, "Erro no Reset", f"Ocorreu uma falha ao resetar a aplicação: {str(e)}")