import sys
import os
import ctypes
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon, QColor, QPalette, Qt

from config.app import config
from database.connection import init_db
from ui.main_window import MainWindow

def apply_dark_palette(app: QApplication):
    """Força o tema Dark em toda a aplicação ignorando o tema do SO."""
    # 1. Define o estilo neutro Fusion (evita que o SO aplique o tema nativo claro)
    app.setStyle("Fusion")

    # 2. Cria uma paleta de cores totalmente escura
    dark_palette = QPalette()

    # Cores base
    dark_color = QColor("#1E1E2E")
    dark_surface = QColor("#252637")
    text_color = QColor("#CDD6F4")
    accent_color = QColor("#89B4FA")

    # Define as cores para todos os papéis do Qt
    dark_palette.setColor(QPalette.Window, dark_color)
    dark_palette.setColor(QPalette.WindowText, text_color)
    dark_palette.setColor(QPalette.Base, dark_surface)
    dark_palette.setColor(QPalette.AlternateBase, dark_color)
    dark_palette.setColor(QPalette.ToolTipBase, text_color)
    dark_palette.setColor(QPalette.ToolTipText, text_color)
    dark_palette.setColor(QPalette.Text, text_color)
    dark_palette.setColor(QPalette.Button, dark_color)
    dark_palette.setColor(QPalette.ButtonText, text_color)
    dark_palette.setColor(QPalette.BrightText, Qt.red)
    dark_palette.setColor(QPalette.Link, accent_color)
    dark_palette.setColor(QPalette.Highlight, accent_color)
    dark_palette.setColor(QPalette.HighlightedText, QColor("#11111B"))
    
    # Cores para elementos desabilitados (Disabled)
    dark_palette.setColor(QPalette.Disabled, QPalette.WindowText, QColor("#6C7086"))
    dark_palette.setColor(QPalette.Disabled, QPalette.Text, QColor("#6C7086"))
    dark_palette.setColor(QPalette.Disabled, QPalette.ButtonText, QColor("#6C7086"))

    # Aplica a paleta globalmente
    app.setPalette(dark_palette)

def main():
    # ---------------------------------------------------------
    # 1. Configuração de AppUserModelID (Exclusivo Windows)
    # Permite que a barra de tarefas do Windows agrupe e mostre o ícone correto
    # ---------------------------------------------------------
    if sys.platform == "win32":
        try:
            myappid = f"{config.AUTHOR}.{config.APP_SLUG}.{config.APP_VERSION}"
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        except Exception as e:
            print(f"Aviso ao definir AppUserModelID: {e}")

    # Inicializa o banco de dados SQLite local
    init_db()

    app = QApplication(sys.argv)
    apply_dark_palette(app)

    # ---------------------------------------------------------
    # 2. Definição do Ícone da Aplicação
    # ---------------------------------------------------------
    # Seleciona .ico no Windows e .png no Linux
    icon_filename = "icon.ico" if sys.platform == "win32" else "icon.png"
    icon_path = config.BASE_DIR / "assets" / icon_filename

    if icon_path.exists():
        app_icon = QIcon(str(icon_path))
        app.setWindowIcon(app_icon)  # Define o ícone global (afeta janelas e barra de tarefas)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()