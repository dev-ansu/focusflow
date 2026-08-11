from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLineEdit, QListWidget, 
    QListWidgetItem, QLabel
)
from PySide6.QtCore import Qt, QTimer
from database.connection import SessionLocal
from models.models import Subject, Topic, Note, Highlight, PdfDocument


class GlobalSearchDialog(QDialog):
    """Modal de busca global estilo Command Palette / Search Bar."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🔍 Busca Global - Matérias, Tópicos, Anotações e Grifos")
        self.resize(700, 480)
        
        self.selected_result = None

        # Timer para Debounce (300ms)
        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self.perform_search)

        self.init_ui()

    def init_ui(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #1E222A;
                color: #ECF0F1;
            }
            QLineEdit {
                background-color: #121418;
                color: #ECF0F1;
                border: 2px solid #34495E;
                border-radius: 6px;
                padding: 10px;
                font-size: 15px;
            }
            QLineEdit:focus {
                border-color: #3498DB;
            }
            QListWidget {
                background-color: #181B20;
                color: #ECF0F1;
                border: 1px solid #2C3E50;
                border-radius: 6px;
                font-size: 13px;
            }
            QListWidget::item {
                padding: 8px 12px;
                border-bottom: 1px solid #232731;
            }
            QListWidget::item:hover {
                background-color: #2C3E50;
            }
            QListWidget::item:selected {
                background-color: #34495E;
                color: #3498DB;
                font-weight: bold;
            }
            QLabel {
                color: #BDC3C7;
                font-size: 12px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔎 Digite para buscar matérias, tópicos, anotações ou grifos...")
        self.search_input.textChanged.connect(self.on_text_changed)
        layout.addWidget(self.search_input)

        self.lbl_status = QLabel("Digite pelo menos 2 caracteres para buscar.")
        layout.addWidget(self.lbl_status)

        self.results_list = QListWidget()
        self.results_list.itemDoubleClicked.connect(self.on_item_double_clicked)
        layout.addWidget(self.results_list)

    def on_text_changed(self, text):
        self.search_timer.stop()
        if len(text.strip()) >= 2:
            self.lbl_status.setText("Buscando...")
            self.search_timer.start(300)
        else:
            self.results_list.clear()
            self.lbl_status.setText("Digite pelo menos 2 caracteres para buscar.")

    def perform_search(self):
        query_text = self.search_input.text().strip()
        if not query_text:
            return

        self.results_list.clear()
        search_pattern = f"%{query_text}%"

        db = SessionLocal()
        results_count = 0

        try:
            # 1. MATÉRIAS
            subjects = db.query(Subject).filter(Subject.name.ilike(search_pattern)).all()
            for s in subjects:
                item = QListWidgetItem(f"📚 MATÉRIA: {s.name}")
                item.setData(Qt.UserRole, {"type": "SUBJECT", "subject_id": s.id})
                self.results_list.addItem(item)
                results_count += 1

            # 2. TÓPICOS / CAPÍTULOS
            topics = (
                db.query(Topic)
                .join(PdfDocument)
                .join(Subject)
                .filter(Topic.title.ilike(search_pattern))
                .all()
            )
            for t in topics:
                subj_name = t.pdf.subject.name if t.pdf and t.pdf.subject else "Matéria"
                item = QListWidgetItem(f"🔖 TÓPICO: {t.title}  ➔  [{subj_name}] (Págs {t.page_start}-{t.page_end})")
                item.setData(Qt.UserRole, {
                    "type": "TOPIC", 
                    "topic_id": t.id, 
                    "subject_id": t.pdf.subject_id if t.pdf else None
                })
                self.results_list.addItem(item)
                results_count += 1

            # 3. ANOTAÇÕES (NOTES)
            notes = (
                db.query(Note)
                .join(PdfDocument)
                .filter(Note.content.ilike(search_pattern))
                .all()
            )
            for n in notes:
                pdf_title = n.pdf.title if n.pdf else "PDF"
                snippet = n.content.replace("\n", " ")[:80]
                item = QListWidgetItem(f"📝 ANOTAÇÃO: \"{snippet}...\"  ➔  [{pdf_title} - Pág {n.page_number}]")
                item.setData(Qt.UserRole, {
                    "type": "NOTE",
                    "note_id": n.id,
                    "subject_id": n.pdf.subject_id if n.pdf else None
                })
                self.results_list.addItem(item)
                results_count += 1

            # 4. GRIFOS (HIGHLIGHTS)
            highlights = (
                db.query(Highlight)
                .join(PdfDocument)
                .filter(Highlight.selected_text.ilike(search_pattern))
                .all()
            )
            for h in highlights:
                pdf_title = h.pdf.title if h.pdf else "PDF"
                snippet = (h.selected_text or "").replace("\n", " ")[:80]
                item = QListWidgetItem(f"🖍️ GRIFO: \"{snippet}...\"  ➔  [{pdf_title} - Pág {h.page_number}]")
                item.setData(Qt.UserRole, {
                    "type": "HIGHLIGHT",
                    "highlight_id": h.id,
                    "subject_id": h.pdf.subject_id if h.pdf else None
                })
                self.results_list.addItem(item)
                results_count += 1

            self.lbl_status.setText(f"Encontrados {results_count} resultado(s) para '{query_text}'.")

        except Exception as e:
            self.lbl_status.setText(f"Erro ao pesquisar: {str(e)}")
        finally:
            db.close()

    def on_item_double_clicked(self, item):
        self.selected_result = item.data(Qt.UserRole)
        self.accept()