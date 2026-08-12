import sys
import os
import ctypes
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon

from config.app import config
from database.connection import init_db
from ui.main_window import MainWindow

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
    app.setStyle("Fusion")  # Garante estilo consistente no Linux e Windows

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