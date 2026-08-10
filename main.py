import sys
from PySide6.QtWidgets import QApplication
from database.connection import init_db
from ui.main_window import MainWindow
from ui.reader import StudyReaderView

def main():
    # Inicializa o banco de dados SQLite local
    init_db()

    app = QApplication(sys.argv)
    app.setStyle("Fusion")  # Garante estilo consistente no Linux e Windows

    window = MainWindow()
    window.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
