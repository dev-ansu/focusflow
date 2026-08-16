from PySide6.QtWidgets import QDialog, QVBoxLayout, QFormLayout, QSpinBox, QDialogButtonBox

class PomodoroSettingsDialog(QDialog):
    def __init__(self, work_min=25, short_min=5, long_min=15, parent=None):
        super().__init__(parent)
        self.setWindowTitle("⚙️ Configurações do Pomodoro")
        self.setFixedWidth(280)
        
        self.setStyleSheet("""
            QDialog {
                background-color: #1E1E2E;
                color: #CDD6F4;
                font-family: 'Segoe UI', system-ui, sans-serif;
            }
            QLabel { color: #CDD6F4; font-size: 13px; }
            QSpinBox {
                background-color: #181825;
                color: #CDD6F4;
                border: 1px solid #313244;
                border-radius: 5px;
                padding: 4px;
                font-size: 13px;
            }
            QSpinBox::up-button, QSpinBox::down-button {
                background-color: #313244;
                border-radius: 2px;
            }
            QPushButton {
                background-color: #313244;
                color: #CDD6F4;
                border: 1px solid #45475A;
                border-radius: 5px;
                padding: 6px 14px;
                font-weight: 500;
            }
            QPushButton:hover { background-color: #45475A; }
        """)

        layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        form_layout.setSpacing(10)

        self.sb_work = QSpinBox()
        self.sb_work.setRange(1, 180)
        self.sb_work.setValue(work_min)
        self.sb_work.setSuffix(" min")

        self.sb_short = QSpinBox()
        self.sb_short.setRange(1, 60)
        self.sb_short.setValue(short_min)
        self.sb_short.setSuffix(" min")

        self.sb_long = QSpinBox()
        self.sb_long.setRange(1, 120)
        self.sb_long.setValue(long_min)
        self.sb_long.setSuffix(" min")

        form_layout.addRow("🎯 Tempo de Foco:", self.sb_work)
        form_layout.addRow("☕ Pausa Curta:", self.sb_short)
        form_layout.addRow("🎉 Pausa Longa:", self.sb_long)

        layout.addLayout(form_layout)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addSpacing(10)
        layout.addWidget(buttons)

    def get_values(self):
        return self.sb_work.value(), self.sb_short.value(), self.sb_long.value()